"""
自定义异常类
提供更具体的异常类型
"""


class AttendanceSystemError(Exception):
    """考勤系统基础异常"""
    pass


class DatabaseError(AttendanceSystemError):
    """数据库操作异常"""
    pass


class StudentNotFoundError(AttendanceSystemError):
    """学生不存在异常"""
    def __init__(self, student_id: str):
        self.student_id = student_id
        super().__init__(f"学生不存在: {student_id}")


class CourseNotFoundError(AttendanceSystemError):
    """课程不存在异常"""
    def __init__(self, course_id: int):
        self.course_id = course_id
        super().__init__(f"课程不存在: {course_id}")


class FaceDetectionError(AttendanceSystemError):
    """人脸检测异常"""
    pass


class FaceEncodingError(AttendanceSystemError):
    """人脸特征提取异常"""
    pass


class FaceMatchingError(AttendanceSystemError):
    """人脸匹配异常"""
    pass


class CameraError(AttendanceSystemError):
    """摄像头异常"""
    pass


class AuthenticationError(AttendanceSystemError):
    """认证异常"""
    pass


class DuplicateRecordError(AttendanceSystemError):
    """重复记录异常"""
    pass


class CooldownError(AttendanceSystemError):
    """冷却时间异常"""
    def __init__(self, remaining_seconds: int):
        self.remaining_seconds = remaining_seconds
        super().__init__(f"请等待 {remaining_seconds} 秒后再打卡")