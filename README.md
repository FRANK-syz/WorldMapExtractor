# WorldMapExtractor · 世界地图提取器

**基于图像特征识别的图片转地理栅格文件工具（GIS 期末作品）**

`WorldMapExtractor` 是一个可交互的 Python GUI 工具，能够自动识别科学文献中的世界地图图片，根据图片提供颜色条（Colorbar）的类型，将论文/文献中的地图图片还原为可用于科研的、具有实际数值的地理栅格数据（GeoTIFF）。当在文献中遇到关键地图数据并未公开提供下载时，本工具提供了一种"试图还原数据"的可行方案。该工具仅为娱乐，缺乏泛用性。本工具仅提供WGS 1984坐标系的世界地图提取，其他坐标系难以支持
注意：科学文献中世界地图的颜色条存在主观设置和信息损失，还原后不能保证完整性和还原性

---

## 项目背景

地理科研中，许多文献里的可视化地图数据往往不提供公开下载链接，发邮件向通讯作者索取也常常得不到回复，手动按像元人眼复现数据既困难又耗时。本系统试图解决这一问题：

- 保存文献中的高清地图图片
- 一键提取世界地图区域，并与标准世界地图大小对齐
- 删除多余空白或图外信息
- 读取图中像元值，反推地图数据的实际值
- 输出可供 **ArcGIS** 正常读取和显示的地理栅格文件（`.tif`）

---

## 功能特性

系统集成 **OpenCV、GDAL、Matplotlib 和 PyQt5** 等 Python 库，提供三大核心功能：

### 1. 图像导入与显示
- 仿 ArcGIS 的界面设计，树状列表按图层管理导入的图片
- 支持 JPG / PNG / TIF 等常见图像格式
- 勾选图层可实时叠加 / 隐藏对应图层
- 画布自动显示鼠标悬浮位置的行列号及像元 RGB / 灰度值
- 点击画布可弹出 Figure 窗口进行缩放平移观察

### 2. 图像自动配准（SIFT）
- 采用 **SIFT** 算法识别目标图像与基准世界地图的海陆轮廓特征
- 支持基准地图坐标系转换、行列号设定与重采样
- 区分"陆地内部均匀填充"与"海陆边缘描边"两种地图特征，提高配准精度
- 输出特征点匹配、连线对比、透明度叠加等质量预览
- 通过匹配点构建**单应性矩阵**，将目标图像逐像元配准到世界地图行列号与海陆位置

### 3. 图像数值映射（读取颜色条还原实际值）
- **快速灰度映射**：灰度图线性映射，效率极高，适合灰度线性连续的颜色条
- **彩色映射**：逐像元匹配颜色条 RGB 序列，适合任意线性连续的彩色颜色条
- **彩色分类**：离散分类颜色条，按颜色类别均值赋值，适合分类色图

### 保存与导出
- 将结果导出为 JPG / PNG 等常见图像格式
- 或按基准世界地图的地理坐标系导出为 **GeoTIFF**（ArcGIS 可正常识别，用于后续科研计算）

---

## 界面设计

| 界面 | 说明 |
|------|------|
| 主界面 | 上方菜单提供功能入口，左侧 ArcGIS 风格树状图层列表，右侧画布可视化，右下角显示行列号与 RGB / 灰度值 |
| 配准对话框 | 输入基准世界地图与目标图像，设置行列号、坐标系、背景值等参数，可预览配准对比与叠加图 |
| 灰度快速映射对话框 | 提供颜色条最值与其对应的灰度值、实际值 |
| 彩色映射对话框 | 手动选择颜色条极值坐标及其实际值，支持水平 / 垂直颜色条 |
| 彩色分类对话框 | 手动添加所有颜色条分类及其对应实际值，数量无上限 |

---

## 技术原理

### Canny 边缘检测
John F. Canny 于 1986 年提出的多级边缘检测算法：高斯平滑去噪 → Sobel 计算梯度 → 非极大值抑制 → 双阈值边缘分级 → 连接弱边缘。用于对基准世界地图提取边缘，匹配边缘特征明显的目标图像。

### SIFT 特征匹配
David G. Lowe 于 1999 年提出的尺度不变特征变换：构建高斯金字塔 → 阈值极值点检测 → 极值点方向求解 → 关键点描述符构建。通过匹配器筛选高质量特征点，实现目标图像与基准地图的特征匹配。

### 单应性矩阵
通过 3×3 单应性矩阵实现图像间的投影变换，将目标图像逐像元配准至基准世界地图。

