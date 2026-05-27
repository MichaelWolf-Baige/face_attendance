"""
应用上下文容器
集中管理所有共享实例，通过构造函数注入到各模块

替代原来的:
  - 各模块自行创建 DatabaseManager()  (多实例问题)
  - 全局 session_manager 单例
  - 各模块直接读取 config 模块全局变量
"""
from database.db_manager import DatabaseManager
from core.face_detector import FaceDetector
from core.face_encoder import FaceEncoder
from core.face_matcher import FaceMatcher
from services.auth_service import SessionManager
import config


class AppContext:
    """应用上下文 — 所有共享实例的唯一来源"""

    def __init__(self, db_path: str = None):
        # 数据库 (唯一实例)
        self.db = DatabaseManager(db_path)

        # 会话管理 (替代全局 session_manager)
        self.session = SessionManager()

        # 配置 InsightFace 模型 (在首次加载前注入)
        from core.face_encoder import set_model_config
        set_model_config(
            model_name=getattr(config, 'FACE_MODEL_NAME', 'buffalo_sc'),
            det_size=getattr(config, 'FACE_DET_SIZE', (320, 320))
        )

        # 人脸识别核心 (唯一实例，由 services 共享)
        self.face_detector = FaceDetector(
            resize_scale=config.FACE_ATTENDANCE_RESIZE_SCALE
        )
        self.face_encoder = FaceEncoder()
        self.face_matcher = FaceMatcher(
            tolerance=config.FACE_RECOGNITION_TOLERANCE
        )

        # 服务层 (延迟导入避免循环依赖)
        from services.student_service import StudentService
        from services.attendance_service import AttendanceService
        from services.course_service import CourseService
        from services.auth_service import AuthService

        self.auth_service = AuthService(self.db)
        self.student_service = StudentService(
            self.db, self.face_detector, self.face_encoder
        )
        self.attendance_service = AttendanceService(
            self.db, self.face_detector, self.face_encoder, self.face_matcher
        )
        self.course_service = CourseService(self.db)

        # 摄像头默认配置
        self.camera_index = config.CAMERA_INDEX
        self.camera_width = config.CAMERA_WIDTH
        self.camera_height = config.CAMERA_HEIGHT
