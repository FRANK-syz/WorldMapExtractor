import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from osgeo import gdal,gdalconst
import cv2 as cv
import ast
import os
import sys

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog, QGraphicsScene, QMessageBox, QTreeWidgetItem, QDialog, QDialogButtonBox
from PyQt5.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(self.resource_path('WorldMapExtractor.ui'), self)
        plt.rcParams['font.sans-serif'] = ['SimHei']  
        plt.rcParams['axes.unicode_minus'] = False    
        plt.tight_layout()

        self.child = None
        self.Layers=[]
        self.Layernames=[]
        self.activated_flag=[]
        self.activated_Layers=[]
        self.activated_Layernames=[]
        self.Transform = None
        self.Projection = None
        self.scene = QGraphicsScene()
        self.graphic.setScene(self.scene)

        self.root = QTreeWidgetItem()
        self.root.setText(0,"Layers")
        self.treeWidget.addTopLevelItem(self.root)
        self.treeWidget.expandAll()

    #导入图片
    def import_graph(self):
        filepath = QFileDialog.getOpenFileName(self,"选择图像","","*.tif *.jpg *.png *.gif")[0]
        filename = filepath.split("/")[-1]
        if filepath:
            Import_Img = cv.imdecode(np.fromfile(filepath, dtype=np.uint8), cv.IMREAD_COLOR)
            Import_Img = cv.cvtColor(Import_Img, cv.COLOR_BGR2RGB)

            self.add_layer(filename,Import_Img)

    #导出为图片
    def export_to_png(self):
        if len(self.activated_Layernames)==1:
            filepath = QFileDialog.getSaveFileName(self,"保存图像","","*.jpg *.png *.gif")[0]
            if filepath:
                suffix="."+filepath.split(".")[1]
                Save_Img = cv.cvtColor(self.activated_Layers[0], cv.COLOR_RGB2BGR)
                ret, buf = cv.imencode(suffix, Save_Img)
                with open(filepath, 'wb') as f:
                    f.write(buf.tobytes())
                f.close()
                QMessageBox.information(self, "提示",f"保存成功！\n{filepath}",QMessageBox.Ok)
        else:
            QMessageBox.warning(self, "警告","请保留一个图层！",QMessageBox.Ok)

    #导出为tif
    def export_to_tif(self):
        if len(self.activated_Layernames)==1:
            filepath = QFileDialog.getSaveFileName(self,"保存图像","","*.tif")[0]
            if filepath:
                Img = self.activated_Layers[0]
                if len(Img.shape)>2:
                    Img = Img[:,:,0]
                xsize=Img.shape[1]
                ysize=Img.shape[0]
                driver = gdal.GetDriverByName("GTiff")
                outdata = driver.Create(filepath, 
                xsize=xsize,ysize=ysize,bands=1,eType=gdalconst.GDT_Float32)
                if self.Transform==None or self.Projection==None:
                    QMessageBox.warning(self, "警告","通过配准可获得地理坐标信息！",QMessageBox.Ok)
                else:
                    outdata.SetGeoTransform(self.Transform)
                    outdata.SetProjection(self.Projection)
                    outband=outdata.GetRasterBand(1)
                    outband.WriteArray(Img)
                    outdata.FlushCache()
                    outdata = None
                    QMessageBox.information(self, "提示",f"保存成功！\n{filepath}",QMessageBox.Ok)
        else:
            QMessageBox.warning(self, "警告","请保留一个图层！",QMessageBox.Ok)

    #添加图层
    def add_layer(self, filename, Img):
        treeItem = QTreeWidgetItem()
        treeItem.setText(0,filename)
        treeItem.setCheckState(0,Qt.Checked)
        subItem = QTreeWidgetItem()
        rows,cols = Img.shape[0], Img.shape[1]
        Info = str(rows)+"\u00D7"+str(cols)
        subItem.setText(0,Info)
        treeItem.addChild(subItem)
        self.root.addChild(treeItem)
        self.treeWidget.expandAll()

        self.Layernames.append(filename)
        self.Layers.append(Img)
        self.activated_flag.append(1)
        self.activated_Layernames=[a for a, b in zip(self.Layernames, self.activated_flag) if b != 0]
        self.activated_Layers = [a for a, b in zip(self.Layers, self.activated_flag) if b != 0]
        
        if self.activated_Layers!=[]:
            self.plot_data()

    #更新图片
    def update_layer(self, item, column):
        state = item.checkState(0)
        if state==Qt.Unchecked:
            index=self.Layernames.index(item.text(0))    
            self.activated_flag[index] = 0
            self.activated_Layernames=[a for a, b in zip(self.Layernames, self.activated_flag) if b != 0]
            self.activated_Layers = [a for a, b in zip(self.Layers, self.activated_flag) if b != 0]
        elif state==Qt.Checked:
            index=self.Layernames.index(item.text(0))   
            self.activated_flag[index] = 1
            self.activated_Layernames=[a for a, b in zip(self.Layernames, self.activated_flag) if b != 0]
            self.activated_Layers = [a for a, b in zip(self.Layers, self.activated_flag) if b != 0]
        self.plot_data()

    #画图区画图
    def plot_data(self):
        _dpi=100
        view_size = self.graphic.size()
        self.figure = Figure(figsize=(view_size.width()/_dpi,view_size.height()/_dpi),dpi=_dpi)
        self.canvas = FigureCanvas(self.figure)
        self.scene.addWidget(self.canvas)
        self.figure.clear()
        self.canvas.setCursor(Qt.PointingHandCursor) 
        self.canvas.mpl_connect('motion_notify_event', self.on_canvas_move)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)

        if len(self.activated_Layers)!=0:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            Imgs = self.activated_Layers
            for Img in Imgs:
                if Img.ndim==3:
                    im = ax.imshow(Img, origin='upper',alpha=1/len(Imgs))
                    self.canvas.draw()
                    self.im = im
                elif Img.ndim==2:
                    greyImg = cv.normalize(Img, None, 0, 255, cv.NORM_MINMAX)
                    im = ax.imshow(greyImg, origin='upper',alpha=1/len(Imgs),cmap="Greys")
                    self.canvas.draw()
                    self.im = im
        else:
            self.figure.clear()
            self.canvas.draw()   

    #点击画布展示matplotlib画图
    def on_canvas_click(self, event):
        Imgs = self.activated_Layers
        plt.close('all')
        plt.figure(num="matplotlib窗口")
        plt.imshow(Imgs[0])
        plt.show()

    #记录行列号
    def on_canvas_move(self, event):
        if not event.inaxes:
            self.label_coord.setText("不在图像区域内")
            return
    
        row = int(event.ydata + 0.5)  
        col = int(event.xdata + 0.5)
        img_array = self.activated_Layers[-1]
        if len(img_array.shape)==3:
            if 0 <= row < img_array.shape[0] and 0 <= col < img_array.shape[1]:
                r, g, b = img_array[row, col]
                rgb_info = f"R:{r}, G:{g}, B:{b}"
                
                self.label_coord.setText(
                    f"行: {row}, 列: {col} | {rgb_info}"
                )
        elif len(img_array.shape)==2:
            if 0 <= row < img_array.shape[0] and 0 <= col < img_array.shape[1]:
                DN = img_array[row, col]
                rgb_info = f"像元值: {DN}"
                
                self.label_coord.setText(
                    f"行: {row}, 列: {col} | {rgb_info}"
                )

    #打开工具栏
    def sift_dialog_show(self):
        self.child = SIFTDialog(self)  
        self.child.show() 

    def greyscale_dialog_show(self):
        self.child = GreyscaleDialog(self)  
        self.child.show()

    def colorscale_dialog_show(self):
        self.child = ColorscaleDialog(self)  
        self.child.show()

    def colorclassify_dialog_show(self):
        self.child = ColorclassifyDialog(self) 
        self.child.show()

    #打包路径
    def resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

