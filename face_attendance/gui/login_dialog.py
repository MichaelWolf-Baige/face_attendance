"""
登录对话框
用户登录界面
Apple 风格设计 - 优化版
"""
import sys
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame,
    QGraphicsDropShadowEffect, QWidget, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QColor

from .apple_style import (
    COLORS, RADIUS, INPUT_STYLE, get_button_style,
    LOGIN_DIALOG_STYLE, ICONS
)


class LoginDialog(QDialog):
    """登录对话框 - Apple风格优化版"""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.init_ui()

    def init_ui(self):
        """初始化UI - Apple风格优化版（宽松布局）"""
        self.setWindowTitle("登录")
        self.setFixedSize(480, 680)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 主容器（用于阴影效果）
        container = QWidget(self)
        container.setObjectName("loginContainer")
        container.setGeometry(24, 24, 432, 632)
        container.setStyleSheet(f"""
            QWidget#loginContainer {{
                background-color: {COLORS['surface']};
                border-radius: {RADIUS['xl']};
            }}
        """)

        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(60)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 16)
        container.setGraphicsEffect(shadow)

        # 主布局 - 增加边距和间距
        layout = QVBoxLayout(container)
        layout.setSpacing(0)
        layout.setContentsMargins(56, 56, 56, 48)

        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setParent(container)
        close_btn.setGeometry(388, 18, 36, 36)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                border: none;
                font-size: 28px;
                font-weight: 300;
            }}
            QPushButton:hover {{
                color: {COLORS['text_primary']};
                background-color: {COLORS['table_header']};
                border-radius: 18px;
            }}
        """)
        close_btn.clicked.connect(self._on_close)

        # ========== Logo 区域 ==========
        icon_container = QHBoxLayout()
        icon_container.setContentsMargins(0, 0, 0, 0)

        icon_frame = QFrame()
        icon_frame.setFixedSize(80, 80)
        icon_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {COLORS['primary']}, stop:1 #0055CC);
                border-radius: 20px;
            }}
        """)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setSpacing(0)

        icon_label = QLabel(ICONS['camera'])
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                background: transparent;
            }
        """)
        icon_layout.addWidget(icon_label)

        icon_container.addStretch()
        icon_container.addWidget(icon_frame)
        icon_container.addStretch()
        layout.addLayout(icon_container)

        # ========== 标题区域 ==========
        layout.addSpacing(40)

        # 主标题
        title_label = QLabel("人脸识别考勤系统")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 24px;
                font-weight: 600;
                letter-spacing: 3px;
            }}
        """)
        layout.addWidget(title_label)

        # 副标题
        subtitle_label = QLabel("Face Attendance System")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 14px;
                letter-spacing: 1px;
                margin-top: 8px;
            }}
        """)
        layout.addWidget(subtitle_label)

        # ========== 表单区域 ==========
        layout.addSpacing(48)

        # 用户名输入
        username_label = QLabel("用户名")
        username_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 13px;
                margin-bottom: 8px;
            }}
        """)
        layout.addWidget(username_label)

        layout.addSpacing(8)

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("请输入用户名")
        self.username_edit.setMinimumHeight(52)
        self.username_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['table_header']};
                color: {COLORS['text_primary']};
                border: 2px solid transparent;
                border-radius: {RADIUS['medium']};
                padding: 0 20px;
                font-size: 15px;
            }}
            QLineEdit:hover {{
                background-color: {COLORS['divider']};
            }}
            QLineEdit:focus {{
                background-color: {COLORS['surface']};
                border-color: {COLORS['primary']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_placeholder']};
            }}
        """)
        layout.addWidget(self.username_edit)

        # 密码输入
        layout.addSpacing(24)
        password_label = QLabel("密码")
        password_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 13px;
                margin-bottom: 8px;
            }}
        """)
        layout.addWidget(password_label)

        layout.addSpacing(8)

        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("请输入密码")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setMinimumHeight(52)
        self.password_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['table_header']};
                color: {COLORS['text_primary']};
                border: 2px solid transparent;
                border-radius: {RADIUS['medium']};
                padding: 0 20px;
                font-size: 15px;
            }}
            QLineEdit:hover {{
                background-color: {COLORS['divider']};
            }}
            QLineEdit:focus {{
                background-color: {COLORS['surface']};
                border-color: {COLORS['primary']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_placeholder']};
            }}
        """)
        self.password_edit.returnPressed.connect(self.login)
        layout.addWidget(self.password_edit)

        # ========== 登录按钮 ==========
        layout.addSpacing(36)

        self.login_btn = QPushButton("登 录")
        self.login_btn.setMinimumHeight(56)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: {COLORS['text_light']};
                border: none;
                border-radius: {RADIUS['medium']};
                font-size: 17px;
                font-weight: 600;
                letter-spacing: 6px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: #004499;
            }}
        """)
        self.login_btn.clicked.connect(self.login)
        layout.addWidget(self.login_btn)

        # ========== 底部提示 ==========
        layout.addSpacing(24)

        hint_label = QLabel("默认账号: admin / admin123")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 13px;
            }}
        """)
        layout.addWidget(hint_label)

        # 允许拖动窗口
        self._drag_pos = None

    def _on_close(self):
        """关闭窗口"""
        if not self.ctx.session.is_logged_in:
            sys.exit(0)
        self.reject()

    def mousePressEvent(self, event):
        """鼠标按下事件 - 用于拖动窗口"""
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 用于拖动窗口"""
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def login(self):
        """登录"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not username or not password:
            self._show_error("请输入用户名和密码")
            return

        # 验证用户
        user = self.ctx.auth_service.login(username, password)
        if user:
            # 记录会话
            self.ctx.session.login(user)
            self.accept()
        else:
            self._show_error("用户名或密码错误")
            self.password_edit.clear()
            self.password_edit.setFocus()

    def _show_error(self, message: str):
        """显示错误提示"""
        msg = QMessageBox(self)
        msg.setWindowTitle("提示")
        msg.setText(message)
        msg.setIcon(QMessageBox.Warning)
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {COLORS['surface']};
            }}
            QMessageBox QLabel {{
                color: {COLORS['text_primary']};
                font-size: 14px;
                min-width: 200px;
            }}
            QMessageBox QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-size: 14px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}
        """)
        msg.exec_()

    def closeEvent(self, event):
        """关闭事件"""
        # 如果没有登录，直接退出程序
        if not self.ctx.session.is_logged_in:
            sys.exit(0)
        event.accept()