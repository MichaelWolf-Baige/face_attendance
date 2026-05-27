# 人脸识别考勤系统 V3 —— 完整架构文档

---

# 版本总览：V2 → V3 核心升级

| 维度 | V2 | V3 |
|------|-----|-----|
| 人脸检测 | dlib HOG/CNN | InsightFace SCRFD (5点关键点) |
| 特征提取 | 128维 (dlib) | 512维 (ArcFace ResNet50) |
| 推理加速 | CPU only | GPU (onnxruntime-gpu + CUDA/cuDNN) |
| 匹配算法 | 欧氏距离逐一比对 | 余弦相似度 + 预计算矩阵 + 批量匹配 |
| 匹配策略 | 单阈值 (0.5) | 三区分类 (confident/uncertain/reject + margin) |
| 注册质量 | 简单5次jitter平均 | 5点关键点质量评分 + Top-N选优 + 离群值剔除 |
| 人脸对齐 | 无 | 5点仿射对齐到ArcFace 112×112模板 |
| 姿态估计 | 无 | roll/yaw/frontal_score |
| 光照处理 | 无 | CLAHE (LAB空间L通道自适应直方图均衡) |
| 人脸跟踪 | 无 | SimpleTracker (IoU匹配 + 3帧投票平滑) |
| 跳帧策略 | 无 | FRAME_SKIP=10 (约3fps识别, 30fps显示) |
| 摄像头 | 640×480 | 1280×720 |
| 架构模式 | 全局单例 + 各自new实例 | AppContext 集中注入 |
| 密码管理 | bcrypt 直接调用 | security.py 工具模块封装 |
| 手动补签 | 无 | MakeupCheckInDialog (批量选择未打卡学生) |
| 班级筛选 | 无 | 全界面班级过滤 + 人脸库按班级刷新 |
| 出勤率 | 打卡数/打卡记录数 (不准) | 去重已打卡人数/学生总人数 |
| 显示渲染 | BGR→RGB→PIL→RGB→BGR 全帧转换 | 全链路BGR + 仅文字标签PIL小区域渲染 |
| 缓存机制 | 60秒TTL人脸库缓存 | 预计算归一化矩阵 + 识别结果不变零开销复用 |
| 数据库 | 4表, 无索引 | 4表 + 4个复合索引 |
| config.py | 47行, 7组参数 | 79行, 10组参数 + settings.json覆盖 |

---

# 第一层：`config.py` —— 重构后的决策中心

V3 的 config.py 从 47 行扩展到 79 行，参数从 7 组增加到 10 组。最关键的改动是**人脸识别引擎彻底换血**。

## 第一行：`BASE_DIR`

```python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
```

与 V2 相同，确保路径一致性。但 V3 新增了 `DATA_DIR`：

```python
DATA_DIR = os.path.dirname(BASE_DIR)  # 数据目录(学生照片)
```

## 第一组：数据库路径

```python
DATABASE_PATH = os.path.join(BASE_DIR, 'face_attendance.db')
```

不变，但 V3 的数据库 schema 新增了 4 个性能索引。

## 第二组：人脸识别核心参数（V3 最大变化）

```python
FACE_RECOGNITION_CONFIDENT = 0.55   # 高置信阈值 (余弦相似度 ≥0.55 直接确认)
FACE_RECOGNITION_UNCERTAIN = 0.55   # 不再有不确定区
FACE_RECOGNITION_TOLERANCE = 0.55   # 统一阈值
```

**与 V2 的本质区别**：V2 使用欧氏距离 (阈值 0.5, 越小越像)，V3 使用**余弦相似度** (阈值 0.55, 越大越像)。这是两种完全不同的度量空间。

V3 实际使用**三区阈值策略**（在 `face_matcher.py` 中实现）：
```
余弦相似度 ≥ 0.55  → 高置信区：直接确认
余弦相似度 < 0.55  → 拒绝区：直接拒绝
```

不确定区合并入拒绝区（V3 经过多次优化后，发现 buffalo_l + 512 维 ArcFace 区分度足够高，不需要不确定缓冲带）。

## 第三组：图像预处理（V3 新增）

```python
FACE_PREPROCESSING_ENABLED = False      # CLAHE 预处理开关
FACE_PREPROCESSING_CLAHE_CLIP = 2.0     # 对比度限制
FACE_PREPROCESSING_CLAHE_TILE = (8, 8)  # CLAHE 网格
FACE_PREPROCESSING_DENOISE = True       # 轻度降噪
```

在 LAB 色彩空间的 L 通道做自适应直方图均衡化，消除教室逆光/暗光影响。默认关闭，启用后须删库重建。

## 第四组：多图注册（V3 核心升级）

```python
FACE_REGISTRATION_SHOTS = 3
FACE_REGISTRATION_MIN_QUALITY = 0.30
FACE_REGISTRATION_OUTLIER_SIM = 0.30
FACE_REGISTRATION_RESIZE_SCALE = 1.0    # 注册全分辨率，不缩放
FACE_REGISTRATION_FALLBACK = True
FACE_REGISTRATION_TOP_N = 5             # 只取质量最高的前N张
```

对比 V2 的混合策略（CNN注册 + HOG考勤），V3 完全取消了混合策略。**原因**：InsightFace 的 SCRFD + ArcFace 速度快到不需要分场景——注册和考勤用同一个模型，区别在于注册用全分辨率+mulit-shot质量选优，考勤用跳帧+缩放。

## 第五组：InsightFace 模型配置（V3 新增）

```python
FACE_MODEL_NAME = 'buffalo_l'      # ResNet50 (高精度) 或 buffalo_sc (MobileFaceNet快速)
FACE_DET_SIZE = (640, 640)         # 检测输入尺寸
```

