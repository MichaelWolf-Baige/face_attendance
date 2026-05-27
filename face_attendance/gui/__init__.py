"""
GUI界面模块
Apple 风格设计
"""
from .main_window import MainWindow
from .attendance_panel import AttendancePanel
from .register_dialog import RegisterDialog
from .teacher_panel import TeacherPanel
from .login_dialog import LoginDialog
from .edit_student_dialog import EditStudentDialog
from .edit_course_dialog import EditCourseDialog
from . import apple_style
from . import widgets

__all__ = [
    'MainWindow',
    'AttendancePanel',
    'RegisterDialog',
    'TeacherPanel',
    'LoginDialog',
    'EditStudentDialog',
    'EditCourseDialog',
    'apple_style',
    'widgets'
]