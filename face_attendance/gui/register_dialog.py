"""
学生注册对话框
Apple 风格设计
"""
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QGroupBox, QFormLayout,
    QMessageBox, QFileDialog, QWidget, QFrame,
    QGraphicsDropShadowEffect, QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QColor

from utils.camera import CameraThread
import config
from .apple_style import (
    COLORS, RADIUS, get_button_style, ICONS
)


class RegisterWorker(QThread):
    """注册工作线程 - 避免阻塞UI"""
    finished = pyqtSignal(bool, str, object)  # success, message, encoding

    def __init__(self, detector, encoder, frame, parent=None):
        super().__init__(parent)
        self.detector = detector
        self.encoder = encoder
        self.frame = frame

    def run(self):
        try:
            # 一次调用完成检测+编码 (避免两次模型推理)
            dets = self.encoder.detect_and_encode(self.frame, max_num=5, resize_scale=1.0)

            if not dets:
                self.finished.emit(False, "未检测到人脸，请确保图片中有清晰的人脸", None)
                return

            if len(dets) > 1:
                self.finished.emit(False, "检测到多张人脸，请确保图片中只有一个人脸", None)
                return

            det = dets[0]
            quality = det['quality']
            min_q = getattr(config, 'FACE_REGISTRATION_MIN_QUALITY', 0.25)
            if quality['total_score'] < min_q:
                reason = quality.get('reject_reason', '质量不达标')
                self.finished.emit(False, f"人脸质量不达标: {reason}", None)
                return

            self.finished.emit(True, "检测成功", det['encoding'])

        except Exception as e:
            self.finished.emit(False, f"处理失败: {str(e)}", None)