buffalo_l 使用 ResNet50 backbone，602M 人脸训练，模型文件约 300MB。首次运行 InsightFace 自动下载。

## 第六组：考勤帧处理（V3 新增）

```python
ATTENDANCE_FRAME_SKIP = 10  # 每N帧处理一次
FACE_MIN_FACE_SIZE = 80     # 最小人脸像素尺寸
```

跳帧 10 意味着识别频率约 3fps，但通过 SimpleTracker（max_lost=3, vote_window=3）保证不丢人。显示仍然是 30fps。

## 第七组：摄像头（升级）

```python
CAMERA_WIDTH = 1280   # V2: 640
CAMERA_HEIGHT = 720   # V2: 480
```

分辨率翻倍。但考勤识别时通过 `FACE_ATTENDANCE_RESIZE_SCALE = 0.5` 缩到 640×360 送检测。

## 第八组：业务规则

```python
ATTENDANCE_COOLDOWN = 10
LATE_THRESHOLD_MINUTES = 15
```

与 V2 相同。

## 第九组：GUI 和日志

```python
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
THEME_COLOR = '#2196F3'
REFRESH_INTERVAL_MS = 5000
LOG_LEVEL = 'INFO'
```

与 V2 相同。

## 第十组：外部配置覆盖（V3 新增）

```python
_CONFIG_FILE = os.path.join(BASE_DIR, 'settings.json')
if os.path.exists(_CONFIG_FILE):
    with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
        overrides = json.load(f)
    for key, value in overrides.items():
        if key.isupper() and key in globals():
            globals()[key] = value
```

支持通过 `settings.json` 文件覆盖任何 config 变量，无需修改代码。

## 小结

```
config.py = 79行 = 10组参数

路径       → BASE_DIR, DATA_DIR, DATABASE_PATH
识别核心   → 余弦相似度阈值 0.55 (三区分类)
预处理     → CLAHE (默认关闭)
多图注册   → 全分辨率 + Top-N质量选优 + 离群值剔除
模型配置   → buffalo_l + det_size(640,640)
帧处理     → FRAME_SKIP=10 + min_face=80
摄像头     → 1280×720
业务规则   → 10秒冷却 + 15分钟迟到 (不变)
界面       → 1200×800 + 蓝色主题 (不变)
外部覆盖   → settings.json 动态覆盖
```

**V2→V3 关键思想转变**：从"注册用CNN求准、考勤用HOG求快"的二段式，升级为"统一高精度模型 + 注册质量选优 + 考勤跳帧加速"的模式。

---

# 第二层：`database/` —— 数据骨架升级

## 四张表的 ER 关系

与 V2 相同的四表结构，但 V3 有重要改进：

### 表结构变化

```diff
Student:
- face_encoding: 128维 float64 = 1024 bytes (dlib)
+ face_encoding: 512维 float32 = 2048 bytes (ArcFace)
+ 新增 Index (student_id)

AttendanceRecord:
+ 新增 4 个复合索引:
  - idx_attendance_student_time (student_id, check_time)
  - idx_attendance_course (course_id)
  - idx_attendance_check_time (check_time)
  - idx_attendance_status (status)
```

### BLOB 互转函数的兼容性升级

```python
def blob_to_encoding(blob: bytes) -> Optional[np.ndarray]:
    blob_len = len(blob)
    if blob_len == 2048:     # 512 × 4 = InsightFace ArcFace float32
        return np.frombuffer(blob, dtype=np.float32).copy()
    if blob_len == 1024:     # 128 × 8 = dlib float64 (向后兼容)
        return np.frombuffer(blob, dtype=np.float64).copy()
    # 未知大小，尝试 float32
    ...
```

**向后兼容**：V3 能读取 V2 数据库中的 dlib 编码，升级时不需要清空数据库。

### 新增查询能力

```python
def get_all_face_encodings(self, class_name: str = None):
    # V3 新增: 支持按班级过滤人脸库
    q = session.query(Student).filter(Student.face_encoding.isnot(None))
    if class_name:
        q = q.filter(Student.class_name == class_name)
```

班级过滤使得多班级场景下可以只加载特定班级的人脸库，减少匹配干扰。

### 学号自然排序

```python
def _natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]
```

解决 `1-10 > 1-2` 的字典序问题。

### 小结

```
database/
├── models.py       ← 4张ORM表 + 4个复合索引，encoding从128维→512维
└── db_manager.py   ← BLOB互转兼容新旧编码, 班级过滤, 自然排序, 批量导出

V2→V3 核心变化:
1. 人脸特征: 128维 → 512维 (dlib → ArcFace)
2. 性能索引: 0 → 4个复合索引
3. 向后兼容: 自动识别 float32/float64 BLOB 长度
4. 班级过滤: get_all_face_encodings 支持 class_name 参数
```

---

# 第三层：`core/` —— 人脸识别四件套 + 人脸对齐

V3 的 core 层从 3 个文件扩展到 **4 个文件**：

```
core/
├── face_detector.py   → InsightFace SCRFD 检测
├── face_encoder.py    → ArcFace 512维编码 + 质量加权 + 统一流水线
├── face_matcher.py    → 余弦相似度 + 预计算矩阵 + 三区阈值 + 批量匹配
└── face_aligner.py    → 5点关键点对齐 + 姿态估计 + 质量评估 (新增)
```

## 核心引擎：从 dlib 到 InsightFace

V3 最大的技术栈变化——不再使用 `face_recognition`（dlib），改用 `insightface`（ArcFace + SCRFD）。

```python
# 模块级单例，detector 和 encoder 共享同一个模型实例
_face_model = None

def _get_face_model():
    global _face_model
    if _face_model is None:
        import insightface
        providers = ['CPUExecutionProvider']
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        _face_model = insightface.app.FaceAnalysis(
            name='buffalo_l', providers=providers
        )
        _face_model.prepare(ctx_id=0, det_size=(640, 640))
    return _face_model
```

