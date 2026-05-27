# 人脸识别考勤系统 — 优化日志

## 一、模型与推理层

### 1.1 模型升级：buffalo_sc → buffalo_l

**文件：** `config.py:41`

```python
FACE_MODEL_NAME = 'buffalo_l'  # ResNet50 backbone，602M人脸训练
```

buffalo_sc 使用 MobileFaceNet（轻量），buffalo_l 使用 ResNet50（10倍参数量）。ArcFace 512维嵌入在 ResNet50 上区分度显著更高，同一人余弦相似度可从 0.70 提升至 0.85+。

**代价：** 模型文件约 300MB，首次运行 InsightFace 自动下载。推理速度慢 2-3 倍，通过跳帧补偿。

---

### 1.2 检测分辨率翻倍：DET_SIZE 320 → 640

**文件：** `config.py:42`

```python
FACE_DET_SIZE = (640, 640)
```

SCRFD 检测器在 640×640 上定位人脸框和 5 点关键点，比 320×320 更精确。更准的关键点 → 更准的仿射对齐 → ArcFace 编码质量更高。

**原理：** ArcFace 输入始终是 112×112，但人脸对齐的质量取决于关键点精度。640 输入下关键点定位误差减小，对齐后人脸更标准，编码区分度更高。

---

### 1.3 GPU 推理：onnxruntime-gpu + cuDNN

**依赖安装：**

```bash
pip uninstall onnxruntime -y         # 卸载 CPU 版
pip install onnxruntime-gpu           # 安装 GPU 版（内置 CUDA 12.x 支持）
pip install nvidia-cudnn-cu12         # cuDNN 9.x，onnxruntime-gpu 依赖
```

**DLL 路径注册（`main.py:8-16`）：**

```python
# 必须在 import onnxruntime 之前执行
# os.add_dll_directory() 对原生 DLL 加载无效，必须用 PATH
_site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')
for _lib in ['nvidia/cudnn/bin', 'nvidia/cublas/bin']:
    _path = os.path.join(_site_packages, _lib)
    if os.path.isdir(_path) and _path not in os.environ.get('PATH', ''):
        os.environ['PATH'] = _path + ';' + os.environ.get('PATH', '')
```

**关键踩坑：** `os.add_dll_directory()` 只影响 Python ctypes 加载，`onnxruntime_providers_cuda.dll` 是原生 Windows DLL 加载，只认 PATH 环境变量。必须在 `import onnxruntime` **之前**把 cuDNN/bin 加入 PATH。

**FaceEncoder 中的 provider 选择（`core/face_encoder.py:37-38`）：**

```python
if 'CUDAExecutionProvider' in ort.get_available_providers():
    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
```

GPU 推理生效后日志显示 `providers: ['CUDAExecutionProvider', 'CPUExecutionProvider']`。

**GPU 占用率说明：** 人脸识别是"推理"不是"训练"，GPU 只做 SCRFD 检测 + ArcFace 编码（每帧几十毫秒），其余时间闲置等 CPU 喂下一帧。20-30% GPU 占用是正常的。

---

## 二、匹配策略层

### 2.1 三区阈值分类

**文件：** `core/face_matcher.py:25-45`，`config.py:17-21`

```python
# config.py
FACE_RECOGNITION_CONFIDENT = 0.55   # 高置信区：直接确认
FACE_RECOGNITION_UNCERTAIN = 0.42   # 不确定区下限：低于此值直接拒绝
FACE_RECOGNITION_TOLERANCE = 0.42   # 兼容旧接口
```

```python
# face_matcher.py
def _classify_match(self, best_sim, margin):
    if best_sim >= self.confident:        # ≥0.55 → 直接确认
        return True, float(best_sim)
    elif best_sim >= self.tolerance:      # 0.42~0.55 → 不确定区
        if margin >= 0.08:                # 最佳-次佳差距够大才确认
            return True, float(best_sim * 0.9)
        else:
            return False, float(best_sim)  # margin不够，拒绝
    else:                                  # <0.42 → 拒绝
        return False, float(best_sim)
```

| 区间 | 余弦相似度 | 行为 |
|------|-----------|------|
| 高置信区 | ≥ 0.55 | 直接确认 |
| 不确定区 | 0.42 ~ 0.55 | margin ≥ 0.08 才确认 |
| 拒绝区 | < 0.42 | 直接拒绝 |