class SIFTDialog(QDialog):
    def __init__(self,MainWindow):
        super().__init__()
        self.MainWindow = MainWindow
        uic.loadUi(self.MainWindow.resource_path('SIFTDialog.ui'), self)
        self.buttonBox.button(QDialogButtonBox.Ok).setText("确定")
        self.buttonBox.button(QDialogButtonBox.Cancel).setText("取消")
        self.buttonBox.button(QDialogButtonBox.Apply).setText("预览")
        self.comboBox.addItems(self.MainWindow.Layernames)
        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

    def showEvent(self, event):
        """窗口显示后自动触发"""
        super().showEvent(event)
        if self.MainWindow.Layernames!=[]:
            self.plot_data(self.MainWindow.Layers[0])

    #导出变量
    def accept(self):
        src_ds = gdal.Open(self.lineEdit_srcImg.text())
        comboBox_text = self.comboBox.currentText()
        edge_flag = self.buttonGroup_edge.checkedButton().text()
        range_flag = self.buttonGroup_range.checkedButton().text()
        coord_type = self.buttonGroup_coord.checkedButton().text()
        coord_id = self.lineEdit_coord.text()
        coord = coord_type+":"+coord_id
        target_rows = int(self.lineEdit_rows.text())
        target_cols = int(self.lineEdit_cols.text())
        match_rate = np.float32(self.lineEdit_matchrate.text())
        min_match_count = np.float32(self.lineEdit_minmatch.text())
        outputName = self.lineEdit_name.text()
        if self.MainWindow.Layernames!=[]:
            index = self.MainWindow.Layernames.index(comboBox_text)   
            testImg = self.MainWindow.Layers[index]

        if self.comboBox.currentText()=="" or self.lineEdit_name.text()=="" or self.lineEdit_coord.text()=="":
            QMessageBox.warning(self, "警告","填写不完整！",QMessageBox.Ok)
        else:
            srcImg, landmask = self.prepare_Warp(src_ds, coord, edge_flag, target_rows, target_cols)
            Matchimg, overlap, warpImg = self.SIFT(srcImg, testImg, landmask, range_flag, match_rate, min_match_count)
            self.close()
            self.MainWindow.add_layer(outputName,warpImg)

    #预览对比图
    def preview(self, button):
        if button.text()=="预览":
            src_ds = gdal.Open(self.lineEdit_srcImg.text())
            comboBox_text = self.comboBox.currentText()
            edge_flag = self.buttonGroup_edge.checkedButton().text()
            range_flag = self.buttonGroup_range.checkedButton().text()
            coord_type = self.buttonGroup_coord.checkedButton().text()
            coord_id = self.lineEdit_coord.text()
            coord = coord_type+":"+coord_id
            target_rows = int(self.lineEdit_rows.text())
            target_cols = int(self.lineEdit_cols.text())
            match_rate = np.float32(self.lineEdit_matchrate.text())
            min_match_count = int(self.lineEdit_minmatch.text())

            if self.MainWindow.Layernames!=[]:
                index = self.MainWindow.Layernames.index(comboBox_text)   
                testImg = self.MainWindow.Layers[index]

        
            if self.comboBox.currentText()=="" or self.lineEdit_coord.text()=="":
                QMessageBox.warning(self, "警告","填写不完整！",QMessageBox.Ok)
            else:
                
                srcImg, landmask = self.prepare_Warp(src_ds, coord, edge_flag, target_rows, target_cols)
                Matchimg, overlap, warpImg = self.SIFT(srcImg, testImg, landmask, range_flag, match_rate, min_match_count)
                self.plot_data(overlap)
                plt.close('all')
                plt.figure(num="匹配点",figsize=(12,8))
                plt.imshow(Matchimg)
                plt.show()
        return()

    #导入图片
    def import_graph(self):
        filepath = QFileDialog.getOpenFileName(self,"选择图像","","*.tif *.jpg *.png *.gif")[0]
        self.lineEdit_srcImg.setText(filepath)

    #画图
    def plot_data(self, Img):
        _dpi = 100
        view_size = self.graphicsView.size()
        self.figure = Figure(figsize=(view_size.width()/_dpi,view_size.height()/_dpi),dpi=_dpi)
        self.canvas = FigureCanvas(self.figure)
        self.scene.addWidget(self.canvas)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.im = ax.imshow(Img, origin='upper')
        self.canvas.draw()
        self.canvas.setCursor(Qt.PointingHandCursor) 
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)

    #画图
    def combo_draw(self):
        if self.MainWindow.Layernames!=[]:
            index = self.MainWindow.Layernames.index(self.comboBox.currentText())   
            testImg = self.MainWindow.Layers[index]
            self.plot_data(testImg)

    #点击画布展示matplotlib画图
    def on_canvas_click(self, event):
        if self.MainWindow.Layernames!=[]:
            comboBox_text = self.comboBox.currentText()
            index = self.MainWindow.Layernames.index(comboBox_text)   
            testImg = self.MainWindow.Layers[index]
            plt.close('all')
        plt.figure(num="matplotlib窗口",figsize=(12,8))
        plt.imshow(testImg)
        plt.show()
    
    #计算
    def prepare_Warp(self, src_ds, coord, edge_flag, target_rows, target_cols):
        # 打包后出现问题
        # warp_options = gdal.WarpOptions(
        # dstSRS = coord,
        # resampleAlg = gdal.GRA_Bilinear,
        # format = "MEM"  
        # )

        # proj_ds = gdal.Warp("", src_ds, options=warp_options) 

        proj_ds = src_ds
        self.MainWindow.Transform = proj_ds.GetGeoTransform()
        self.MainWindow.Projection = proj_ds.GetProjection()

        continent = proj_ds.ReadAsArray()
        continent = np.where(continent<255,0,255)
        continent = continent.astype(np.uint8)
        srcImg = np.expand_dims(continent,2).repeat(3,axis=2)
        srcImg = cv.resize(srcImg, (target_cols, target_rows), interpolation=cv.INTER_LINEAR)
        src_ds = None
        proj_ds = None
        landmask = srcImg[:,:,0]
        
        if edge_flag == "边缘（边缘具有明显黑色线条）":
            median = np.median(srcImg)
            sigma = 0.33 
            low_threshold = int(max(0, (1.0 - sigma) * median))
            high_threshold = int(min(255, (1.0 + sigma) * median))
            srcImg = cv.Canny(srcImg, low_threshold, high_threshold)
            srcImg = np.where(srcImg==255,0,255).astype(np.uint8)
            srcImg = np.expand_dims(srcImg,2).repeat(3,axis=2)

        return srcImg, landmask

    def SIFT(self, srcImg, testImg, landmask, range_flag, match_rate, min_match_count):
        #转换为灰度图
        img1gray = cv.cvtColor(srcImg, cv.COLOR_BGR2GRAY)
        img2gray = cv.cvtColor(testImg, cv.COLOR_BGR2GRAY)

        #特征检测与匹配
        sift = cv.SIFT_create()
        kp1, des1 = sift.detectAndCompute(img1gray, None)
        kp2, des2 = sift.detectAndCompute(img2gray, None)

        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des1, des2, k=2)

        #筛选优质匹配点
        matchesMask = [[0, 0] for i in range(len(matches))]
        good = []
        pts1 = []
        pts2 = []
        match_rate=0.7
        # ratio test as per Lowe's paper
        for i, (m, n) in enumerate(matches):
            if m.distance < match_rate*n.distance:
                good.append(m)
                pts2.append(kp2[m.trainIdx].pt)
                pts1.append(kp1[m.queryIdx].pt)
                matchesMask[i] = [1, 0]

        draw_params = dict(matchColor=(0, 255, 0),singlePointColor=(255, 0, 0),matchesMask=matchesMask,flags=0)
        img3 = cv.drawMatchesKnn(img1gray, kp1, img2gray, kp2, matches, None, **draw_params)

        #单应性矩阵计算
        rows,cols=srcImg.shape[0], srcImg.shape[1]
        if len(good) > min_match_count:
            src_pts = np.float32(pts2).reshape(-1, 1, 2)
            dst_pts = np.float32(pts1).reshape(-1, 1, 2)
            M, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 5.0)
            warpImg = cv.warpPerspective(testImg, M, (cols, rows),flags=cv.INTER_LINEAR,borderMode=cv.BORDER_CONSTANT,borderValue=(255, 255, 255))

            alpha = np.arange(1,cols+1).reshape(1,-1,1)/cols/2+0.25
            overlap = srcImg*alpha+warpImg*(1 - alpha)
            overlap = overlap.astype(np.uint8)
            
            if range_flag == "陆地":
                warpImg[landmask==255,:]=[255,255,255]
            elif range_flag == "海洋":
                warpImg[landmask==0,:]=[255,255,255]
            
            return img3, overlap, warpImg
        else:
            QMessageBox.warning(self, "警告","没有足够匹配点！ - {}/{}".format(len(good), min_match_count),QMessageBox.Ok)
            matchesMask = None