**模型单例共享**：FaceDetector 和 FaceEncoder 共享同一个 InsightFace 模型实例，避免重复加载 ~300MB 的模型文件。通过 `set_model_config()` 在模型加载前注入配置。

GPU 推理的关键路径：`main.py` 在导入 onnxruntime 之前将 cuDNN bin 目录加入 PATH 环境变量（非 `os.add_dll_directory()`，因为 onnxruntime 的 GPU provider DLL 是原生 Windows 加载）。

## FaceDetector —— V3 简化

```python
class FaceDetector:
    def __init__(self, model=None, resize_scale=None):
        self.resize_scale = resize_scale or config.FACE_ATTENDANCE_RESIZE_SCALE

    def detect(self, image, resize_scale=None):
        # SCRFD 检测 → bbox → (top, right, bottom, left)
        model = _get_face_model()
        faces = model.get(small)
```

**与 V2 的关键区别**：
- V2 需要手动指定 HOG/CNN 模型，V3 统一使用 SCRFD（更快、更准）
- V2 需要 BGR→RGB 手动转换，V3 InsightFace 内部处理
- V3 新增 `detect_with_details()` 返回质量分 + 检测置信度
- V3 新增 `detect_fast()` 自适应缩放

## FaceEncoder —— V3 最复杂的核心模块

V3 的 FaceEncoder (414行) 比 V2 (约80行) 膨胀了 5 倍。核心新增：

### 统一检测+编码流水线

```python
def detect_and_encode(self, image, max_num=10, resize_scale=None):
    # 一次 model.get() 同时完成检测+编码 (省掉一次 SCRFD+ArcFace前向传播)
    faces = model.get(small, max_num=max_num)
    for face in faces:
        emb = face.embedding           # 512维 ArcFace 嵌入
        emb = emb / np.linalg.norm(emb) # L2归一化
        landmark = face.kps            # 5点关键点
        pose = FaceAligner.estimate_pose(landmark)
        quality = FaceAligner.assess_quality(face_region, landmark, det_score)
        aligned_face = FaceAligner.align_face(image, landmark)
```

一个方法返回：人脸框 + 编码 + 关键点 + 姿态 + 质量 + 对齐后人脸。上层只用调一次，不关心内部细节。

### 质量加权编码（注册专用）

```python
def encode_with_quality(self, images, ...):
    # 第1步: 每张图 detect_and_encode
    # 第2步: 过滤质量 < min_quality 的图片
    # 第3步: 按质量排序，只取最好的前 TOP_N 张
    # 第4步: 离群值剔除（余弦相似度 < outlier_sim 的丢掉）
    # 第5步: 质量加权平均（好照片权重高）
    # 第6步: L2 归一化输出
```

对比 V2 的简单 `encode_average()`（多次采样 → 取均值），V3 的流程引入了**质量意识**——模糊的、侧脸的、光线差的照片权重低甚至被丢弃。

### CLAHE 预处理集成

在 `detect_and_encode` 和 `encode` 中各入口都检查 `FACE_PREPROCESSING_ENABLED`，如果开启则在送检测前对图像做 CLAHE 处理（在缩略图上做，CPU 友好）。

## FaceMatcher —— 三区阈值 + 批量矩阵

V3 的 FaceMatcher 从简单的欧氏距离比对升级为工业级匹配器。

### 预计算归一化矩阵

```python
def update_database(self, encodings, names, student_ids):
    # 一次性 L2 归一化 + 堆叠为矩阵
    self._known_matrix = np.array(encodings, dtype=np.float32)  # (N, 512)
    norms = np.linalg.norm(self._known_matrix, axis=1, keepdims=True)
    self._known_matrix = self._known_matrix / (norms + 1e-10)
```

### O(1) 匹配 vs V2 的 O(N) 匹配

```python
def match(self, face_encoding, ...):
    query = face_encoding / np.linalg.norm(face_encoding)
    similarities = self._known_matrix @ query   # (N,512) @ (512,) → (N,)
    best_idx = np.argmax(similarities)
    # 三区阈值分类
    is_match, confidence = self._classify_match(best_sim, margin)
```

V2 需要逐个计算欧氏距离（O(N)），V3 一次性矩阵乘法完成所有人比对（numpy 底层 BLAS 优化）。

### 三区阈值策略

```python
def _classify_match(self, best_sim, margin):
    if best_sim >= 0.55:          # 高置信区: 直接确认
        return True, best_sim
    elif best_sim >= 0.42:        # 不确定区: 需要 margin ≥ 0.08
        if margin >= 0.08:
            return True, best_sim * 0.9
        else:
            return False, best_sim  # margin不够，拒绝
    else:                          # 拒绝区
        return False, best_sim
```

**margin 的含义**：最佳匹配与次佳匹配的相似度差值。58 人的课堂上，两个人可能碰巧有相似的人脸编码。如果最佳匹配 sim=0.50 但次佳 sim=0.48（margin=0.02），说明无法区分，应拒绝。

### 批量匹配

```python
def match_multiple_batch(self, face_encodings):
    queries = np.array(face_encodings)  # (M, 512)
    sim_matrix = queries @ self._known_matrix.T  # (M, N) 一次完成M个人脸匹配
```

一帧检测到 5 个人时，一次矩阵乘法完成全部匹配。

## FaceAligner —— V3 全新模块

这是 V3 的核心新增能力，负责将 InsightFace 的 5 点关键点转化为可用的姿态和质量信息。

### 5点仿射对齐

