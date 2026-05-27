"""
自定义UI组件实现
包含：LoadingOverlay, EmptyStateWidget, CustomMessageBox, ToastNotification
Apple 风格设计 - 增强版
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QDialogButtonBox, QFrame, QGraphicsDropShadowEffect,
    QApplication, QSpacerItem, QSizePolicy, QStyledItemDelegate, QStyle
)
from PyQt5.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QSize, pyqtSignal, QParallelAnimationGroup,
    QSequentialAnimationGroup, QRect
)
from PyQt5.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPainterPath,
    QLinearGradient, QRadialGradient, QConicalGradient
)
import math

from ..apple_style import COLORS, RADIUS, get_button_style


# ==================== 无焦点框 Delegate ====================

class NoFocusDelegate(QStyledItemDelegate):
    """表格单元格代理 — 禁止绘制焦点虚线/实线框"""
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.state &= ~QStyle.State_HasFocus


# ==================== Loading Overlay ====================

class LoadingSpinner(QWidget):
    """加载旋转动画组件"""

    def __init__(self, size=48, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._color = QColor(COLORS['primary'])

        # 动画定时器
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)

    def start(self):
        """开始动画"""
        self._timer.start(30)
        self.show()

    def stop(self):
        """停止动画"""
        self._timer.stop()
        self.hide()

    def _rotate(self):
        """旋转"""
        self._angle = (self._angle + 8) % 360
        self.update()

    def paintEvent(self, event):
        """绘制旋转圆环"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制背景圆
        center = self.width() // 2
        radius = center - 4

        # 绘制淡色底圈
        pen = QPen(QColor(COLORS['divider']))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.drawEllipse(center - radius, center - radius, radius * 2, radius * 2)

        # 绘制渐变弧线
        gradient = QConicalGradient(center, center, self._angle)
        gradient.setColorAt(0, self._color)
        gradient.setColorAt(0.3, self._color)
        gradient.setColorAt(0.5, QColor(self._color.red(), self._color.green(), self._color.blue(), 100))
        gradient.setColorAt(1, QColor(self._color.red(), self._color.green(), self._color.blue(), 0))

        pen = QPen(QBrush(gradient), 3)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(center - radius, center - radius, radius * 2, radius * 2, 0, 270 * 16)


class LoadingOverlay(QWidget):
    """加载遮罩层"""

    def __init__(self, parent=None, text="加载中..."):
        super().__init__(parent)

        self._text = text
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # 容器
        container = QFrame()
        container.setObjectName("loadingContainer")
        container.setStyleSheet(f"""
            QFrame#loadingContainer {{
                background-color: {COLORS['surface']};
                border-radius: {RADIUS['large']};
                padding: 32px 48px;
            }}
        """)

        # 添加阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(16)
        container_layout.setAlignment(Qt.AlignCenter)

        # 旋转动画
        self.spinner = LoadingSpinner(56)
        container_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)

        # 文字
        self.label = QLabel(self._text)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 15px;
                font-weight: 500;
            }}
        """)
        container_layout.addWidget(self.label, alignment=Qt.AlignCenter)

        layout.addWidget(container)

        self.hide()

    def set_text(self, text):
        """设置提示文字"""
        self._text = text
        self.label.setText(text)

    def show_overlay(self):
        """显示遮罩"""
        if self.parent():
            self.setGeometry(self.parent().rect())
            self.parent().installEventFilter(self)
        self.show()
        self.spinner.start()

    def eventFilter(self, obj, event):
        """监听父窗口大小变化"""
        from PyQt5.QtCore import QEvent
        if obj == self.parent() and event.type() == QEvent.Resize:
            self.setGeometry(self.parent().rect())
        return super().eventFilter(obj, event)

    def hide_overlay(self):
        """隐藏遮罩"""
        self.spinner.stop()
        self.hide()


# ==================== Empty State ====================

class EmptyStateWidget(QWidget):
    """空状态组件"""

    action_clicked = pyqtSignal()

    def __init__(self, icon="📭", title="暂无数据", description="", action_text="", parent=None):
        super().__init__(parent)
        self._icon = icon
        self._title = title
        self._description = description
        self._action_text = action_text

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        # 图标
        self.icon_label = QLabel(self._icon)
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("""
            QLabel {
                font-size: 64px;
                background: transparent;
            }
        """)
        layout.addWidget(self.icon_label, alignment=Qt.AlignCenter)

        # 标题
        self.title_label = QLabel(self._title)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 18px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(self.title_label, alignment=Qt.AlignCenter)

        # 描述
        if self._description:
            self.desc_label = QLabel(self._description)
            self.desc_label.setAlignment(Qt.AlignCenter)
            self.desc_label.setWordWrap(True)
            self.desc_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['text_secondary']};
                    font-size: 14px;
                    max-width: 280px;
                }}
            """)
            layout.addWidget(self.desc_label, alignment=Qt.AlignCenter)

        # 操作按钮
        if self._action_text:
            self.action_btn = QPushButton(self._action_text)
            self.action_btn.setMinimumHeight(44)
            self.action_btn.setCursor(Qt.PointingHandCursor)
            self.action_btn.setStyleSheet(get_button_style('primary'))
            self.action_btn.clicked.connect(self.action_clicked.emit)
            layout.addSpacing(8)
            layout.addWidget(self.action_btn, alignment=Qt.AlignCenter)

    def set_icon(self, icon):
        """设置图标"""
        self._icon = icon
        self.icon_label.setText(icon)

    def set_title(self, title):
        """设置标题"""
        self._title = title
        self.title_label.setText(title)