class GreyscaleDialog(QDialog):
    def __init__(self,MainWindow):
        super().__init__()
        self.MainWindow = MainWindow
        uic.loadUi(self.MainWindow.resource_path('GreyscaleDialog.ui'), self)
        self.buttonBox.button(QDialogButtonBox.Ok).setText("确定")
        self.buttonBox.button(QDialogButtonBox.Cancel).setText("取消")
        self.comboBox.addItems(self.MainWindow.Layernames)
        self.barImg = np.array([])
        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

    def import_graph(self):
        filepath = QFileDialog.getOpenFileName(self,"选择图像","","*.tif *.jpg *.png *.gif")[0]
        if filepath:
            self.lineEdit_barImg.setText(filepath)
            Import_Img = cv.imdecode(np.fromfile(filepath, dtype=np.uint8), cv.IMREAD_COLOR)
            self.barImg = cv.cvtColor(Import_Img, cv.COLOR_BGR2GRAY)
            self.plot_data(self.barImg)
            possible_backgroundrgb = self.find_major_rgb(self.barImg)
            self.lineEdit_backgroundrgb.setText(str(possible_backgroundrgb))

    def find_major_rgb(self, Img):
        pixels = Img.reshape(-1)
        counts = np.bincount(pixels)
        major_rgb = np.argmax(counts)
        return major_rgb

    #画图
    def plot_data(self, Img):
        _dpi = 100
        view_size = self.graphicsView.size()
        self.figure = Figure(figsize=(view_size.width()/_dpi,view_size.height()/_dpi),dpi=_dpi)
        self.canvas = FigureCanvas(self.figure)
        self.scene.addWidget(self.canvas)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.im = ax.imshow(Img, origin='upper', cmap="Greys_r")
        self.canvas.draw()
        self.canvas.setCursor(Qt.PointingHandCursor) 
        self.canvas.mpl_connect('motion_notify_event', self.on_canvas_move)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)

    def on_canvas_move(self, event):
        if not event.inaxes:
            self.label_coord.setText("不在图像区域内")
            return
    
        row = int(event.ydata + 0.5)  
        col = int(event.xdata + 0.5)
        img_array = self.im.get_array()

        if 0 <= row < img_array.shape[0] and 0 <= col < img_array.shape[1]:
            DN = img_array[row, col]
            self.label_coord.setText(
                f"行: {row}, 列: {col} | 灰度: {DN}"
            )

    #点击画布展示matplotlib画图
    def on_canvas_click(self, event):
        if self.barImg!=np.array([]):
            plt.close('all')
            plt.figure(num="matplotlib窗口",figsize=(12,8))
            plt.imshow(self.barImg, cmap="Greys_r")
            plt.title("灰度值")
            plt.colorbar(shrink=0.8)
            plt.show()

    #计算
    def accept(self):
        if self.comboBox.currentText()=="" or self.lineEdit_minvalue.text()=="" or self.lineEdit_minrgb.text()=="" or self.lineEdit_maxvalue.text()=="" or self.lineEdit_maxrgb.text()=="":
            QMessageBox.warning(self, "警告","填写不完整！",QMessageBox.Ok)
        else:
            min_value = self.lineEdit_minvalue.text()
            min_rgb = self.lineEdit_minrgb.text()
            max_value = self.lineEdit_maxvalue.text()
            max_rgb = self.lineEdit_maxrgb.text()
            background_value = self.lineEdit_backgroundvalue.text()
            background_rgb = self.lineEdit_backgroundrgb.text()
            outputName = self.lineEdit_name.text()
            comboBox_text = self.comboBox.currentText()
            index = self.MainWindow.Layernames.index(comboBox_text)   

            testImg = self.MainWindow.Layers[index]
            imggrey = cv.cvtColor(testImg, cv.COLOR_RGB2GRAY)
            grey_stretch = self.grey_stretch(imggrey, int(min_rgb), int(max_rgb) , np.float32(min_value), np.float32(max_value))

            if background_value!="":
                grey_stretch = np.where(imggrey==int(background_rgb),np.float32(background_value),grey_stretch)
            self.close()
            self.MainWindow.add_layer(outputName,grey_stretch)

    def grey_stretch(self, X, x1, x2, y1, y2):
        Y = X*(y2-y1)/(x2-x1)+(x2*y1-x1*y2)/(x2-x1)
        return Y