**为什么需要 margin 检查：** 58 人的课堂，两个人的人脸编码可能碰巧相似（cos_sim ≈ 0.50）。如果最佳匹配 0.50 而次佳 0.48，说明无法区分这两个人，应该拒绝而非误识。

### 2.2 预计算矩阵加速

**文件：** `core/face_matcher.py:21-23` 的 `update_database()` 方法

```python
self._known_matrix = np.array(encodings, dtype=np.float32)
norms = np.linalg.norm(self._known_matrix, axis=1, keepdims=True)
self._known_matrix = self._known_matrix / (norms + 1e-10)
```

启动时一次性对 58 个编码做 L2 归一化，匹配时只需一次矩阵乘法 `queries @ known_matrix.T`，O(1) 完成 58 人比对。

### 2.3 批量匹配

**文件：** `core/face_matcher.py` `match_multiple_batch()` 方法

一帧内检测到多人脸时，所有查询编码堆叠成矩阵，单次 `(N_queries, 512) @ (512, N_known)` 完成所有人脸比对，避免逐个循环。

---

## 三、注册质量层

### 3.1 全分辨率注册：REGISTRATION_RESIZE_SCALE = 1.0

**文件：** `config.py:36`

```python
FACE_REGISTRATION_RESIZE_SCALE = 1.0  # 注册时不缩放
```

注册是离线一次性操作，不缩放直接送检测器，人脸框和关键点精度最大化。

### 3.2 Top-N 质量选优

**文件：** `config.py:38`，`core/face_encoder.py` `encode_with_quality()`

```python
FACE_REGISTRATION_TOP_N = 5  # 只取质量最高的前N张
FACE_REGISTRATION_MIN_QUALITY = 0.30
```

每人 10 张不同角度的注册照 → 检测+编码 → 过滤质量 < 0.30 → 按质量分排序取前 5 → 离群值剔除 → 质量加权平均。

**质量评分维度（`core/face_aligner.py:134-199`）：**
- 姿态（40%）：5 点关键点推算 roll/yaw，侧脸扣分
- 清晰度（30%）：Laplacian 方差
- 检测置信度（15%）：SCRFD det_score
- 亮度（15%）：过暗/过亮扣分

### 3.3 离群值剔除

**文件：** `core/face_encoder.py` `encode_with_quality()` 第 2 步

```python
outlier_sim = 0.30  # FACE_REGISTRATION_OUTLIER_SIM
mean_enc = np.mean(encodings, axis=0)
sims = encodings @ mean_enc
mask = sims > outlier_sim  # 保留与均值相似度 > 0.30 的编码
```

防止某张照片检测错误（非该学生的人脸）污染编码。

---

## 四、显示渲染层（性能关键路径）

### 4.1 全链路 BGR，零色彩空间转换

**文件：** `gui/attendance_panel.py:591-627` `_draw_label()`

不将整帧转为 RGB 再转回来。流程：

```
摄像头 BGR 帧
  → cv2.rectangle() 画 BGR 框
  → PIL 只渲染文字标签小 RGBA 块（几十像素）
  → label_rgba[:, :, 2::-1] 翻成 BGR 通道
  → alpha 混合到 BGR 帧的标签位置
  → QImage.Format_BGR888 直接显示
```

之前每帧做 `cv2.cvtColor(BGR→RGB) + PIL Image + cv2.cvtColor(RGB→BGR)`，1280×720×3 的全帧两次色彩转换完全消除。

### 4.2 结果不变时零开销

**文件：** `gui/attendance_panel.py:638-640`

```python
if self.last_results == self._last_drawn_results and self._cached_display is not None:
    self.display_image(self._cached_display)
    return
```

识别结果没变 → 跳过 `frame.copy()`、`cv2.rectangle()`、`_draw_label()`，直接复用上一帧。

### 4.3 QPixmap 数据指针缓存

**文件：** `gui/attendance_panel.py:656-670`

```python
data_ptr = image.ctypes.data
if data_ptr == self._last_data_ptr and self._cached_pixmap is not None:
    self.video_label.setPixmap(self._cached_pixmap)
    return
```