# ==================== Custom MessageBox ====================

class CustomMessageBox(QDialog):
    """自定义消息对话框"""

    def __init__(self, title="提示", message="", icon_type="info", parent=None):
        """
        icon_type: info, success, warning, error, question
        """
        super().__init__(parent)

        self._icon_type = icon_type
        self._result = None

        self.setWindowTitle(title)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.init_ui(title, message)

        # 允许拖动
        self._drag_pos = None

    def init_ui(self, title, message):
        """初始化UI"""
        # 根据消息行数动态调整高度（单行240，多行每行+22）
        lines = message.count('\n') + 1
        dlg_w, dlg_h = 400, max(240, 200 + lines * 22)
        self.setFixedSize(dlg_w, dlg_h)

        # 容器
        container = QFrame(self)
        container.setObjectName("msgContainer")
        container.setGeometry(16, 16, dlg_w - 32, dlg_h - 32)
        container.setStyleSheet(f"""
            QFrame#msgContainer {{
                background-color: {COLORS['surface']};
                border-radius: {RADIUS['xl']};
            }}
        """)

        # 阴影
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 12)
        container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(32, 32, 32, 24)
        layout.setSpacing(20)

        # 图标和标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        # 图标
        icon_map = {
            'info': ('💡', COLORS['primary']),
            'success': ('✅', COLORS['success']),
            'warning': ('⚠️', COLORS['warning']),
            'error': ('❌', COLORS['danger']),
            'question': ('❓', COLORS['primary'])
        }
        icon_text, icon_color = icon_map.get(self._icon_type, icon_map['info'])

        icon_label = QLabel(icon_text)
        icon_label.setStyleSheet("font-size: 36px; background: transparent;")
        header_layout.addWidget(icon_label)

        # 标题
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 18px;
                font-weight: 600;
            }}
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # 消息
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 14px;
                line-height: 1.5;
            }}
        """)
        layout.addWidget(msg_label)

        layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        if self._icon_type == 'question':
            # 确认/取消按钮
            self.btn_cancel = QPushButton("取 消")
            self.btn_cancel.setMinimumHeight(46)
            self.btn_cancel.setMinimumWidth(110)
            self.btn_cancel.setCursor(Qt.PointingHandCursor)
            self.btn_cancel.setStyleSheet(get_button_style('secondary'))
            self.btn_cancel.clicked.connect(self._on_cancel)
            btn_layout.addWidget(self.btn_cancel)

            self.btn_confirm = QPushButton("确 认")
            self.btn_confirm.setMinimumHeight(46)
            self.btn_confirm.setMinimumWidth(110)
            self.btn_confirm.setCursor(Qt.PointingHandCursor)
            self.btn_confirm.setStyleSheet(get_button_style('primary'))
            self.btn_confirm.clicked.connect(self._on_confirm)
            btn_layout.addWidget(self.btn_confirm)
        else:
            self.btn_ok = QPushButton("确 定")
            self.btn_ok.setMinimumHeight(46)
            self.btn_ok.setMinimumWidth(110)
            self.btn_ok.setCursor(Qt.PointingHandCursor)
            self.btn_ok.setStyleSheet(get_button_style('primary'))
            self.btn_ok.clicked.connect(self.accept)
            btn_layout.addStretch()
            btn_layout.addWidget(self.btn_ok)

        layout.addLayout(btn_layout)

    def _on_confirm(self):
        """确认"""
        self._result = True
        self.accept()

    def _on_cancel(self):
        """取消"""
        self._result = False
        self.reject()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()


# ==================== Toast Notification ====================

class ToastNotification(QFrame):
    """Toast通知组件"""

    def __init__(self, message="", toast_type="info", duration=3000, parent=None):
        """
        toast_type: info, success, warning, error
        """
        super().__init__(parent)

        self._duration = duration
        self._toast_type = toast_type

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.init_ui(message)

        # 自动关闭定时器
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide_animated)

        # 淡入淡出动画
        self._opacity = 1.0

    def init_ui(self, message):
        """初始化UI"""
        self.setObjectName("toastFrame")

        # 根据类型设置背景色和字体色
        style_configs = {
            'info': {'bg': COLORS['primary_light'], 'text': COLORS['primary'], 'border': COLORS['primary']},
            'success': {'bg': '#E8F5E9', 'text': '#2E7D32', 'border': COLORS['success']},
            'warning': {'bg': '#FFF3E0', 'text': '#E65100', 'border': '#FF9800'},
            'error': {'bg': '#FFEBEE', 'text': '#C62828', 'border': COLORS['danger']}
        }
        config = style_configs.get(self._toast_type, style_configs['info'])
        bg_color = config['bg']
        text_color = config['text']
        border_color = config['border']

        # 图标
        icon_map = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }
        icon = icon_map.get(self._toast_type, icon_map['info'])

        self.setStyleSheet(f"""
            QFrame#toastFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: {RADIUS['medium']};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(12)

        # 图标
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px; background: transparent;")
        layout.addWidget(icon_label)

        # 消息（深色字体）
        msg_label = QLabel(message)
        msg_label.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-size: 14px;
                font-weight: 500;
                background: transparent;
            }}
        """)
        layout.addWidget(msg_label)

        self.adjustSize()

    def show_toast(self):
        """显示Toast"""
        # 计算位置（屏幕右下角）
        if self.parent():
            parent_rect = self.parent().rect()
            x = parent_rect.width() - self.width() - 24
            y = parent_rect.height() - self.height() - 24
        else:
            screen = QApplication.primaryScreen().geometry()
            x = screen.width() - self.width() - 24
            y = screen.height() - self.height() - 100

        self.move(x, y)
        self.show()
        self._timer.start(self._duration)

    def hide_animated(self):
        """隐藏动画"""
        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(200)
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self.hide)
        self._fade_animation.start()


# ==================== 便捷函数 ====================

def show_toast(parent, message, toast_type="info", duration=3000):
    """显示Toast通知"""
    toast = ToastNotification(message, toast_type, duration, parent)
    toast.show_toast()
    return toast


def show_confirm(parent, title, message):
    """显示确认对话框，返回True/False"""
    dlg = CustomMessageBox(title, message, "question", parent)
    result = dlg.exec_()
    return dlg._result if hasattr(dlg, '_result') else False


def show_info(parent, title, message):
    """显示信息对话框"""
    dlg = CustomMessageBox(title, message, "info", parent)
    dlg.exec_()


def show_warning(parent, title, message):
    """显示警告对话框"""
    dlg = CustomMessageBox(title, message, "warning", parent)
    dlg.exec_()


def show_error(parent, title, message):
    """显示错误对话框"""
    dlg = CustomMessageBox(title, message, "error", parent)
    dlg.exec_()


def show_success(parent, title, message):
    """显示成功对话框"""
    dlg = CustomMessageBox(title, message, "success", parent)
    dlg.exec_()