```python
# ArcFace 标准模板 (112×112 输入坐标系)
ARCFACE_TEMPLATE = np.array([
    [38.2946, 51.6963],   # 左眼
    [73.5318, 51.5014],   # 右眼
    [56.0252, 71.7366],   # 鼻尖
    [41.5493, 92.3655],   # 左嘴角
    [70.7299, 92.2041],   # 右嘴角
])

def align_face(image, landmarks, output_size=(112,112)):
    M, _ = cv2.estimateAffinePartial2D(src_pts, ARCFACE_TEMPLATE)
    aligned = cv2.warpAffine(image, M, output_size)
```

### 姿态估计

从 5 点关键点的几何关系推算：
- **roll**：两眼连线与水平线的夹角 → 头部侧倾
- **yaw**：两眼到鼻子的水平距离比 → 头部左右偏转
- **frontal_score**：0~1 正面程度综合评分

### 质量评估（4 维评分）

```python
total_score = (
    pose['frontal_score'] * 0.4 +  # 姿态（40%）
    sharpness * 0.3 +              # 清晰度 Laplacian方差（30%）
    det_score * 0.15 +             # SCRFD检测置信度（15%）
    brightness * 0.15              # 亮度（15%）
)
```

并输出 `reject_reason`："头部偏转过大"、"图像模糊"、"光线不佳"等。

## 小结

```
core/
├── face_detector.py   → SCRFD检测, detect_with_details(), detect_fast()
├── face_encoder.py    → 统一流水线detect_and_encode(), 质量加权encode_with_quality(), CLAHE集成
├── face_matcher.py    → 预计算矩阵, 三区阈值+margin, 批量匹配, match_with_details()
└── face_aligner.py    → 5点仿射对齐, 姿态估计(roll/yaw), 质量评估(4维加权)

V2→V3 核心变化:
1. 模型引擎: dlib → InsightFace (SCRFD + ArcFace)
2. 编码维度: 128维 → 512维
3. 匹配算法: 欧氏距离 → 余弦相似度 + 预计算矩阵
4. 匹配策略: 单阈值 → 三区分类 + margin检查
5. 注册流程: 简单平均 → 质量评分 + Top-N选取 + 离群值剔除
6. 新增模块: FaceAligner (对齐/姿态/质量)
```

---

# 第四层：`services/` —— 业务中枢升级

## 架构重构：从全局单例到 AppContext

V3 最大的架构变化是引入了 `AppContext` 模式：

```python
# V2 模式: 各模块各自创建实例
db = DatabaseManager()
attendance_service = AttendanceService(db)

# V3 模式: 统一注入
class AppContext:
    def __init__(self):
        self.db = DatabaseManager()
        self.session = SessionManager()
        self.face_detector = FaceDetector(...)
        self.face_encoder = FaceEncoder()
        self.face_matcher = FaceMatcher(...)
        self.auth_service = AuthService(self.db)
        self.student_service = StudentService(self.db, self.face_detector, self.face_encoder)
        self.attendance_service = AttendanceService(self.db, self.face_detector, self.face_encoder, self.face_matcher)
        self.course_service = CourseService(self.db)

# main.py
ctx = AppContext()
window = MainWindow(ctx)  # 所有依赖通过 ctx 注入
```

**好处**：保证整个程序只有一套人脸模型实例（~300MB 只加载一次），依赖关系显式化。

## AttendanceService —— 引入跟踪器和批量匹配

### 初始化变化

```python
# V3 不再有混合策略判断——统一使用注入的 detector/encoder/matcher
class AttendanceService:
    def __init__(self, db_manager, detector, encoder, matcher):
        self.detector = detector
        self.encoder = encoder
        self.matcher = matcher
        self._tracker = SimpleTracker(max_lost=3, iou_threshold=0.3, vote_window=3)
```

### SimpleTracker —— V3 新增的时序跟踪器

```python
class SimpleTracker:
    def update(self, detections):
        # 1. 贪心IoU匹配：每个检测框与已有track配对
        # 2. 未匹配的检测 → 新建track
        # 3. 未匹配的track → lost_count++
        # 4. lost_count > max_lost → 删除track
        # 5. 投票平滑: Counter(votes).most_common(1)[0] 过半才覆盖
        # 6. 返回平滑后的确认结果
```

**作用**：消除单帧误识别闪烁。一个学生在 3 帧中 2 帧被识别为"张三"、1 帧被识别为"李四"，跟踪器投票输出"张三"。

### process_frame() 升级

```python
def process_frame(self, frame, course_id=None):
    # V3: 一次 detect_and_encode() 完成检测+编码
    detections = self.encoder.detect_and_encode(frame, max_num=10, ...)
    # V3: 一次 match_multiple_batch() 完成所有人匹配
    match_results = self.matcher.match_multiple_batch(encodings)
    # V3: 跟踪器平滑 + 投票
    tracked = self._tracker.update(raw_detections)
    # V3: 通过matcher返回的index查找student_id (修复重名bug)
```

### 新增手动补签

```python
def manual_makeup_check_in(self, student_id, course_id, status='normal', remark=None):
    # 绕过人脸识别和冷却时间，教师直接标记出勤
    # 备注自动添加"手动补签"前缀
```

### 新增未打卡学生查询

```python
def get_unchecked_students(self, course_id=None, class_name=None):
    # 遍历全班学生，找出今日未打卡的
```

## StudentService —— 注册流程质变

### 多图质量加权注册

```python
def register_student(self, student_id, name, ..., images=None):
    frames = self._collect_frames(image_path, image, images)
    # 使用 encode_with_quality(): 质量评分 → Top-N → 离群值剔除 → 质量加权平均
    avg_encoding = self.encoder.encode_with_quality(frames, ...)
    # 回退: 质量编码失败时尝试简单平均
    if avg_encoding is None:
        avg_encoding = self.encoder.encode_average(frames)
```

### 中断续传的批量导入

