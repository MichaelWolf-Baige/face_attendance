"""
学生编辑对话框
Apple 风格设计
"""
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QGroupBox, QFormLayout,
    QMessageBox, QFileDialog, QWidget, QComboBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap

from utils.camera import CameraThread
import config
from .apple_style import (
    COLORS, RADIUS, get_button_style, ICONS
)


class EditStudentDialog(QDialog):
    """学生编辑对话框 - Apple风格"""

    def __init__(self, ctx, student_data: dict, parent=None):
        super().__init__(parent)

        self.ctx = ctx
        self.student_data = student_data
        self.detector = ctx.face_detector
        self.encoder = ctx.face_encoder

        self.camera_thread = None
        self.current_frame = None
        self.captured_frame = None

        self.init_ui()

    def init_ui(self):
        """初始化UI - Apple风格"""
        self.setWindowTitle(f"编辑学生 - {self.student_data['name']}")
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
        self.image_label = QLabel(f"{ICONS['camera']}  点击\"重新拍照\"或\"选择图片\"更新人脸")
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

        # 显示现有图片
        if self.student_data.get('face_image_path'):
            self.load_existing_image()

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

        # 标题
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

        # 学号（只读）
        sid_lbl = QLabel(self.student_data['student_id'])
        sid_lbl.setMinimumHeight(46)
        sid_lbl.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 15px;
                font-weight: 600;
                padding: 0 16px;
                background-color: {COLORS['divider']};
                border-radius: {RADIUS['medium']};
            }}
        """)
        info_layout.addLayout(self._labeled_input("学号", sid_lbl))

        # 姓名
        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("请输入姓名")
        self.edit_name.setText(self.student_data.get('name', ''))
        info_layout.addLayout(self._labeled_input("姓名", self.edit_name))

        # 班级
        self.edit_class = QLineEdit()
        self.edit_class.setPlaceholderText("请输入班级")
        self.edit_class.setText(self.student_data.get('class_name', '') or '')
        info_layout.addLayout(self._labeled_input("班级", self.edit_class))

        tip = QLabel("提示：如需更新人脸照片，请拍照或选择新图片")
        tip.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; padding: 10px 14px; background-color: {COLORS['table_header']}; border-radius: {RADIUS['small']};")
        tip.setWordWrap(True)
        info_layout.addWidget(tip)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"color: {COLORS['danger']}; font-size: 13px; padding: 10px 14px; background-color: rgba(255,59,48,0.1); border-radius: {RADIUS['small']};")
        self.status_label.setWordWrap(True)
        self.status_label.hide()
        info_layout.addWidget(self.status_label)

        info_layout.addStretch()
        right_layout.addWidget(info_container)

        # 按钮
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        self.btn_save = QPushButton("保 存")
        self.btn_save.setMinimumHeight(50)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet(get_button_style('success'))
        self.btn_save.clicked.connect(self.save_student)
        btn_box.addWidget(self.btn_save, 1)
        self.btn_cancel = QPushButton("取 消")
        self.btn_cancel.setMinimumHeight(50)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet(get_button_style('secondary'))
        self.btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_cancel, 1)
        right_layout.addLayout(btn_box)

        layout.addWidget(right_widget)

    def _labeled_input(self, label_text: str, widget) -> QVBoxLayout:
        """标签 + 控件（QLineEdit 或 QLabel）"""
        lay = QVBoxLayout()
        lay.setSpacing(8)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600; background: transparent;")
        lay.addWidget(lbl)

        if isinstance(widget, QLineEdit):
            widget.setMinimumHeight(46)
            widget.setStyleSheet(f"""
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
        lay.addWidget(widget)
        return lay

    def load_existing_image(self):
        """加载现有图片"""
        image_path = self.student_data.get('face_image_path')
        if image_path and os.path.exists(image_path):
            try:
                img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    self.display_image(img)
            except:
                pass

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
            self.status_label.setText("已捕获新图像")
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
                self.status_label.setText("已选择新图片")
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

    def save_student(self):
        """保存学生信息"""
        # 验证输入
        name = self.edit_name.text().strip()
        class_name = self.edit_class.text().strip()

        if not name:
            QMessageBox.warning(self, "提示", "请输入姓名")
            return

        # 更新基本信息
        try:
            self.ctx.student_service.update_student(
                self.student_data['student_id'],
                name=name,
                class_name=class_name
            )

            # 如果有新的人脸图片，更新人脸特征
            if self.captured_frame is not None:
                success, msg = self.ctx.student_service.update_face_encoding(
                    self.student_data['student_id'], self.captured_frame
                )
                if not success:
                    QMessageBox.warning(self, "提示", msg)

            QMessageBox.information(self, "成功", "学生信息已更新")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def reject(self):
        """取消"""
        self.stop_camera()
        super().reject()

    def closeEvent(self, event):
        """关闭事件"""
        self.stop_camera()
        super().closeEvent(event)