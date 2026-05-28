"""
人脸识别考勤系统 - 全局配置
"""
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据库配置
DATABASE_PATH = os.path.join(BASE_DIR, 'face_attendance.db')

# 人脸识别配置 (InsightFace ArcFace + SCRFD)
# 阈值策略:
#   sim >= 0.55 → 确认匹配
#   sim < 0.55  → 拒绝，不记录考勤
FACE_RECOGNITION_CONFIDENT = 0.55   # 高置信阈值
FACE_RECOGNITION_UNCERTAIN = 0.55   # 不再有不确定区
FACE_RECOGNITION_TOLERANCE = 0.55   # 统一阈值
FACE_ATTENDANCE_RESIZE_SCALE = 1   # 考勤缩放 (1280→640, 减少CPU resize负担)

# 多图注册配置
FACE_REGISTRATION_SHOTS = 3  # 注册时拍摄张数 (取平均encoding)
FACE_REGISTRATION_MIN_QUALITY = 0.30     # 注册最低质量分 (提高门槛)
FACE_REGISTRATION_OUTLIER_SIM = 0.30     # 离群值剔除余弦相似度阈值
FACE_REGISTRATION_RESIZE_SCALE = 1.0  # 注册时不缩放，全分辨率提取编码
FACE_REGISTRATION_FALLBACK = True        # 质量编码失败时回退到简单平均编码
FACE_REGISTRATION_TOP_N = 5              # 只取质量最高的前N张照片注册 (0=使用全部)

# InsightFace 模型配置
FACE_MODEL_NAME = 'buffalo_l'      # buffalo_l (ResNet50,高精度) / buffalo_sc (MobileFaceNet,快速)
FACE_DET_SIZE = (640, 640)         # 检测输入尺寸 (640→人脸框更准→ArcFace编码更准)

# 考勤帧处理配置
ATTENDANCE_FRAME_SKIP = 1   # 每N帧处理一次 (1=不跳帧，充分利用GPU)
FACE_MIN_FACE_SIZE = 80     # 最小人脸像素尺寸 (用于质量过滤)

# 摄像头配置
CAMERA_INDEX = 0  # 默认摄像头索引
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30

# 考勤配置
ATTENDANCE_COOLDOWN = 10  # 同一学生两次打卡间隔(秒)
LATE_THRESHOLD_MINUTES = 15  # 迟到阈值(分钟)

# GUI配置
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
THEME_COLOR = '#2196F3'  # 主色调
REFRESH_INTERVAL_MS = 5000  # 考勤记录刷新间隔(毫秒)

# 日志配置
LOG_LEVEL = 'INFO'  # 日志级别: DEBUG, INFO, WARNING, ERROR

# 数据配置
DATA_DIR = os.path.dirname(BASE_DIR)  # 数据目录(学生照片)

# 性能配置 ('auto' | 'gpu' | 'cpu')
PERFORMANCE_PROFILE = 'auto'


def auto_detect_profile(profile: str = None):
    """根据性能配置选择人脸识别模型和参数"""
    if profile is None:
        profile = PERFORMANCE_PROFILE

    if profile == 'cpu':
        _apply_cpu_profile()
        return
    if profile == 'gpu':
        print("[性能] 强制 GPU 模式 (buffalo_l + 640)")
        return

    # 'auto': 自动检测 GPU
    try:
        import onnxruntime as ort
        if 'CUDAExecutionProvider' in ort.get_available_providers():
            print("[性能] 检测到 GPU，使用高性能模式 (buffalo_l + 640)")
            return
    except Exception:
        pass
    _apply_cpu_profile()


def _apply_cpu_profile():
    global FACE_MODEL_NAME, FACE_DET_SIZE
    global FACE_ATTENDANCE_RESIZE_SCALE, ATTENDANCE_FRAME_SKIP
    FACE_MODEL_NAME = 'buffalo_sc'
    FACE_DET_SIZE = (320, 320)
    FACE_ATTENDANCE_RESIZE_SCALE = 0.5
    ATTENDANCE_FRAME_SKIP = 1
    print("[性能] 未检测到 GPU，已切换轻量配置 (buffalo_sc + 320 + 0.5缩放)")


# 从外部配置文件加载覆盖值 (可选)
import json
_CONFIG_FILE = os.path.join(BASE_DIR, 'settings.json')
if os.path.exists(_CONFIG_FILE):
    try:
        with open(_CONFIG_FILE, 'r', encoding='utf-8') as f:
            overrides = json.load(f)
        for key, value in overrides.items():
            if key.isupper() and key in globals():
                globals()[key] = value
    except Exception as e:
        print(f"Warning: Failed to load settings.json: {e}")
