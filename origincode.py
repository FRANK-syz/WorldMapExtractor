import numpy as np
from matplotlib import pyplot as plt
from osgeo import gdal,osr
import cv2 as cv

import time

def SIFT(filepath,coordinate,fill_flag,surface_flag,target_rows,target_cols):

    #读取并投影源图像
    src_ds = gdal.Open("worldmap/Continent025.tif")

    warp_options = gdal.WarpOptions(
    dstSRS = coordinate,
    resampleAlg = gdal.GRA_Bilinear,
    format = "MEM"  
    )

    proj_ds = gdal.Warp("", src_ds, options=warp_options)  # 空字符串表示不生成文件
    continent = proj_ds.ReadAsArray()
    continent = np.where(continent<255,0,255)
    continent = continent.astype(np.uint8)
    srcImg = np.expand_dims(continent,2).repeat(3,axis=2)
    srcImg = cv.resize(srcImg, (target_cols, target_rows), interpolation=cv.INTER_LINEAR)
    src_ds = None
    proj_ds = None
    landmask = srcImg[:,:,0]
    
    if fill_flag != "fill":
        median = np.median(srcImg)
        sigma = 0.33 
        low_threshold = int(max(0, (1.0 - sigma) * median))
        high_threshold = int(min(255, (1.0 + sigma) * median))
        srcImg = cv.Canny(srcImg, low_threshold, high_threshold)
        srcImg = np.where(srcImg==255,0,255).astype(np.uint8)
        srcImg = np.expand_dims(srcImg,2).repeat(3,axis=2)

    #读取目标图像
    testImg = cv.imdecode(np.fromfile(filepath, dtype=np.uint8), cv.IMREAD_COLOR)
    if testImg is None:
        raise ValueError(f"无法读取图像: {filepath}")
    
    #转换为灰度图
    # top, bot, left, right = 0,0,0,0
    # srcImg = cv.copyMakeBorder(srcImg, top, bot, left, right, cv.BORDER_CONSTANT, value=(255, 255, 255))
    # testImg = cv.copyMakeBorder(testImg, top, bot, left, right, cv.BORDER_CONSTANT, value=(255, 255, 255))
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
    
    print("finish control points")

    #单应性矩阵计算
    rows,cols=srcImg.shape[0], srcImg.shape[1]
    MIN_MATCH_COUNT = 10
    if len(good) > MIN_MATCH_COUNT:
        src_pts = np.float32(pts2).reshape(-1, 1, 2)
        dst_pts = np.float32(pts1).reshape(-1, 1, 2)
        M, mask = cv.findHomography(src_pts, dst_pts, cv.RANSAC, 5.0)
        warpImg = cv.warpPerspective(testImg, M, (cols, rows),flags=cv.INTER_LINEAR,borderMode=cv.BORDER_CONSTANT,borderValue=(255, 255, 255))

        alpha = np.arange(1,cols+1).reshape(1,-1,1)/cols/2+0.25
        # alpha = 0.5
        overlap = srcImg*alpha+warpImg*(1 - alpha)
        overlap = overlap.astype(np.uint8)

        warpImg = cv.cvtColor(warpImg, cv.COLOR_BGR2RGB)
        overlap = cv.cvtColor(overlap, cv.COLOR_BGR2RGB)
        
        if surface_flag == "land":
            warpImg[landmask==255,:]=[255,255,255]
        elif surface_flag == "ocean":
            warpImg[landmask==0,:]=[255,255,255]

        # plt.figure(1)
        # plt.imshow(img3)
        # plt.figure(2)
        # plt.imshow(overlap)
        plt.figure(3)
        plt.imshow(warpImg)  
        plt.show()
        # np.save("warpImg.npy",warpImg)
        return warpImg
    else:
        print("Not enough matches are found - {}/{}".format(len(good), MIN_MATCH_COUNT))
        matchesMask = None

def Quickgreystrech(warpImg,barfile,min_value,max_value,background_rgb,fill_value):
    imggray = cv.cvtColor(warpImg, cv.COLOR_BGR2GRAY)
    barfig = cv.imread(barfile)
    barfig = cv.cvtColor(barfig, cv.COLOR_BGR2GRAY)
    
    startpoint = float(barfig[1924,3087])
    endpoint = float(barfig[1924,4261])
    # startpoint = 255
    # endpoint = 60
    backgroundpoint = barfig[0,0]
    k = (max_value-min_value)/(endpoint-startpoint)
    b = (endpoint*min_value-max_value*startpoint)/(endpoint-startpoint)

    Target_value = imggray*k+b
    Target_value = np.where(imggray==backgroundpoint,fill_value,Target_value)
    
    plt.imshow(Target_value)
    plt.show()
    return Target_value

def Colorstrech(warpImg,barfile,min_value,max_value,Tolerance,background_rgb,fill_value):
    barfig = cv.imread(barfile)
    barfig = cv.cvtColor(barfig, cv.COLOR_BGR2RGB)
    barcolor = barfig[1924,3087:4261+1,:].astype(np.float16)
    
    rows,cols = warpImg.shape[:2]
    Target_value = np.ones([rows,cols])*fill_value
    for i in range(0,rows):
        for j in range(0,cols):
            current_rgb = warpImg[i,j,:]
            if np.array_equal(current_rgb,background_rgb)==False:
                rgbdiff=np.max(np.abs(barcolor-current_rgb),axis=1)
                if np.min(rgbdiff)<Tolerance:
                    Index = np.argmin(rgbdiff)
                    Target_value[i,j] = (Index+1)/len(barcolor)*(max_value-min_value)+min_value

    plt.imshow(Target_value)
    plt.show()  
    return Target_value

def Colorclassify(warpImg,barfile,value_array,coord_array,Tolerance,background_rgb,fill_value):
    barfig = cv.imread(barfile)
    barfig = cv.cvtColor(barfig, cv.COLOR_BGR2RGB)
    rgb_array = np.array([barfig[i[0],i[1]] for i in coord_array]).astype(np.float16)

    rows,cols = warpImg.shape[:2]
    Target_value = np.ones([rows,cols])*fill_value
    for i in range(0,rows):
        for j in range(0,cols):
            current_rgb = warpImg[i,j,:]
            if np.array_equal(current_rgb,background_rgb)==False:
                rgbdiff=np.max(np.abs(rgb_array-current_rgb),axis=1)
                if np.min(rgbdiff)<Tolerance:
                    Index = np.argmin(rgbdiff)
                    Target_value[i,j] = value_array[Index]
    plt.figure(1)
    plt.imshow(Target_value)
    plt.colorbar(shrink=0.6)
    plt.show()  
    return Target_value 

warpImg = SIFT('worldmap/edge3.png','EPSG:4326',"fil","land",720,1440)
# Greystreched = Quickgreystrech(warpImg,'edge3.png',min_value=0,max_value=60,background_rgb=np.array([255,255,255]),fill_value=0)
Colorstreched = Colorstrech(warpImg,'worldmap/edge3.png',min_value=0,max_value=60,Tolerance=70,background_rgb=np.array([255,255,255]),fill_value=0)
# Colorclassified = Colorclassify(warpImg,"worldmap/colorbar2.png",
#                                 value_array=np.array([5,15,25,35,45,75,125,175,225,275]),
#                                 coord_array=np.array([[3010,300],[3010,580],[3010,870],[3010,1150],[3010,1420],[3010,1700],[3010,2000],[3010,2260],[3010,2540],[3010,2820]]),
#                                 Tolerance=50,background_rgb=np.array([255,255,255]),fill_value=0)