同一块内存数据 → 跳过 `QImage` 构造和 `scaled()` 缩放，直接 `setPixmap`。

### 4.4 FastTransformation 替代 SmoothTransformation

```python
q_image.scaled(label_size, Qt.KeepAspectRatio, Qt.FastTransformation)
```

`SmoothTransformation` 是双三次插值，`FastTransformation` 是最近邻。视觉差异极小，CPU 开销差一个量级。

---

## 五、考勤逻辑层

### 5.1 出勤率分母修正

**文件：** `gui/attendance_panel.py:702-722`

**修复前：** 出勤率 = (正常 + 迟到) / 打卡记录数 → 3人打卡 = 100%
**修复后：** 出勤率 = 去重已打卡人数 / 学生总人数

```python
total_students = len(self.ctx.student_service.get_all_students())
checked_in = len(normal_students) + len(late_students)
attendance_rate = checked_in / total_students * 100
```

### 5.2 学号+姓名联合去重

```python
key = (record['student_id'], record['student_name'])
```

同一学生的多条考勤记录只算一个人。同时有正常和迟到记录时按迟到计。

### 5.3 识别结果持久化

**文件：** `gui/attendance_panel.py:562-565`

```python
# 有结果才更新，空结果保留上次识别的人名不闪
if results:
    self.last_results = results
```

识别线程空帧返回时不清除 `last_results`，人名保持显示直到下一次有效识别。

---

## 六、CLAHE 光照预处理（可选功能）

**文件：** `utils/preprocessing.py`（新建），`core/face_encoder.py` 各编码入口

```python
FACE_PREPROCESSING_ENABLED = False  # 默认关闭
FACE_PREPROCESSING_CLAHE_CLIP = 2.0
FACE_PREPROCESSING_CLAHE_TILE = (8, 8)
```

在 LAB 色彩空间的 L 通道做自适应直方图均衡化，消除逆光/暗光影响。

**⚠️ 启用约束：** 注册和考勤必须用同一流水线。启用 CLAHE 后必须删库重导：

```
FACE_PREPROCESSING_ENABLED = True
→ 删除 face_attendance.db
→ 运行 import_all_data.py
```

CLAHE 在缩略图上执行（`detect_and_encode` 先 resize 再做 CLAHE），避免全分辨率处理拖慢 CPU。

---

## 七、性能参数调优

**文件：** `config.py`

| 参数 | 值 | 说明 |
|------|-----|------|
| `FACE_ATTENDANCE_RESIZE_SCALE` | 0.5 | 考勤帧缩至 640×360 送检测 |
| `ATTENDANCE_FRAME_SKIP` | 10 | 每 10 帧识别一次（~3fps） |
| `FACE_REGISTRATION_RESIZE_SCALE` | 1.0 | 注册全分辨率 |
| `FACE_REGISTRATION_TOP_N` | 5 | 每人取最优 5 张 |
| `FACE_REGISTRATION_MIN_QUALITY` | 0.30 | 注册质量门槛 |
| `FACE_DET_SIZE` | (640, 640) | 检测分辨率 |
| `CAMERA_WIDTH/HEIGHT` | 1280/720 | 原始采集分辨率不变 |

**SimpleTracker 参数（`services/attendance_service.py:21`）：**
- `max_lost=3`：丢失 3 帧才放弃跟踪
- `iou_threshold=0.3`：IoU 匹配阈值
- `vote_window=3`：滑动窗口投票平滑

跳帧 10 时识别频率约 3fps。跟踪器在 3fps 下仍能稳定跟踪，因为 `max_lost=3` 允许约 1 秒的空窗。

---

## 八、环境依赖

```bash
# requirements.txt 核心依赖
onnxruntime-gpu>=1.26.0    # GPU 推理（替代 onnxruntime）
nvidia-cudnn-cu12           # cuDNN 9.x DLL
insightface>=1.0.1          # SCRFD + ArcFace
opencv-python>=4.5.0
PyQt5>=5.15.0
SQLAlchemy>=1.4.0
numpy>=1.19.0
Pillow                       # 中文文字渲染
openpyxl                     # Excel 导出
```

**硬件要求：** NVIDIA GPU + CUDA 驱动 ≥ 12.x，4GB+ 显存。