```python
def register_from_directory(self, dir_path, ..., cancel_check=None, error_log_path=None):
    # 支持嵌套子目录 (train/test/val)
    # 已注册学号自动跳过
    # 失败记录写入 error_log_path
    # 支持 cancel_check() 回调中途取消

def register_from_class_dir(self, class_dir, class_name, ...):
    # 处理班级目录结构 (train/test/val)
    # 自动提取班级编号前缀 (23人工智能1班 → 1-)
```

## AuthService —— 密码模块抽离

V2 中密码哈希逻辑在 `auth_service.py` 中，且 `db_manager.py` 通过延迟 import 调用它。V3 将密码逻辑抽到 `utils/security.py`：

```python
# utils/security.py
def hash_password(password): ...
def verify_password(password, hashed): ...
def is_hashed(password): ...

# db_manager.py
from utils.security import hash_password  # 不再需要延迟import
```

消除了 V2 中唯一的环形引用。

## 小结

```
services/
├── auth_service.py       → SessionManager (无变化)
├── student_service.py    → 质量加权注册, 中断续传导入, 班级批量导入
├── attendance_service.py → 统一流水线, 跟踪器+投票, 批量匹配, 手动补签, 未打卡查询
└── course_service.py     → 简单CRUD (无变化)

V2→V3 核心变化:
1. 依赖注入: 全局单例 → AppContext统一注入
2. 跟踪器: 无 → SimpleTracker (IoU匹配 + 3帧投票平滑)
3. 匹配: 逐个匹配 → 批量矩阵乘法
4. 注册: 简单平均 → 质量评分 + Top-N + 离群值剔除
5. 新增: manual_makeup_check_in, get_unchecked_students
6. 消除: 环形引用 (密码逻辑抽到utils/security.py)
```

---

# 第五层：`main.py` —— 心脏升级

V3 的 main.py 从 76 行增加到 94 行，核心变化：

## GPU 推理 DLL 路径注册

```python
# 必须在 onnxruntime 导入之前
_site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')
for _lib in ['nvidia/cudnn/bin', 'nvidia/cublas/bin']:
    _path = os.path.join(_site_packages, _lib)
    if os.path.isdir(_path):
        os.environ['PATH'] = _path + ';' + os.environ.get('PATH', '')

import onnxruntime  # 必须在 PyQt5 之前导入
```

这是 GPU 推理的关键踩坑经验——`os.add_dll_directory()` 只影响 Python ctypes，不影响原生 Windows DLL 加载。必须用 PATH 环境变量。

## AppContext 替代分散初始化

```python
# V2: 分散创建
db = DatabaseManager()
window = MainWindow()

# V3: 集中创建
ctx = AppContext()
window = MainWindow(ctx)
```

## QMessageBox 按钮样式

V3 新增了全局 QMessageBox 按钮样式，解决了 Windows 11 下按钮文字不可见的问题：

```python
app.setStyleSheet("""
    QMessageBox QPushButton {
        background-color: #E0E0E0; color: #000000;
        ...
    }
""")
```

## 小结

```
main.py = 94行 = 新增内容:
1. CUDA/cuDNN PATH注册 (GPU推理前提)
2. onnxruntime抢先导入 (避免DLL冲突)
3. AppContext 创建 (替代分散new)
4. QMessageBox按钮样式 (Windows 11兼容)
```

---

# 第六层：`gui/` —— 界面层升级

## 文件清单变化

```
gui/
├── apple_style.py          ← V2: 866行 → V3: 23860 bytes (扩展)
├── login_dialog.py         ← 适配 AppContext
├── main_window.py          ← 适配 AppContext, 新增键盘快捷键
├── attendance_panel.py     ← 核心重写 (双线程 → 跳帧+跟踪+显示缓存)
├── teacher_panel.py        ← 新增批量删除, 右键菜单, 统计优化
├── register_dialog.py      ← 适配多图注册
├── edit_student_dialog.py  ← 适配
├── edit_course_dialog.py   ← 适配
├── makeup_checkin_dialog.py ← 完全新增
└── widgets/
    ├── components.py        ← 扩展 (LoadingOverlay, EmptyState, Toast, NoFocusDelegate)
    ├── ui_components.py     ← 新增
    └── __init__.py
```

## attendance_panel.py —— 从双线程到跳帧+显示优化

V3 的考勤面板是整个系统最大变化的文件（约830行，V2约500行），核心变化：

### 跳帧策略替代密集识别

```python
# V2: 每帧都送识别线程
self.recognition_thread.add_frame(frame)

# V3: 每10帧送一次
if self._frame_counter % config.ATTENDANCE_FRAME_SKIP == 0:
    self.recognition_thread.add_frame(frame)
```

### 全链路 BGR 渲染（零色彩转换）

```python
# V2: BGR → RGB → PIL → RGB → BGR (全帧两次cvtColor)
# V3: BGR 保持 → 只在文字标签小区域做PIL RGBA → BGR通道翻转 → alpha混合
def _draw_label(self, frame, left, top, name, confidence, color):
    label_img = Image.new('RGBA', ...)  # 只有几十像素
    label_bgr = label_rgba[:, :, 2::-1] # RGBA → BGR
    roi = frame[y1:y2, x1:x2]
    blended = (label_bgr * alpha + roi * (1 - alpha))  # alpha混合
```

### 结果不变零开销

```python
# 识别结果没变 → 跳过 frame.copy() + rectangle() + _draw_label()
if self.last_results == self._last_drawn_results and self._cached_display is not None:
    self.display_image(self._cached_display)
    return
```

### QPixmap 数据指针缓存

```python
# 同一块内存数据 → 跳过 QImage构造 + scaled()
data_ptr = image.ctypes.data
if data_ptr == self._last_data_ptr and self._cached_pixmap is not None:
    self.video_label.setPixmap(self._cached_pixmap)
    return
```