class RegisterDialog(QDialog):
    """学生注册对话框 - Apple风格"""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)

        self.ctx = ctx

        self.detector = ctx.face_detector
        self.encoder = ctx.face_encoder

        self.camera_thread = None
        self.current_frame = None
        self.captured_frame = None
        self.register_worker = None  # 注册工作线程
        self.face_encoding = None  # 存储提取的特征

        self.init_ui()

    def init_ui(self):
        """初始化UI - Apple风格"""
        self.setWindowTitle("学生注册")
        self.setMinimumSize(800, 550)
        self.setStyleSheet(f"background-color: {COLORS['background']};")

        layout = QHBoxLayout(self)
        layout.setSpacing(24)
        layout.setContentsMargins(24, 24, 24, 24)

        # 左侧：图像区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(16)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 图像容器
        image_container = QFrame()
        image_container.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['divider']};
                border-radius: {RADIUS['large']};
            }}
        """)
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(16, 16, 16, 16)
        image_layout.setSpacing(12)

        # 图像显示
        self.image_label = QLabel(f"{ICONS['camera']}  点击\"打开摄像头\"或\"选择图片\"")
        self.image_label.setMinimumSize(400, 320)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['video_bg']};
                color: {COLORS['text_secondary']};
                font-size: 15px;
                border: none;
                border-radius: {RADIUS['medium']};
            }}
        """)
        image_layout.addWidget(self.image_label)

        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_camera = QPushButton("打开摄像头")
        self.btn_camera.setMinimumHeight(44)
        self.btn_camera.setCursor(Qt.PointingHandCursor)
        self.btn_camera.setStyleSheet(get_button_style('secondary'))
        self.btn_camera.clicked.connect(self.toggle_camera)
        btn_layout.addWidget(self.btn_camera)

        self.btn_capture = QPushButton("拍照")
        self.btn_capture.setMinimumHeight(44)
        self.btn_capture.setCursor(Qt.PointingHandCursor)
        self.btn_capture.setStyleSheet(get_button_style('primary'))
        self.btn_capture.clicked.connect(self.capture_image)
        self.btn_capture.setEnabled(False)
        btn_layout.addWidget(self.btn_capture)

        self.btn_file = QPushButton("选择图片")
        self.btn_file.setMinimumHeight(44)
        self.btn_file.setCursor(Qt.PointingHandCursor)
        self.btn_file.setStyleSheet(get_button_style('secondary'))
        self.btn_file.clicked.connect(self.select_image)
        btn_layout.addWidget(self.btn_file)

        image_layout.addLayout(btn_layout)
        left_layout.addWidget(image_container)

        layout.addWidget(left_widget)

        # 右侧：信息输入
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(16)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 学生信息容器
        info_container = QFrame()
        info_container.setObjectName("infoContainer")
        info_container.setStyleSheet(f"""
            QFrame#infoContainer {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['divider']};
                border-radius: {RADIUS['large']};
            }}
        """)
        info_layout = QVBoxLayout(info_container)
        info_layout.setContentsMargins(28, 24, 28, 28)
        info_layout.setSpacing(18)

        # 标题区域（带图标）
        header_row = QHBoxLayout()
        header_icon = QLabel(ICONS['students'])
        header_icon.setStyleSheet("font-size: 22px; background: transparent;")
        header_row.addWidget(header_icon)
        title_label = QLabel("学生信息")
        title_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 20px; font-weight: 700; background: transparent;")
        header_row.addWidget(title_label)
        header_row.addStretch()
        info_layout.addLayout(header_row)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['divider']};")
        info_layout.addWidget(sep)

        # 学号
        self.edit_student_id = QLineEdit()
        self.edit_student_id.setPlaceholderText("请输入学号")
        info_layout.addLayout(self._labeled_input("学号", self.edit_student_id))

        # 姓名
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("请输入姓名")
        info_layout.addLayout(self._labeled_input("姓名", self.edit_name))

        # 班级
        self.edit_class = QLineEdit()
        self.edit_class.setPlaceholderText("请输入班级")
        info_layout.addLayout(self._labeled_input("班级", self.edit_class))

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['danger']};
                font-size: 13px;
                padding: 10px 14px;
                background-color: rgba(255, 59, 48, 0.1);
                border-radius: {RADIUS['small']};
            }}
        """)
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        info_layout.addWidget(self.status_label)

        info_layout.addStretch()
        right_layout.addWidget(info_container)

        # 操作按钮
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        self.btn_register = QPushButton("注 册")
        self.btn_register.setMinimumHeight(50)
        self.btn_register.setCursor(Qt.PointingHandCursor)
        self.btn_register.setStyleSheet(get_button_style('success'))
        self.btn_register.clicked.connect(self.register_student)
        btn_box.addWidget(self.btn_register, 1)
        self.btn_cancel = QPushButton("取 消")
        self.btn_cancel.setMinimumHeight(50)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet(get_button_style('secondary'))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel, 1)
        right_layout.addLayout(btn_box)

        layout.addWidget(right_widget)

    def _labeled_input(self, label: str, edit: QLineEdit) -> QVBoxLayout:
        """标签 + 输入框"""
        lay = QVBoxLayout()
        lay.setSpacing(8)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600; background: transparent;")
        lay.addWidget(lbl)
        edit.setMinimumHeight(46)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 2px solid {COLORS['divider']};
                border-radius: {RADIUS['medium']};
                padding: 0 16px;
                font-size: 15px;
            }}
            QLineEdit:hover {{ border-color: {COLORS['text_placeholder']}; }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
                background-color: {COLORS['surface']};
            }}
            QLineEdit::placeholder {{ color: {COLORS['text_placeholder']}; }}
        """)
        lay.addWidget(edit)
        return lay

    def toggle_camera(self):
        """切换摄像头"""
        if self.camera_thread and self.camera_thread.is_running():
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        """启动摄像头"""
        try:
            self.camera_thread = CameraThread(
                camera_index=config.CAMERA_INDEX,
                width=config.CAMERA_WIDTH,
                height=config.CAMERA_HEIGHT
            )
            self.camera_thread.frame_ready.connect(self.update_frame)
            self.camera_thread.start()

            self.btn_camera.setText("关闭摄像头")
            self.btn_camera.setStyleSheet(get_button_style('danger'))
            self.btn_capture.setEnabled(True)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法启动摄像头: {str(e)}")

    def stop_camera(self):
        """停止摄像头"""
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread = None

        self.btn_camera.setText("打开摄像头")
        self.btn_camera.setStyleSheet(get_button_style('secondary'))
        self.btn_capture.setEnabled(False)

    def update_frame(self, frame: np.ndarray):
        """更新视频帧"""
        self.current_frame = frame
        self.display_image(frame)

    def capture_image(self):
        """拍照"""
        if self.current_frame is not None:
            self.captured_frame = self.current_frame.copy()
            self.stop_camera()
            self.display_image(self.captured_frame)
            self.status_label.setText("已捕获图像，请填写信息并注册")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['success']};
                    font-size: 13px;
                    padding: 8px 12px;
                    background-color: rgba(52, 199, 89, 0.1);
                    border-radius: {RADIUS['small']};
                }}
            """)

    def select_image(self):
        """选择图片文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择人脸图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp)"
        )

        if file_path:
            image = cv2.imdecode(np.fromfile(file_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is not None:
                self.captured_frame = image
                self.display_image(image)
                self.status_label.setText("已选择图片，请填写信息并注册")
                self.status_label.setStyleSheet(f"""
                    QLabel {{
                        color: {COLORS['success']};
                        font-size: 13px;
                        padding: 8px 12px;
                        background-color: rgba(52, 199, 89, 0.1);
                        border-radius: {RADIUS['small']};
                    }}
                """)
            else:
                QMessageBox.warning(self, "错误", "无法读取图片文件")

    def display_image(self, image: np.ndarray):
        """显示图像 - 使用BGR888避免颜色转换"""
        h, w, ch = image.shape
        contiguous = np.ascontiguousarray(image)
        bytes_per_line = ch * w
        q_image = QImage(contiguous.data, w, h, bytes_per_line, QImage.Format_BGR888)
        scaled = q_image.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(QPixmap.fromImage(scaled))

    def register_student(self):
        """注册学生 - 非阻塞版本"""
        # 验证输入
        student_id = self.edit_student_id.text().strip()
        name = self.edit_name.text().strip()
        class_name = self.edit_class.text().strip()

        if not student_id:
            QMessageBox.warning(self, "提示", "请输入学号")
            return
        if not name:
            QMessageBox.warning(self, "提示", "请输入姓名")
            return
        if self.captured_frame is None:
            QMessageBox.warning(self, "提示", "请先拍照或选择图片")
            return

        # 检查学号是否已存在
        existing = self.ctx.student_service.get_student(student_id)
        if existing:
            QMessageBox.warning(self, "提示", f"学号 {student_id} 已存在")
            return

        # 禁用注册按钮，显示处理中
        self.btn_register.setEnabled(False)
        self.btn_register.setText("处理中...")
        self.status_label.setText("正在检测人脸并提取特征...")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['primary']};
                font-size: 13px;
                padding: 8px 12px;
                background-color: rgba(0, 122, 255, 0.1);
                border-radius: {RADIUS['small']};
            }}
        """)

        # 启动工作线程
        self.register_worker = RegisterWorker(
            self.detector, self.encoder, self.captured_frame
        )
        self.register_worker.finished.connect(self.on_register_finished)
        self.register_worker.start()

    def on_register_finished(self, success: bool, message: str, encoding):
        """注册处理完成回调"""
        # 恢复按钮状态
        self.btn_register.setEnabled(True)
        self.btn_register.setText("注册")

        if not success:
            self.status_label.setText(message)
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['danger']};
                    font-size: 13px;
                    padding: 8px 12px;
                    background-color: rgba(255, 59, 48, 0.1);
                    border-radius: {RADIUS['small']};
                }}
            """)
            return

        # 保存到数据库
        student_id = self.edit_student_id.text().strip()
        name = self.edit_name.text().strip()
        class_name = self.edit_class.text().strip()

        try:
            self.ctx.student_service.add_student_with_encoding(
                student_id=student_id,
                name=name,
                class_name=class_name,
                encoding=encoding
            )
            dlg = QDialog(self)
            dlg.setWindowTitle("提示")
            dlg.setFixedSize(360, 180)
            dlg.setStyleSheet(f"background-color: {COLORS['surface']};")
            dlg_layout = QVBoxLayout(dlg)
            dlg_layout.setContentsMargins(32, 32, 32, 24)
            dlg_layout.setSpacing(24)
            msg = QLabel(f"学生 {name} 注册成功")
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 16px; font-weight: 600;")
            dlg_layout.addWidget(msg)
            btn_ok = QPushButton("确 定")
            btn_ok.setMinimumHeight(44)
            btn_ok.setCursor(Qt.PointingHandCursor)
            btn_ok.setStyleSheet("""
                QPushButton {
                    background-color: #333333; color: white;
                    border: none; border-radius: 8px; font-size: 15px;
                    font-weight: 600; padding: 10px 28px;
                }
                QPushButton:hover { background-color: #555555; }
                QPushButton:pressed { background-color: #111111; }
            """)
            btn_ok.clicked.connect(dlg.accept)
            dlg_layout.addWidget(btn_ok)
            dlg.exec_()
            self.accept()

        except Exception as e:
            self.status_label.setText(f"注册失败: {str(e)}")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    color: {COLORS['danger']};
                    font-size: 13px;
                    padding: 8px 12px;
                    background-color: rgba(255, 59, 48, 0.1);
                    border-radius: {RADIUS['small']};
                }}
            """)

    def reject(self):
        """取消"""
        self.stop_camera()
        super().reject()

    def closeEvent(self, event):
        """关闭事件"""
        self.stop_camera()

        # 等待工作线程完成
        if self.register_worker and self.register_worker.isRunning():
            self.register_worker.wait(2000)  # 等待最多2秒

        super().closeEvent(event)