class ColorscaleDialog(QDialog):
    def __init__(self,MainWindow):
        super().__init__()
        self.MainWindow = MainWindow
        uic.loadUi(self.MainWindow.resource_path('ColorscaleDialog.ui'), self)
        self.buttonBox.button(QDialogButtonBox.Ok).setText("确定")
        self.buttonBox.button(QDialogButtonBox.Cancel).setText("取消")
        self.comboBox.addItems(self.MainWindow.Layernames)
        self.barImg = np.array([])
        self.isSelecting = False
        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

    def import_graph(self):
        filepath = QFileDialog.getOpenFileName(self,"选择图像","","*.tif *.jpg *.png *.gif")[0]
        if filepath:
            self.lineEdit_barImg.setText(filepath)
            Import_Img = cv.imdecode(np.fromfile(filepath, dtype=np.uint8), cv.IMREAD_COLOR)
            self.barImg = cv.cvtColor(Import_Img, cv.COLOR_BGR2RGB)
            self.plot_data(self.barImg)
            possible_backgroundrgb = self.find_major_rgb(self.barImg)
            self.lineEdit_backgroundrgb.setText(str(possible_backgroundrgb))

    def find_major_rgb(self, Img):
        pixels = Img.reshape(-1, 3)
        df = pd.DataFrame(pixels, columns=['R', 'G', 'B'])
        counts = df.groupby(['R', 'G', 'B']).size().reset_index(name='counts')
        max_row = counts.loc[counts['counts'].idxmax()]
        major_rgb = [int(max_row['R']), int(max_row['G']), int(max_row['B'])]
        return major_rgb

    #画图
    def plot_data(self, Img):
        _dpi = 100
        view_size = self.graphicsView.size()
        self.figure = Figure(figsize=(view_size.width()/_dpi,view_size.height()/_dpi),dpi=_dpi)
        self.canvas = FigureCanvas(self.figure)
        self.scene.addWidget(self.canvas)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.im = ax.imshow(Img, origin='upper')
        self.canvas.draw()
        self.canvas.mpl_connect('motion_notify_event', self.on_canvas_move) 
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)

    def change_flag(self):
        if self.isSelecting==True:
            self.isSelecting=False
            self.label_choose.setText("未开始选择")
            self.setCursor(Qt.ArrowCursor) 
            if self.barImg.size > 0:
                self.canvas.setCursor(Qt.ArrowCursor) 
        elif self.isSelecting==False:
            self.isSelecting=True
            self.label_choose.setText("开始选择")
            self.setCursor(Qt.CrossCursor) 
            if self.barImg.size > 0:
                self.canvas.setCursor(Qt.CrossCursor) 

    def on_canvas_move(self, event):
        if not event.inaxes:
            self.label_coord.setText("不在图像区域内")
            return
    
        row = int(event.ydata + 0.5)  
        col = int(event.xdata + 0.5)
        img_array = self.im.get_array()

        if 0 <= row < img_array.shape[0] and 0 <= col < img_array.shape[1]:
            r,g,b = img_array[row, col]
            self.label_coord.setText(f"行: {row}, 列: {col} | R: {r} G: {g} B: {b}")

    #点击画布展示matplotlib画图
    def on_canvas_click(self, event):
        if self.isSelecting:
            row = int(event.ydata + 0.5)  
            col = int(event.xdata + 0.5)
            point = (row,col)
            currentpointText = self.lineEdit_points.text()
            if currentpointText == "":
                self.lineEdit_points.setText(str(point))
            else:
                self.lineEdit_points.setText(currentpointText+","+str(point))

    #计算
    def accept(self):
        self.setWindowTitle("正在运行......")
        if self.lineEdit_barImg.text()=="" or self.comboBox.currentText()=="" or self.lineEdit_name.text()=="" or self.lineEdit_points.text()=="" or self.lineEdit_values.text()=="" or self.lineEdit_tolerance.text()=="":
            QMessageBox.warning(self, "警告","填写不完整！",QMessageBox.Ok)
        else:
            points = ast.literal_eval(self.lineEdit_points.text())
            values = ast.literal_eval(self.lineEdit_values.text())
            if len(points)>2 or len(values)>2:
                QMessageBox.warning(self, "警告","点过多，请保留两个点！",QMessageBox.Ok)
            elif len(points)<2 or len(values)<2:
                QMessageBox.warning(self, "警告","点过少，请增加至两个点！",QMessageBox.Ok)
            else:
                Tolerance = int(self.lineEdit_tolerance.text())
                background_value = np.float32(self.lineEdit_backgroundvalue.text())
                background_rgb = ast.literal_eval(self.lineEdit_backgroundrgb.text())
                outputName = self.lineEdit_name.text()
            
                comboBox_text = self.comboBox.currentText()
                index = self.MainWindow.Layernames.index(comboBox_text)   
                testImg = self.MainWindow.Layers[index]

                barcolor, min_value, max_value = self.getbarcolor(points, values)
                Color_stretch = self.Colorstretch(testImg, barcolor, min_value, max_value, Tolerance, background_rgb, background_value)
                self.close()
                self.MainWindow.add_layer(outputName,Color_stretch)

    def Colorstretch(self, testImg, barcolor, min_value, max_value, Tolerance, background_rgb, background_value):
        rows,cols = testImg.shape[:2]
        Color_stretch = np.ones([rows,cols])*background_value
        for i in range(0,rows):
            for j in range(0,cols):
                current_rgb = testImg[i,j,:]
                if np.array_equal(current_rgb,background_rgb)==False:
                    rgbdiff = np.max(np.abs(barcolor-current_rgb),axis=1)
                    if np.min(rgbdiff)<Tolerance:
                        Index = np.argmin(rgbdiff)
                        Color_stretch[i,j] = (Index+1)/len(barcolor)*(max_value-min_value)+min_value
        return Color_stretch
    
    def getbarcolor(self, points, values):
        point1 = points[0] 
        point2 = points[1]
        value1 = values[0]
        value2 = values[1]
        direction = self.buttonGroup.checkedButton().text()
        
        if direction=="水平（行号一致）":
            if point1[1]<point2[1]:
                min_point = point1
                min_value = value1
                max_point = point2
                max_value = value2
            else:
                min_point = point2
                min_value = value2
                max_point = point1
                max_value = value1
            barcolor = self.barImg[point1[0],min_point[1]:max_point[1]+1,:].astype(np.float32)
            return(barcolor,min_value,max_value)
        elif direction=="垂直（列号一致）" :
            if point1[0]<point2[0]:
                min_point = point1
                min_value = value1
                max_point = point2
                max_value = value2
            else:
                min_point = point2
                min_value = value2
                max_point = point1
                max_value = value1
            barcolor = self.barImg[min_point[0]:max_point[0]+1,point1[1],:].astype(np.float32)
            return(barcolor,min_value,max_value)        