### 出勤率修正

```python
# V2: 出勤率 = (正常+迟到) / 打卡记录数 (3人打100次卡 = 100%)
# V3: 出勤率 = 去重已打卡人数 / 学生总人数
total_students = len(all_students)
checked_in = len(normal_students) + len(late_students)
attendance_rate = checked_in / total_students * 100
```

### 按班级统计数据

```python
# V3 新增: 班级筛选时，统计只在选定班级范围内计算
class_name = self.combo_class.currentData()
if class_name:
    all_students = [s for s in all_students if s.get('class_name') == class_name]
    self.attendance_service.refresh_face_database(class_name=class_name)
```

## teacher_panel.py —— 多选批量操作 + 后台导入

### ImportWorker 后台线程

```python
class ImportWorker(QThread):
    progress_signal = pyqtSignal(int, int, str)
    finished_signal = pyqtSignal(int, list, str)
    def run(self):
        # 在后台线程执行批量导入，不阻塞UI
        # 支持取消 (self._cancelled = True)
        # 支持错误日志写入文件
```

### 批量操作

- 多选删除 (Ctrl/Shift)
- 右键菜单 (编辑/删除)
- 上下文菜单 (CustomContextMenu)

## makeup_checkin_dialog.py —— 完全新增

V2 没有手动补签功能。V3 新增了完整的手动补签界面：

```
┌──────────────────────────────────────────┐
│  手动补签 — 选择未打卡学生                │
│                                          │
│  班级筛选: [全部班级 ▼]  搜索: [______]  │
│  [全选]  [取消全选]                      │
│                                          │
│  ☑ 2023001  张三    [23人工智能1班]      │
│  ☐ 2023002  李四    [23人工智能1班]      │
│  ☐ 2023003  王五    [23人工智能2班]      │
│                                          │
│  补签状态: [正常 ▼]  备注: [_________]  │
│                                          │
│              [取消]  [确认补签 (3/5)]     │
└──────────────────────────────────────────┘
```

功能：
- 自动列出今日未打卡学生
- 按班级、学号、姓名筛选和搜索
- 全选/取消全选
- 选择补签状态（正常/迟到）
- 可写备注
- 批量提交

## 小结

```
gui/
├── apple_style.py            ← 设计系统 (扩展)
├── login_dialog.py           ← 适配ctx注入
├── main_window.py            ← 键盘快捷键, 自适应ctx
├── attendance_panel.py       ← 跳帧+全链路BGR+显示缓存+出勤率修正+班级筛选
├── teacher_panel.py          ← ImportWorker后台线程, 批量操作, 右键菜单
├── register_dialog.py        ← 适配多图注册
├── edit_*.py                 ← 适配
├── makeup_checkin_dialog.py  ← 完全新增: 手动补签
└── widgets/                  ← 扩展通用组件

V2→V3 显示管线对比:

V2: 摄像头BGR → cvtColor(RGB) → PIL渲染全帧 → cvtColor(BGR) → QImage(RGB) → 显示
V3: 摄像头BGR → 直接cv2画框 → PIL仅渲染标签(几十像素) → RGBA→BGR → alpha混合 → QImage(BGR888) → 显示

V2: 每帧都做 frame.copy() + rectangle() + PIL渲染
V3: 结果不变跳过渲染, 同一内存跳过QImage构造, FastTransformation替代Smooth
```

---

# 第七层：`utils/` —— 工具箱扩展

```
utils/
├── logger.py         ← 统一日志 (不变)
├── exceptions.py     ← 11个自定义异常 (不变)
├── excel_exporter.py ← Excel导出 (不变)
├── camera.py         ← CameraThread + CameraManager (不变)
├── preprocessing.py  ← 完全新增: CLAHE光照预处理
└── security.py       ← 完全新增: bcrypt密码工具
```

## preprocessing.py —— CLAHE 光照归一化

```python
def preprocess_face(image, clip_limit=2.0, tile_size=(8,8), denoise=True):
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_eq = clahe.apply(l)              # 只在L通道做均衡化
    lab_eq = cv2.merge([l_eq, a, b])
    result = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)
    if denoise:
        result = cv2.bilateralFilter(result, 5, 20, 20)
    return result
```

模块级 CLAHE 单例缓存（`_get_clahe()`），避免每帧重复创建 CLAHE 对象。

## security.py —— 密码工具

从 V2 的 `services/auth_service.py` 中抽离出来的纯函数模块：
- `hash_password()` / `verify_password()` / `is_hashed()`

消除了 V2 中唯一的环形引用依赖。

---

# 全系统互联关系图

## 一、静态依赖（import 关系）

