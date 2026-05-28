"""
主窗口
人脸识别考勤系统主界面
Apple 风格设计
"""
import sys
import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QMessageBox, QApplication, QGraphicsDropShadowEffect, QShortcut
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon, QColor, QKeySequence

import config

from .attendance_panel import AttendancePanel
from .teacher_panel import TeacherPanel
from .apple_style import (
    COLORS, RADIUS, NAVIGATION_STYLE, get_button_style,
    LOGOUT_BUTTON_STYLE, REQUIRED_ASTERISK_STYLE, get_app_style, SHADOWS, ICONS
)


class MainWindow(QMainWindow):
    """主窗口类"""

    # 自定义信号，用于退出登录后返回登录界面
    logout_signal = None

    def __init__(self, ctx):
        super().__init__()

        self.ctx = ctx

        # 标志位：是否为退出登录（区别于直接关闭窗口）
        self._is_logging_out = False

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化用户界面 - Apple风格"""
        # 窗口设置
        self.setWindowTitle("人脸识别考勤系统")
        self.setGeometry(100, 100, config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setMinimumSize(1200, 800)

        # 应用全局样式
        self.setStyleSheet(get_app_style())

        # 主部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航栏
        nav_frame = self.create_navigation()
        main_layout.addWidget(nav_frame)

        # 右侧内容区
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet(f"""
            QStackedWidget {{
                background-color: {COLORS['background']};
                border: none;
            }}
        """)

        # 考勤面板（共享 attendance_service）
        self.attendance_panel = AttendancePanel(self.ctx)
        self.content_stack.addWidget(self.attendance_panel)

        # 教师管理面板（共享 attendance_service）
        self.teacher_panel = TeacherPanel(self.ctx)
        self.content_stack.addWidget(self.teacher_panel)

        main_layout.addWidget(self.content_stack, 1)

        # 设置导航按钮点击事件
        self.setup_navigation()

        # 键盘快捷键
        self.setup_shortcuts()

        # 默认显示考勤面板
        self.content_stack.setCurrentIndex(0)

    def create_navigation(self) -> QFrame:
        """创建导航栏 - Apple风格"""
        nav_frame = QFrame()
        nav_frame.setObjectName("navFrame")
        nav_frame.setFixedWidth(220)
        nav_frame.setStyleSheet(f"""
            QFrame#navFrame {{
                background-color: {COLORS['sidebar']};
                border: none;
                border-top-right-radius: 0px;
            }}
        """)

        layout = QVBoxLayout(nav_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题区域
        title_frame = QFrame()
        title_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                padding: 20px 16px;
            }}
        """)
        title_layout = QVBoxLayout(title_frame)
        title_layout.setSpacing(4)

        title_label = QLabel("考勤系统")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_light']};
                font-size: 20px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
        """)
        title_layout.addWidget(title_label)

        subtitle_label = QLabel("Face Attendance")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['sidebar_text_secondary']};
                font-size: 11px;
                letter-spacing: 0.5px;
            }}
        """)
        title_layout.addWidget(subtitle_label)

        layout.addWidget(title_frame)

        # 分隔线
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['sidebar_divider']};
                margin: 0px 16px;
            }}
        """)
        layout.addWidget(separator)

        # 导航按钮区域
        nav_container = QWidget()
        nav_container.setStyleSheet("padding: 8px 0px;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(12, 8, 12, 8)
        nav_layout.setSpacing(2)

        self.btn_attendance = QPushButton(f"{ICONS['attendance']}  考勤打卡")
        self.btn_attendance.setObjectName("navButton")
        self.btn_attendance.setCheckable(True)
        self.btn_attendance.setChecked(True)
        self.btn_attendance.setMinimumHeight(48)
        self.btn_attendance.setStyleSheet(self._get_nav_button_style(True))
        nav_layout.addWidget(self.btn_attendance)

        self.btn_students = QPushButton(f"{ICONS['students']}  学生管理")
        self.btn_students.setObjectName("navButton")
        self.btn_students.setCheckable(True)
        self.btn_students.setMinimumHeight(48)
        self.btn_students.setStyleSheet(self._get_nav_button_style(False))
        nav_layout.addWidget(self.btn_students)

        self.btn_courses = QPushButton(f"{ICONS['courses']}  课程管理")
        self.btn_courses.setObjectName("navButton")
        self.btn_courses.setCheckable(True)
        self.btn_courses.setMinimumHeight(48)
        self.btn_courses.setStyleSheet(self._get_nav_button_style(False))
        nav_layout.addWidget(self.btn_courses)

        self.btn_records = QPushButton(f"{ICONS['records']}  考勤记录")
        self.btn_records.setObjectName("navButton")
        self.btn_records.setCheckable(True)
        self.btn_records.setMinimumHeight(48)
        self.btn_records.setStyleSheet(self._get_nav_button_style(False))
        nav_layout.addWidget(self.btn_records)

        self.btn_export = QPushButton(f"{ICONS['export']}  数据导出")
        self.btn_export.setObjectName("navButton")
        self.btn_export.setCheckable(True)
        self.btn_export.setMinimumHeight(48)
        self.btn_export.setStyleSheet(self._get_nav_button_style(False))
        nav_layout.addWidget(self.btn_export)

        layout.addWidget(nav_container)

        # 弹性空间
        layout.addStretch()

        # 用户信息区域
        user_frame = QFrame()
        user_frame.setObjectName("userFrame")
        user_frame.setStyleSheet(f"""
            QFrame#userFrame {{
                background-color: {COLORS['sidebar_user_bg']};
                border-radius: {RADIUS['medium']};
                margin: 12px;
                padding: 16px;
            }}
        """)
        user_layout = QVBoxLayout(user_frame)
        user_layout.setSpacing(8)

        # 用户头像占位
        avatar_label = QLabel("")
        avatar_label.setFixedSize(40, 40)
        avatar_label.setAlignment(Qt.AlignCenter)
        avatar_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['primary']};
                border-radius: 20px;
                color: white;
                font-size: 16px;
                font-weight: 600;
            }}
        """)
        avatar_text = self.ctx.session.get_user_display_name()
        if avatar_text:
            avatar_label.setText(avatar_text[0] if len(avatar_text) > 0 else "U")

        user_header = QHBoxLayout()
        user_header.addWidget(avatar_label)

        user_info = QVBoxLayout()
        user_info.setSpacing(2)

        self.user_label = QLabel(f"{self.ctx.session.get_user_display_name()}")
        self.user_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_light']};
                font-size: 14px;
                font-weight: 500;
            }}
        """)
        user_info.addWidget(self.user_label)

        role_label = QLabel("管理员" if self.ctx.session.current_user and self.ctx.session.current_user.get('role') == 'admin' else "教师")
        role_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['sidebar_text_secondary']};
                font-size: 12px;
            }}
        """)
        user_info.addWidget(role_label)
        user_header.addLayout(user_info)
        user_header.addStretch()

        user_layout.addLayout(user_header)

        # 注销按钮
        self.btn_logout = QPushButton("退出登录")
        self.btn_logout.setStyleSheet(LOGOUT_BUTTON_STYLE)
        self.btn_logout.clicked.connect(self.logout)
        user_layout.addWidget(self.btn_logout)

        layout.addWidget(user_frame)

        # 版本信息
        version_label = QLabel("v1.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['sidebar_text_secondary']};
                padding: 12px;
                font-size: 11px;
            }}
        """)
        layout.addWidget(version_label)

        self.nav_buttons = [
            self.btn_attendance,
            self.btn_students,
            self.btn_courses,
            self.btn_records,
            self.btn_export
        ]

        return nav_frame

    def _get_nav_button_style(self, checked: bool) -> str:
        """获取导航按钮样式"""
        if checked:
            return f"""
                QPushButton {{
                    background-color: {COLORS['primary']};
                    color: {COLORS['text_light']};
                    border: none;
                    padding: 12px 16px;
                    text-align: left;
                    font-size: 14px;
                    font-weight: 500;
                    border-radius: {RADIUS['medium']};
                }}
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: rgba(255, 255, 255, 0.8);
                border: none;
                padding: 12px 16px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                border-radius: {RADIUS['medium']};
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """

    def setup_navigation(self):
        """设置导航逻辑"""
        self.btn_attendance.clicked.connect(lambda checked, i=0: self.switch_page(i))
        self.btn_students.clicked.connect(lambda checked, i=1: self.switch_page(i))
        self.btn_courses.clicked.connect(lambda checked, i=2: self.switch_page(i))
        self.btn_records.clicked.connect(lambda checked, i=3: self.switch_page(i))
        self.btn_export.clicked.connect(lambda checked, i=4: self.switch_page(i))

    def setup_shortcuts(self):
        """设置键盘快捷键"""
        shortcuts = [
            ("Ctrl+1", 0),  # 考勤打卡
            ("Ctrl+2", 1),  # 学生管理
            ("Ctrl+3", 2),  # 课程管理
            ("Ctrl+4", 3),  # 考勤记录
            ("Ctrl+5", 4),  # 数据导出
        ]
        for key_seq, index in shortcuts:
            shortcut = QShortcut(QKeySequence(key_seq), self)
            shortcut.activated.connect(lambda i=index: self.switch_page(i))

    def switch_page(self, index: int):
        """切换页面"""
        # 更新按钮状态
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
            btn.setStyleSheet(self._get_nav_button_style(i == index))

        # 切换内容
        if index == 0:
            self.content_stack.setCurrentWidget(self.attendance_panel)
        else:
            # 其他页面使用教师面板的不同标签页
            self.content_stack.setCurrentWidget(self.teacher_panel)
            self.teacher_panel.switch_tab(index - 1)

    def logout(self):
        """退出登录"""
        reply = QMessageBox.question(
            self, '退出登录',
            '确定要退出登录吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 设置标志位，避免 closeEvent 再次弹出确认框
            self._is_logging_out = True

            # 停止摄像头
            if hasattr(self.attendance_panel, 'camera_thread'):
                self.attendance_panel.stop_camera()

            # 清除会话
            self.ctx.session.logout()

            # 关闭当前窗口（会触发 closeEvent，但由于标志位不会弹框）
            self.close()

    def closeEvent(self, event):
        """关闭窗口事件"""
        # 如果是退出登录，直接接受关闭事件
        if self._is_logging_out:
            event.accept()
            return

        reply = QMessageBox.question(
            self, '退出确认',
            '确定要退出系统吗？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 停止摄像头
            if hasattr(self.attendance_panel, 'camera_thread'):
                self.attendance_panel.stop_camera()
            # 不清除会话，让 main 循环检测到 session 存在，直接退出程序
            event.accept()
        else:
            event.ignore()