class ColorclassifyDialog(QDialog):
    def __init__(self,MainWindow):
        super().__init__()
        self.MainWindow = MainWindow
        uic.loadUi(self.MainWindow.resource_path('ColorclassifyDialog.ui'), self)
        self.buttonBox.button(QDialogButtonBox.Ok).setText("确定")
        self.buttonBox.button(QDialogButtonBox.Cancel).setText("取消")
        self.comboBox.addItems(self.MainWindow.Layernames)
        self.barImg = np.array([])
        self.isSelecting = False
        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

    def import_graph(self):
        filepath = QFileDialog.getOpenFileName(self,"选择图像","","*.tif *.jpg *.png *.gif")[0]
        if filepath:
            self.lineEdit_barImg.setText(filepath)
            Import_Img = cv.imdecode(np.fromfile(filepath, dtype=np.uint8), cv.IMREAD_COLOR)
            self.barImg = cv.cvtColor(Import_Img, cv.COLOR_BGR2RGB)
            self.plot_data(self.barImg)
            possible_backgroundrgb = self.find_major_rgb(self.barImg)
            self.lineEdit_backgroundrgb.setText(str(possible_backgroundrgb))

    def find_major_rgb(self, Img):
        pixels = Img.reshape(-1, 3)
        df = pd.DataFrame(pixels, columns=['R', 'G', 'B'])
        counts = df.groupby(['R', 'G', 'B']).size().reset_index(name='counts')
        max_row = counts.loc[counts['counts'].idxmax()]
        major_rgb = [int(max_row['R']), int(max_row['G']), int(max_row['B'])]
        return major_rgb

    #画图
    def plot_data(self, Img):
        _dpi = 100
        view_size = self.graphicsView.size()
        self.figure = Figure(figsize=(view_size.width()/_dpi,view_size.height()/_dpi),dpi=_dpi)
        self.canvas = FigureCanvas(self.figure)
        self.scene.addWidget(self.canvas)
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        self.im = ax.imshow(Img, origin='upper')
        self.canvas.draw()
        self.canvas.mpl_connect('motion_notify_event', self.on_canvas_move) 
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)

    def change_flag(self):
        if self.isSelecting==True:
            self.isSelecting=False
            self.label_choose.setText("未开始选择")
            self.setCursor(Qt.ArrowCursor) 
            if self.barImg.size > 0:
                self.canvas.setCursor(Qt.ArrowCursor) 
        elif self.isSelecting==False:
            self.isSelecting=True
            self.label_choose.setText("开始选择")
            self.setCursor(Qt.CrossCursor) 
            if self.barImg.size > 0:
                self.canvas.setCursor(Qt.CrossCursor) 

    def on_canvas_move(self, event):
        if not event.inaxes:
            self.label_coord.setText("不在图像区域内")
            return
    
        row = int(event.ydata + 0.5)  
        col = int(event.xdata + 0.5)
        img_array = self.im.get_array()

        if 0 <= row < img_array.shape[0] and 0 <= col < img_array.shape[1]:
            r,g,b = img_array[row, col]
            self.label_coord.setText(f"行: {row}, 列: {col} | R: {r} G: {g} B: {b}")

    #点击画布展示matplotlib画图
    def on_canvas_click(self, event):
        if self.isSelecting:
            row = int(event.ydata + 0.5)  
            col = int(event.xdata + 0.5)
            point = (row,col)
            currentpointText = self.lineEdit_points.text()
            if currentpointText == "":
                self.lineEdit_points.setText(str(point))
            else:
                self.lineEdit_points.setText(currentpointText+","+str(point))

    #计算
    def accept(self):
        self.setWindowTitle("正在运行......")
        if self.lineEdit_barImg.text()=="" or self.comboBox.currentText()=="" or self.lineEdit_name.text()=="" or self.lineEdit_points.text()=="" or self.lineEdit_values.text()=="" or self.lineEdit_tolerance.text()=="":
            QMessageBox.warning(self, "警告","填写不完整！",QMessageBox.Ok)
        else:
            points = ast.literal_eval(self.lineEdit_points.text())
            values = ast.literal_eval(self.lineEdit_values.text())
            if len(points)!=len(values):
                QMessageBox.warning(self, "警告","点与对应值数量不一致！",QMessageBox.Ok)
            else:
                Tolerance = int(self.lineEdit_tolerance.text())
                background_value = np.float32(self.lineEdit_backgroundvalue.text())
                background_rgb = ast.literal_eval(self.lineEdit_backgroundrgb.text())
                outputName = self.lineEdit_name.text()
            
                comboBox_text = self.comboBox.currentText()
                index = self.MainWindow.Layernames.index(comboBox_text)   
                testImg = self.MainWindow.Layers[index]

                rgbs = self.getrgbs(points)
                Color_stretch = self.Colorstretch(testImg, rgbs, values, Tolerance, background_rgb, background_value)
                self.close()
                self.MainWindow.add_layer(outputName,Color_stretch)

    def Colorstretch(self, testImg, rgbs, values, Tolerance, background_rgb, background_value):
        rows,cols = testImg.shape[:2]
        Color_stretch = np.ones([rows,cols])*background_value
        for i in range(0,rows):
            for j in range(0,cols):
                current_rgb = testImg[i,j,:]
                if np.array_equal(current_rgb,background_rgb)==False:
                    rgbdiff = np.max(np.abs(rgbs-current_rgb),axis=1)
                    if np.min(rgbdiff)<Tolerance:
                        Index = np.argmin(rgbdiff)
                        Color_stretch[i,j] = values[Index]
        return Color_stretch
    
    def getrgbs(self, points):
        rgbs = np.array([self.barImg[point[0],point[1]] for point in points]).astype(np.float32)
        return rgbs
    
if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()