```
config.py
  └── import os, json                  (零项目依赖)

utils/
  ├── logger.py      → import config
  ├── exceptions.py  → (零项目依赖)
  ├── camera.py      → (仅 cv2 + PyQt5)
  ├── excel_exporter.py → (仅 openpyxl)
  ├── preprocessing.py  → (仅 cv2 + numpy)
  └── security.py       → (仅 bcrypt)

database/
  ├── models.py      → (仅 SQLAlchemy)
  └── db_manager.py  → from .models import *
                     → from utils.security import hash_password (不再延迟import!)

core/
  ├── face_detector.py → import config
  ├── face_encoder.py  → import config, from .face_aligner import FaceAligner
  │                     → from utils.logger import get_logger
  │                     → from utils.preprocessing import preprocess_face
  ├── face_matcher.py  → import config
  └── face_aligner.py  → (仅 cv2 + numpy)

services/
  ├── auth_service.py     → (仅 bcrypt)
  ├── student_service.py  → from core.face_encoder import FaceEncoder
  │                       → from core.face_aligner import FaceAligner
  │                       → from database.db_manager import DatabaseManager
  │                       → import config
  ├── attendance_service.py → from core.*
  │                          → from database.db_manager import DatabaseManager
  │                          → import config, from utils.logger import get_logger
  └── course_service.py    → from database.db_manager import DatabaseManager

app_context.py
  ├── from database.db_manager import DatabaseManager
  ├── from core.* import FaceDetector, FaceEncoder, FaceMatcher
  ├── from services.auth_service import SessionManager
  ├── from services.* import StudentService, AttendanceService, CourseService, AuthService
  └── import config

gui/
  ├── apple_style.py  → (纯CSS字符串)
  ├── login_dialog.py → from app_context import AppContext
  ├── main_window.py  → import config, from app_context import AppContext
  ├── attendance_panel.py → from app_context, from utils.camera, from utils.logger
  │                       → import config, from .apple_style, from .widgets
  │                       → from .makeup_checkin_dialog import MakeupCheckInDialog
  ├── teacher_panel.py    → from app_context, from utils.excel_exporter
  │                       → from .apple_style, from .widgets, from .register_dialog, from .edit_*
  ├── register_dialog.py  → 同上模式
  ├── makeup_checkin_dialog.py → from app_context, from .apple_style
  └── widgets/            → from .apple_style

main.py
  ├── from app_context import AppContext
  ├── from gui.main_window import MainWindow
  ├── from gui.login_dialog import LoginDialog
  └── import onnxruntime (必须在PyQt5之前)
```

## 二、V2 中的环形引用已被消除

V2 中 `database/db_manager.py` 的方法内部有延迟 import：
```python
# V2 的 db_manager.py add_user() 内部:
from services.auth_service import AuthService  # 延迟import
```

V3 将此逻辑移到 `utils/security.py`（纯工具模块），`db_manager.py` 顶部直接 `from utils.security import hash_password`，不再需要延迟 import。

## 三、运行时调用链（流程对比）

### 流程：启动

```
V2:
main.py → QApplication() → DatabaseManager() → ensure_default_admin()
       → while True: LoginDialog → MainWindow → app.exec_()

V3:
main.py → CUDA PATH注册 → import onnxruntime
       → QApplication() + QMessageBox样式
       → AppContext() → 注入所有共享实例 + 加载InsightFace模型
       → ensure_default_admin(ctx)
       → while True: LoginDialog(ctx) → MainWindow(ctx) → app.exec_()
```

### 流程：考勤识别

```
V2 双线程:
CameraThread(30fps) → frame_ready → UI显示
                    → FaceRecognitionThread → 每帧detect+encode+match → 逐个欧氏距离比对 → 打卡

V3 跳帧+跟踪+批量:
CameraThread(30fps) → 每帧送UI显示
                    → 每10帧送 FaceRecognitionThread
                    → detect_and_encode() 一次完成检测+编码
                    → match_multiple_batch() 一次矩阵乘法完成全库匹配
                    → SimpleTracker 投票平滑
                    → 打卡 + 统计刷新
```

### 流程：学生注册

```
V2:
用户拍照 → CNN detect → jitters=5 encode → encoding_to_blob() → 写入DB

V3:
多张照片 → 每张 detect_and_encode() 获取编码+姿态+质量
       → 过滤质量<0.30的图片
       → 按质量排序取Top-N
       → 离群值剔除
       → 质量加权平均编码
       → encoding_to_blob() (2048 bytes) → 写入DB
```

## 四、AppContext 的全局共享关系

```
AppContext (集中容器)
  ├── db: DatabaseManager               ← 唯一数据库实例
  ├── session: SessionManager            ← 替代 V2 的全局 session_manager
  ├── face_detector: FaceDetector        ← 唯一检测器实例
  ├── face_encoder: FaceEncoder          ← 共享 InsightFace 模型单例
  ├── face_matcher: FaceMatcher          ← 唯一匹配器 (含预计算矩阵)
  ├── auth_service: AuthService          ← 服务层
  ├── student_service: StudentService    ← 服务层
  ├── attendance_service: AttendanceService ← 服务层
  ├── course_service: CourseService      ← 服务层
  ├── camera_index/width/height          ← 摄像头默认配置
```

所有 GUI 组件通过 `self.ctx.xxx` 访问，不再自行创建实例。

## 五、config.py 的参数被谁消费（变化对比）

```
V2: config.FACE_USE_HYBRID_MODE → StudentService/AttendanceService 决定 CNN/HOG
V3: 无此参数 — 统一使用 InsightFace SCRFD + ArcFace

V2: config.FACE_RECOGNITION_TOLERANCE(0.5, 欧氏距离) → FaceMatcher
V3: config.FACE_RECOGNITION_CONFIDENT(0.55, 余弦相似度) → FaceMatcher

V2: config.FACE_REGISTRATION_MODEL/JITTERS → StudentService
V3: config.FACE_REGISTRATION_SHOTS/TOP_N/MIN_QUALITY/OUTLIER_SIM → FaceEncoder + StudentService

V2: config.FACE_ATTENDANCE_MODEL/JITTERS → AttendanceService
V3: 无 — 统一模型，通过 FRAME_SKIP 补偿性能

V2: config.CAMERA_WIDTH/HEIGHT = 640/480
V3: config.CAMERA_WIDTH/HEIGHT = 1280/720

V3 新增:
  config.FACE_MODEL_NAME → FaceEncoder._get_face_model()
  config.FACE_DET_SIZE → FaceEncoder._get_face_model()
  config.ATTENDANCE_FRAME_SKIP → AttendancePanel.on_frame_ready()
  config.FACE_PREPROCESSING_ENABLED → FaceEncoder各编码入口
```

## 六、依赖层级自底向上