### 三种数值映射算法
- **灰度快速映射**：`Y = X*(y2-y1)/(x2-x1) + (x2*y1-x1*y2)/(x2-x1)`，将灰度值 `[Xmin, Xmax]` 线性映射到实际值 `[Ymin, Ymax]`
- **彩色映射**：在容差范围内，逐像元寻找与颜色条 RGB 最接近的行 / 列序号，按 `Y=(Index+1)/Length*(y2-y1)+y1` 线性映射实际值
- **彩色分类**：在容差范围内，逐像元匹配最近的分类并赋予该分类对应的实际值

---

## 环境依赖

| 依赖 | 说明 |
|------|------|
| Python | ≥ 3.10 |
| PyQt5 | 图形用户界面 |
| opencv-python | 图像读取、SIFT 匹配、单应性矩阵、Canny 边缘检测 |
| GDAL | 地理栅格数据读写与坐标系转换（Windows 建议用 conda 或 gdalwhls 安装） |
| matplotlib | 数据可视化 |
| numpy | 数组运算 |

```bash
# 建议使用 conda 或 venv 创建环境后安装
pip install PyQt5 opencv-python matplotlib numpy
# GDAL 在 Windows 上的安装（示例，任选其一）
conda install -c conda-forge gdal
# 或：pip install --extra-index-url https://girder.github.io/large_image_wheels GDAL
```

---

## 快速开始

克隆仓库到本地：

```bash
git clone https://github.com/FRANK-syz/WorldMapExtractor.git
cd WorldMapExtractor
```

运行源码：

```bash
python WorldMapExtractor.py
```

> 提示：完整打包客户端为 `WorldMapExtractor.exe`（约 372 MB，独立可运行）。

---

## 使用流程

1. **导入图片**：将文献中保存的地图高清图片导入，作为图层显示在画布上
2. **SIFT 配准**：选择基准世界地图与目标图像，设置输出行列号（如 `720×1440`，即 0.25°×0.25°）、坐标系（如 WGS 1984 / EPSG:4326）、背景值；`edge*.png` 选"边缘"选项、`fill*.png` 选"填充"选项；预览确认后生成配准图像
3. **数值映射**：根据颜色条类型选择灰度快速映射 / 彩色映射 / 彩色分类，读取或选择颜色条极值与实际值
4. **导出保存**：将还原结果导出为 GeoTIFF，可被 ArcGIS 读取与可视化

默认示例数据及说明：

- `worldmap/continent025.tif`：基准世界地图栅格文件
- `worldmap/edge*.png`：海陆轮廓呈边缘特征的示例图片（配准选"边缘"）
- `worldmap/fill*.png`：海陆轮廓呈填充特征的示例图片（配准选"填充"）
- `worldmap/WebMercator.png`：Web 墨卡托投影测试图片（GDAL 在 exe 环境坐标转换存在限制，暂放弃支持）

---

## 输出结果

系统可将配准后的图像还原为含有实际值的全球栅格，典型输出为 **720×1440（0.25°×0.25°）** 的 GeoTIFF，可供 ArcGIS 正常识别、可视化与后续科研计算。

> 受还原手段与图像存储限制，结果无法 100% 完全还原原始数据，但可辅助科研；将还原数据与原数据对比可进一步量化还原精度。

---

## 项目结构

```
WorldMapExtractor/
├── WorldMapExtractor.py      # Python 主程序源码
├── origincode.py             # 原始/参考代码
├── WorldMapExtractor.ui      # Qt Designer 主界面
├── ColorclassifyDialog.ui    # 彩色分类对话框界面
├── ColorscaleDialog.ui       # 彩色映射对话框界面
├── GreyscaleDialog.ui        # 灰度快速映射对话框界面
├── SIFTDialog.ui             # SIFT 配准对话框界面
├── WorldMapExtractor.spec    # 打包配置（PyInstaller）
└── worldmap/                 # 基准地图栅格与示例图片数据
```

---

## 说明与局限性

- 系统可还原的图片类型有限，还原精度有待进一步验证
- 在目标图片或导出图片极大 / 极小时，还原能力仍存在不确定
- 界面设计基础欠缺，当前版本仍有待完善与遗留问题

---

## 参考

- John Canny. *A Computational Approach to Edge Detection*. Readings in Computer Vision, 1987, 8:184-203.
- David G. Lowe. *Object Recognition from Local Scale-Invariant Features*. Proceedings of the Seventh IEEE International Conference on Computer Vision, 1999, 2:1150-1157.