```
第0层（零项目依赖）:
  config.py
  database/models.py
  utils/exceptions.py
  utils/security.py
  utils/preprocessing.py
  gui/apple_style.py

第1层（只依赖第0层 + 三方库）:
  utils/logger.py         → config
  utils/camera.py         → (cv2 + PyQt5)
  utils/excel_exporter.py → (openpyxl)
  core/face_aligner.py    → (cv2 + numpy)
  core/face_detector.py   → config + .face_encoder (模型单例)
  core/face_encoder.py    → config + logger + preprocessing + .face_aligner
  core/face_matcher.py    → config

第2层:
  database/db_manager.py  → models + utils.security (不再延迟import)
  services/auth_service.py → (bcrypt)

第3层:
  services/student_service.py    → core + database + config
  services/attendance_service.py → core + database + config + logger
  services/course_service.py     → database

第4层:
  app_context.py → 组装所有第0-3层实例

第5层（顶层入口）:
  gui/* (所有GUI组件) → app_context + 具体服务
  main.py → gui + app_context
```

## 七层全景回顾

```
                         ┌──────────────┐
                         │   main.py    │  ← 心脏：CUDA注册 + AppContext + 登录循环
                         │   (94行)     │
                         └──────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    │   app_context.py      │  ← 中枢：所有共享实例的唯一来源
                    │   (63行)             │
                    └───────────┬───────────┘
                                │ 注入
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌──────────────┐ ┌───────────┐ ┌──────────────┐
        │  services/   │ │   gui/    │ │   utils/     │
        │  业务编排     │ │  用户界面  │ │   工具箱      │
        │──────────────│ │───────────│ │──────────────│
        │ AuthService  │ │ LoginDlg  │ │ logger       │
        │ StudentSvc   │ │ MainWin   │ │ camera       │
        │ AttendanceSvc│ │ AttendPnl │ │ excel_export │
        │ CourseSvc    │ │ TeacherPnl│ │ exceptions   │
        │ SimpleTracker│ │ MakeupDlg │ │ preprocessing│
        └──┬───────┬───┘ │ apple_style│ │ security     │
           │       │     └───────────┘ └──────────────┘
           ▼       ▼
    ┌──────────┐ ┌──────────────┐
    │  core/   │ │  database/   │
    │  算法层   │ │   数据层      │
    │──────────│ │──────────────│
    │Detector  │ │ models+4索引 │
    │Encoder   │ │ db_manager   │
    │Matcher   │ │              │
    │Aligner   │ │              │
    └──────────┘ └──────────────┘
           ▲               ▲
           └───────┬───────┘
                   │ 都依赖
           ┌───────┴───────┐
           │   config.py   │  ← 大脑：79行 + settings.json覆盖
           │   (79行)      │
           └───────────────┘
```

**数据流向一句话**：

> `config` 定规则 → `core` (SCRFD+ArcFace+Aligner) 做算法 → `database` (4表+4索引) 存数据 → `services` (跟踪器+批量匹配) 串联业务 → `gui` (跳帧+全链路BGR+缓存) 展示交互 → `main` 注册CUDA+创建AppContext循环驱动 → `utils` (CLAHE+安全) 辅助支撑

---

# 总结：V2 → V3 十项核心对比

| # | 维度 | V2 | V3 | 影响 |
|---|------|-----|-----|------|
| 1 | **识别引擎** | dlib (HOG/CNN + ResNet 128d) | InsightFace (SCRFD + ArcFace 512d) | 识别准确率显著提升 |
| 2 | **推理加速** | CPU only | GPU (onnxruntime-gpu + CUDA) | 高精度模型下保持实时 |
| 3 | **匹配策略** | 单阈值(0.5欧氏距离) | 三区分类+margin (余弦相似度) | 降低误识率 |
| 4 | **注册质量** | jitters多次采样取平均 | 5点关键点质量评分+Top-N+离群值剔除 | 注册模板更稳定 |
| 5 | **人脸跟踪** | 无 | SimpleTracker (IoU+投票) | 消除单帧闪烁 |
| 6 | **光照适应** | 无 | CLAHE预处理 (可选) | 教室光线适应 |
| 7 | **架构模式** | 全局单例 + 各自new | AppContext 集中注入 | 依赖清晰, 模型只加载一次 |
| 8 | **性能优化** | 每帧识别 | 跳帧+预计算矩阵+批量匹配+显示缓存 | GPU+CPU协同, 30fps显示+3fps识别 |
| 9 | **手动补签** | 无 | 完整补签界面 | 教师可控出勤记录 |
| 10 | **环形依赖** | db_manager 延迟import auth_service | security.py 抽离 | 代码结构更清晰 |

## V2 中保留到 V3 的设计

- **BASE_DIR 路径基准**：所有路径基于 config.py 所在目录计算
- **上下文管理器 get_session()**：永不泄漏连接 + 自动回滚
- **main.py 的 while True 心脏循环**：登录 → 主界面 → 退出登录 → 循环
- **登录退出 vs 直接关闭的区分**：`_is_logging_out` 标志位
- **apple_style.py 设计宪法**：所有视觉定义唯一来源
- **侧边栏 + QStackedWidget 布局**：5个按钮切换2个面板
- **10秒冷却 + 15分钟迟到**：业务规则不变
- **11个自定义异常类**：继承层次保留
- **双线程架构思路**：CameraThread + FaceRecognitionThread (实现方式升级)

## V2 中被移除的设计

- **混合策略 (CNN注册 + HOG考勤)**：V3 统一使用 InsightFace，通过跳帧+缩放补偿性能
- **face_recognition 库**：完全替换为 insightface
- **V2 的 FaceDetector 的 model 参数**：不再需要 hog/cnn 选择
- **V2 的 FaceEncoder 的 num_jitters**：不再使用 dlib 的 jitter 机制
- **延迟 import 绕环形引用**：通过 utils/security.py 消除
- **全局 session_manager 单例**：整合到 AppContext 中
