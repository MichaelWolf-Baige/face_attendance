"""
考勤打卡面板
包含摄像头显示和考勤记录
Apple 风格设计
"""
import cv2
import numpy as np
import threading
import time
from datetime import datetime
from queue import Queue
from PIL import Image, ImageDraw, ImageFont
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QComboBox, QMessageBox, QHeaderView,
    QFrame, QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor

from utils.logger import get_logger
from utils.camera import CameraThread
import config
from .apple_style import (
    COLORS, RADIUS, SHADOWS, get_button_style,
    INPUT_STYLE, COMBO_STYLE, TABLE_STYLE,
    STATS_LABEL_STYLE, VIDEO_LABEL_STYLE, ICONS
)
from .widgets import LoadingOverlay, EmptyStateWidget, NoFocusDelegate
from .makeup_checkin_dialog import MakeupCheckInDialog

logger = get_logger(__name__)

# 全局缓存字体（只加载一次）
_cached_font = None

def _get_chinese_font():
    """获取中文字体（缓存）"""
    global _cached_font
    if _cached_font is None:
        try:
            _cached_font = ImageFont.truetype("msyh.ttc", 28)
        except:
            try:
                _cached_font = ImageFont.truetype("simsun.ttc", 28)
            except:
                _cached_font = ImageFont.load_default()
    return _cached_font


class FaceRecognitionThread(QThread):
    """人脸识别线程 - 避免阻塞UI"""
    result_ready = pyqtSignal(list)  # 识别结果信号

    def __init__(self, attendance_service):
        super().__init__()
        self.attendance_service = attendance_service
        self.frame_queue = Queue(maxsize=1)  # 只保留最新帧
        self._running = True

    def add_frame(self, frame):
        """添加帧到队列"""
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()  # 丢弃旧帧
            except Exception as e:
                logger.debug(f"清空帧队列时异常: {e}")
        self.frame_queue.put(frame)

    def run(self):
        # 确保人脸数据库已加载
        self.attendance_service.refresh_face_database()
        db_size = self.attendance_service.matcher.get_database_size()
        logger.info(f"人脸库已加载: {db_size} 人")

        while self._running:
            try:
                frame = self.frame_queue.get(timeout=0.5)
                results = self.attendance_service.process_frame(frame)

                # 将结果转换为可序列化格式（numpy数组不能跨线程传递）
                serializable_results = []
                for r in results:
                    serializable_results.append({
                        'name': r.get('name'),
                        'student_id': r.get('student_id'),
                        'confidence': float(r.get('confidence', 0)),
                        'bbox': tuple(r.get('bbox', (0, 0, 0, 0))),
                        'location': tuple(r.get('location', (0, 0, 0, 0))),
                        'track_id': r.get('track_id'),
                    })

                if serializable_results:
                    logger.debug(f"检测到 {len(serializable_results)} 人: {[r.get('name') for r in serializable_results]}")
                self.result_ready.emit(serializable_results)
            except Exception as e:
                logger.debug(f"帧处理异常: {e}")
                continue

    def stop(self):
        """停止线程 - 安全版本"""
        self._running = False
        # 清空队列避免阻塞
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except:
                break
        self.wait(3000)  # 等待最多3秒


class AttendancePanel(QWidget):
    """考勤打卡面板"""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)

        self.ctx = ctx
        self.attendance_service = ctx.attendance_service

        # 线程
        self.camera_thread = None
        self.recognition_thread = None
        self.current_frame = None
        self.last_results = []  # 缓存上次识别结果
        self._frame_counter = 0  # 帧计数器，用于跳帧
        self._last_drawn_results = None  # 上次绘制的结果，避免重复PIL转换
        self._cached_display = None  # 缓存绘制好的帧，结果不变时直接复用
        self._cached_pixmap = None  # 缓存QPixmap，避免每帧重复创建
        self._last_data_ptr = None  # 跟踪帧数据指针，判断是否需要重建QPixmap
        self._fps_t0 = time.time()       # FPS 计时起点
        self._fps_display_count = 0      # 显示帧数
        self._fps_recog_count = 0        # 识别帧数
        self._fps_display = 0            # 当前显示 FPS
        self._fps_recog = 0              # 当前识别 FPS

        # 初始化UI
        self.init_ui()

        # 刷新人脸数据库
        self.attendance_service.refresh_face_database()

        # 加载课程和班级列表
        self.load_courses()
        self.load_classes()

    def init_ui(self):
        """初始化UI - Apple风格"""
        # 先初始化需要的属性
        self.stats_labels = {}

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        # 左侧：摄像头区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(16)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 摄像头容器（带阴影）
        video_container = QFrame()
        video_container.setObjectName("videoContainer")
        video_container.setStyleSheet(f"""
            QFrame#videoContainer {{
                background-color: {COLORS['surface']};
                border-radius: {RADIUS['large']};
                border: 1px solid {COLORS['divider']};
            }}
        """)
        video_layout = QVBoxLayout(video_container)
        video_layout.setContentsMargins(16, 16, 16, 16)
        video_layout.setSpacing(12)

        # 摄像头显示标签
        self.video_label = QLabel(f"{ICONS['camera']}  点击\"开始考勤\"启动摄像头")
        self.video_label.setMinimumSize(320, 240)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['video_bg']};
                color: {COLORS['text_secondary']};
                font-size: 15px;
                border: none;
                border-radius: {RADIUS['medium']};
            }}
        """)
        self.video_label.setScaledContents(False)
        video_layout.addWidget(self.video_label)

        # FPS 显示标签
        self.fps_label = QLabel("FPS: --")
        self.fps_label.setAlignment(Qt.AlignCenter)
        self.fps_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 11px;
                background: transparent;
                border: none;
            }}
        """)
        video_layout.addWidget(self.fps_label)

        # 课程选择区域
        course_frame = QFrame()
        course_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['table_header']};
                border-radius: {RADIUS['medium']};
                padding: 8px;
            }}
        """)
        course_layout = QHBoxLayout(course_frame)
        course_layout.setContentsMargins(12, 8, 12, 8)
        course_layout.setSpacing(12)

        course_icon = QLabel(ICONS['courses'])
        course_icon.setStyleSheet("background: transparent; font-size: 16px;")
        course_layout.addWidget(course_icon)

        course_label = QLabel("当前课程")
        course_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 14px;
                background: transparent;
            }}
        """)
        course_layout.addWidget(course_label)

        # 班级筛选
        self.combo_class = QComboBox()
        self.combo_class.setMinimumWidth(160)
        self.combo_class.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['small']};
                padding: 10px 36px 10px 14px;
                font-size: 14px;
            }}
            QComboBox:hover {{ border-color: {COLORS['primary']}; }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border: none;
                border-left: 1px solid {COLORS['divider']};
            }}
        """)
        self.combo_class.addItem("全部班级", None)
        self.combo_class.currentIndexChanged.connect(self._on_class_changed)
        course_layout.addWidget(self.combo_class)

        self.combo_course = QComboBox()
        self.combo_course.setMinimumWidth(200)
        self.combo_course.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['small']};
                padding: 10px 36px 10px 14px;
                font-size: 14px;
                min-width: 120px;
            }}
            QComboBox:hover {{ border-color: {COLORS['primary']}; }}
            QComboBox:focus  {{ border-color: {COLORS['primary']}; }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border: none;
                border-left: 1px solid {COLORS['divider']};
                border-top-right-radius: {RADIUS['small']};
                border-bottom-right-radius: {RADIUS['small']};
            }}
            QComboBox::down-arrow {{
                width: 12px;
                height: 12px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['medium']};
                padding: 6px;
                outline: none;
                selection-background-color: {COLORS['primary_light']};
                selection-color: {COLORS['text_primary']};
            }}
            QComboBox QAbstractItemView::item {{
                padding: 10px 14px;
                border-radius: {RADIUS['small']};
                margin: 1px 0;
                font-size: 14px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {COLORS['table_header']};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary']};
                font-weight: 600;
            }}
        """)
        course_layout.addWidget(self.combo_course)
        course_layout.addStretch()

        video_layout.addWidget(course_frame)

        # 控制按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_start = QPushButton(f"{ICONS['camera']}  开始考勤")
        self.btn_start.setMinimumHeight(48)
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setStyleSheet(get_button_style('success'))
        self.btn_start.setToolTip("启动摄像头开始人脸识别考勤")
        self.btn_start.clicked.connect(self.toggle_camera)
        btn_layout.addWidget(self.btn_start, 1)

        self.btn_capture = QPushButton(f"{ICONS['capture']}  手动补签")
        self.btn_capture.setMinimumHeight(48)
        self.btn_capture.setCursor(Qt.PointingHandCursor)
        self.btn_capture.setStyleSheet(get_button_style('primary'))
        self.btn_capture.setToolTip("从名单中直接选择未打卡学生，批量补签")
        self.btn_capture.clicked.connect(self.open_makeup_checkin)
        btn_layout.addWidget(self.btn_capture, 1)

        video_layout.addLayout(btn_layout)

        left_layout.addWidget(video_container)
        layout.addWidget(left_widget, 3)

        # 右侧：考勤记录
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(16)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 记录容器
        record_container = QFrame()
        record_container.setObjectName("recordContainer")
        record_container.setStyleSheet(f"""
            QFrame#recordContainer {{
                background-color: {COLORS['surface']};
                border-radius: {RADIUS['large']};
                border: 1px solid {COLORS['divider']};
            }}
        """)
        record_layout = QVBoxLayout(record_container)
        record_layout.setContentsMargins(20, 20, 20, 20)
        record_layout.setSpacing(16)

        # 标题区域
        header_layout = QHBoxLayout()

        title_label = QLabel("今日考勤记录")
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 18px;
                font-weight: 600;
            }}
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        record_layout.addLayout(header_layout)

        # 统计信息卡片
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['table_header']};
                border-radius: {RADIUS['medium']};
            }}
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(16, 12, 16, 12)

        # 正常统计
        normal_stat = self._create_stat_item("正常", "0", COLORS['success'])
        stats_layout.addWidget(normal_stat)

        # 分隔线
        separator1 = QFrame()
        separator1.setFixedSize(1, 32)
        separator1.setStyleSheet(f"background-color: {COLORS['divider']};")
        stats_layout.addWidget(separator1)

        # 迟到统计
        late_stat = self._create_stat_item("迟到", "0", COLORS['warning'])
        stats_layout.addWidget(late_stat)

        # 分隔线
        separator2 = QFrame()
        separator2.setFixedSize(1, 32)
        separator2.setStyleSheet(f"background-color: {COLORS['divider']};")
        stats_layout.addWidget(separator2)

        # 缺勤统计
        absent_stat = self._create_stat_item("缺勤", "0", COLORS['danger'])
        stats_layout.addWidget(absent_stat)

        # 分隔线
        separator3 = QFrame()
        separator3.setFixedSize(1, 32)
        separator3.setStyleSheet(f"background-color: {COLORS['divider']};")
        stats_layout.addWidget(separator3)

        # 出勤率统计
        rate_stat = self._create_stat_item("出勤率", "0%", COLORS['primary'])
        stats_layout.addWidget(rate_stat)

        # 分隔线
        separator4 = QFrame()
        separator4.setFixedSize(1, 32)
        separator4.setStyleSheet(f"background-color: {COLORS['divider']};")
        stats_layout.addWidget(separator4)

        # 总计统计
        total_stat = self._create_stat_item("总计", "0", COLORS['text_primary'])
        stats_layout.addWidget(total_stat)

        record_layout.addWidget(stats_frame)

        # 考勤记录表格
        self.record_table = QTableWidget()
        self.record_table.setColumnCount(3)
        self.record_table.setHorizontalHeaderLabels(["姓名", "状态", "置信度"])
        self.record_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.record_table.setAlternatingRowColors(True)
        self.record_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.record_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.record_table.verticalHeader().setVisible(False)
        self.record_table.setSortingEnabled(True)  # 启用排序
        self.record_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface']};
                alternate-background-color: {COLORS['table_alternate']};
                border: 1px solid {COLORS['divider']};
                border-radius: {RADIUS['medium']};
                gridline-color: {COLORS['divider']};
                font-size: 14px;
            }}
            QTableWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {COLORS['divider']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['table_selected']};
                color: {COLORS['text_primary']};
            }}
            QTableWidget::item:focus {{
                outline: none;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {COLORS['table_header']};
                color: {COLORS['text_secondary']};
                font-weight: 600;
                padding: 12px;
                border: none;
                border-bottom: 1px solid {COLORS['divider']};
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        self.record_table.setItemDelegate(NoFocusDelegate())
        self.record_table.setFocusPolicy(Qt.NoFocus)
        record_layout.addWidget(self.record_table)

        right_layout.addWidget(record_container)
        layout.addWidget(right_widget, 2)

        # Loading 遮罩层
        self.loading_overlay = LoadingOverlay(self, "正在启动摄像头...")

        # 定时刷新记录
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_records)
        self.refresh_timer.start(5000)

        # 初始加载记录
        self.refresh_records()

    def _create_stat_item(self, label: str, value: str, color: str) -> QWidget:
        """创建统计项"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 0, 8, 0)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 12px;
            }}
        """)
        label_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 24px;
                font-weight: 700;
            }}
        """)
        value_widget.setAlignment(Qt.AlignCenter)
        layout.addWidget(value_widget)

        # 存储引用以便更新
        self.stats_labels[label] = value_widget

        return widget

    def load_courses(self):
        """加载课程列表（先清空再重新加载）"""
        self.combo_course.blockSignals(True)
        self.combo_course.clear()
        self.combo_course.addItem("未选择课程", None)
        courses = self.ctx.course_service.get_all_courses()
        for course in courses:
            self.combo_course.addItem(
                f"{course['course_name']} ({course['course_code']})",
                course['id']
            )
        self.combo_course.blockSignals(False)

    def load_classes(self):
        """加载班级列表到筛选下拉框（先清空再重新加载）"""
        self.combo_class.blockSignals(True)
        self.combo_class.clear()
        self.combo_class.addItem("全部班级", None)
        students = self.ctx.student_service.get_all_students()
        classes = sorted(set(
            s.get('class_name') for s in students
            if s.get('class_name')
        ))
        for cls in classes:
            self.combo_class.addItem(cls, cls)
        self.combo_class.blockSignals(False)

    def _on_class_changed(self):
        """班级筛选变化时刷新人脸库和统计"""
        class_name = self.combo_class.currentData()
        self.attendance_service.refresh_face_database(class_name=class_name)
        self.refresh_records()

    def toggle_camera(self):
        """切换摄像头状态"""
        if self.camera_thread and self.camera_thread.is_running():
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        """启动摄像头"""
        try:
            # 显示loading
            self.loading_overlay.set_text("正在启动摄像头...")
            self.loading_overlay.show_overlay()

            # 启动摄像头线程（使用config配置）
            self.camera_thread = CameraThread(
                camera_index=self.ctx.camera_index,
                width=self.ctx.camera_width,
                height=self.ctx.camera_height
            )
            self.camera_thread.frame_ready.connect(self.on_frame_ready)
            self.camera_thread.error_occurred.connect(self.on_camera_error)
            self.camera_thread.start()

            # 启动人脸识别线程
            self.recognition_thread = FaceRecognitionThread(self.attendance_service)
            self.recognition_thread.result_ready.connect(self.on_recognition_result)
            self.recognition_thread.start()

            self.btn_start.setText(f"{ICONS['camera']}  停止考勤")
            self.btn_start.setStyleSheet(get_button_style('danger'))

            # 延迟隐藏loading（等待第一帧）
            QTimer.singleShot(1000, self.loading_overlay.hide_overlay)

        except Exception as e:
            self.loading_overlay.hide_overlay()
            QMessageBox.critical(self, "错误", f"无法启动摄像头: {str(e)}")

    def stop_camera(self):
        """停止摄像头 - 完整清理版本"""
        self._cached_display = None
        self._last_drawn_results = None
        self.last_results = []
        self.fps_label.setText("FPS: --")
        self._fps_display_count = 0
        self._fps_recog_count = 0
        # 停止摄像头线程
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread = None

        # 停止识别线程
        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread = None

        # 重置UI
        self.btn_start.setText(f"{ICONS['camera']}  开始考勤")
        self.btn_start.setStyleSheet(get_button_style('success'))
        self.video_label.setText(f"{ICONS['camera']}  点击\"开始考勤\"启动摄像头")
        self.last_results = []
        self.current_frame = None

    def on_frame_ready(self, frame):
        """摄像头帧就绪"""
        self.current_frame = frame
        self._frame_counter += 1

        # FPS 统计
        t = time.time()
        self._fps_display_count += 1
        if t - self._fps_t0 >= 1.0:
            self._fps_display = self._fps_display_count / (t - self._fps_t0)
            self._fps_recog = self._fps_recog_count / (t - self._fps_t0)
            self._fps_display_count = 0
            self._fps_recog_count = 0
            self._fps_t0 = t
            self.fps_label.setText(
                f"Display: {self._fps_display:.0f} fps  |  Recognition: {self._fps_recog:.0f} fps"
            )

        # 识别: 每N帧处理一次
        if self.recognition_thread and self._frame_counter % getattr(config, 'ATTENDANCE_FRAME_SKIP', 10) == 0:
            self.recognition_thread.add_frame(frame)

        # 显示: 保持30fps画面流畅
        self.draw_results(frame)

    def on_recognition_result(self, results):
        """识别结果就绪 - 结果持久化，不清除旧结果"""
        self._fps_recog_count += 1
        logger.debug(f"收到识别结果: {len(results)} 人, {[r.get('name') for r in results]}")
        # 有结果才更新，空结果保留上次识别的人名不闪
        if results:
            self.last_results = results

        # 自动打卡逻辑
        if results:
            course_id = self.combo_course.currentData()
            for result in results:
                student_id = result.get('student_id')
                if student_id:
                    success, status, message = self.attendance_service.check_in(
                        student_id,
                        course_id,
                        result.get('confidence')
                    )
                    if success:
                        logger.info(f"自动打卡: {message}")
            # 刷新记录显示
            self.refresh_records()

    def _draw_label(self, frame, left, top, name, confidence, color):
        """PIL渲染文字标签，alpha混合到BGR帧。全链路BGR，零色彩转换"""
        font = _get_chinese_font()
        label = f"{name} {confidence:.0%}"
        label_y = max(0, top - 32)

        # 用 PIL 渲染文字到小 RGBA
        dummy = Image.new('RGBA', (1, 1))
        tmp_draw = ImageDraw.Draw(dummy)
        tbbox = tmp_draw.textbbox((0, 0), label, font=font)
        tw, th = tbbox[2] - tbbox[0], tbbox[3] - tbbox[1]
        pad = 4

        # color 是 cv2 BGR 格式 (B, G, R)，PIL 需要 RGB/A 格式 (R, G, B, A)
        b, g, r = int(color[0]), int(color[1]), int(color[2])
        label_img = Image.new('RGBA', (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
        label_draw = ImageDraw.Draw(label_img)
        label_draw.rectangle([0, 0, tw + pad * 2 - 1, th + pad * 2 - 1],
                             fill=(0, 0, 0, 180), outline=(r, g, b, 255), width=2)
        label_draw.text((pad - tbbox[0], pad - tbbox[1]), label, font=font, fill=(255, 255, 255, 255))

        # PIL RGBA → numpy，取 BGR 通道顺序用于混合（R,G,B → B,G,R）
        label_rgba = np.array(label_img)
        label_bgr = label_rgba[:, :, 2::-1]  # RGBA[:,:,2::-1] → BGR
        alpha = label_rgba[:, :, 3:4] / 255.0

        x1 = max(0, left)
        y1 = max(0, label_y)
        x2 = min(frame.shape[1], x1 + label_img.width)
        y2 = min(frame.shape[0], y1 + label_img.height)
        lx2 = x2 - x1
        ly2 = y2 - y1

        if lx2 > 0 and ly2 > 0:
            roi = frame[y1:y2, x1:x2]
            blended = (label_bgr[:ly2, :lx2] * alpha[:ly2, :lx2] + roi * (1 - alpha[:ly2, :lx2])).astype(np.uint8)
            frame[y1:y2, x1:x2] = blended

    def draw_results(self, frame):
        """在帧上绘制识别结果 - 只渲染文字区域，不转换全帧"""
        if not self.last_results:
            self._last_drawn_results = None
            self._cached_display = None
            self._invalidate_display_cache()
            self.display_image(frame)
            return

        # 结果没变 → 直接复用缓存
        if self.last_results == self._last_drawn_results and self._cached_display is not None:
            self.display_image(self._cached_display)
            return

        self._last_drawn_results = list(self.last_results)
        display_frame = frame.copy()

        for result in self.last_results:
            left, top, width, height = result.get('bbox', (0, 0, 0, 0))
            name = result.get('name') or "Unknown"
            bgr_color = (0, 255, 0) if name != "Unknown" else (0, 0, 255)
            cv2.rectangle(display_frame, (left, top), (left + width, top + height), bgr_color, 2)
            self._draw_label(display_frame, left, top, name, result.get('confidence', 0), bgr_color)

        self._cached_display = display_frame
        self.display_image(display_frame)

    def display_image(self, image):
        """显示图像 - 缓存QPixmap，同帧跳过重建"""
        # 同一帧数据 → 直接复用QPixmap（最省）
        data_ptr = image.ctypes.data
        if data_ptr == self._last_data_ptr and self._cached_pixmap is not None:
            self.video_label.setPixmap(self._cached_pixmap)
            return

        self._last_data_ptr = data_ptr
        h, w, ch = image.shape
        bytes_per_line = ch * w
        q_image = QImage(image.data, w, h, bytes_per_line, QImage.Format_BGR888)
        self._cached_pixmap = QPixmap.fromImage(
            q_image.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.FastTransformation))
        self.video_label.setPixmap(self._cached_pixmap)

    def _invalidate_display_cache(self):
        self._last_data_ptr = None
        self._cached_pixmap = None

    def on_camera_error(self, error_msg):
        """摄像头错误处理"""
        QMessageBox.critical(self, "摄像头错误", error_msg)
        self.stop_camera()

    def open_makeup_checkin(self):
        """打开手动补签对话框"""
        course_id = self.combo_course.currentData()
        class_name = self.combo_class.currentData()
        dialog = MakeupCheckInDialog(
            self.ctx,
            course_id=course_id,
            class_name=class_name,
            parent=self
        )
        if dialog.exec_() == MakeupCheckInDialog.Accepted:
            self.refresh_records()
            # 刷新人脸数据库（可能有新班级数据）
            self.attendance_service.refresh_face_database(class_name=self.combo_class.currentData())

    def refresh_records(self):
        """刷新考勤记录（按课程+班级过滤）"""
        course_id = self.combo_course.currentData()
        class_name = self.combo_class.currentData()

        if course_id is None:
            records = self.ctx.attendance_service.get_today_records()
        else:
            records = self.ctx.attendance_service.get_today_records(course_id)

        # 按班级过滤记录
        if class_name:
            records = [r for r in records if r.get('student_class') == class_name]

        self.record_table.setRowCount(len(records))
        for row, record in enumerate(records):
            self.record_table.setItem(row, 0, QTableWidgetItem(str(record.get('student_name', ''))))

            status = record['status']
            status_text = '正常' if status == 'normal' else ('迟到' if status == 'late' else '缺勤')
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)

            if status == 'normal':
                status_item.setForeground(QColor(COLORS['success']))
            elif status == 'late':
                status_item.setForeground(QColor(COLORS['warning']))
            else:
                status_item.setForeground(QColor(COLORS['danger']))
            self.record_table.setItem(row, 1, status_item)

            confidence = record.get('confidence')
            confidence_text = f'{confidence:.0%}' if confidence else ''
            self.record_table.setItem(row, 2, QTableWidgetItem(confidence_text))

        # 按学号+姓名去重统计（同一人多条记录只算一次）
        normal_students = set()
        late_students = set()
        for r in records:
            key = (r.get('student_id', ''), r.get('student_name', ''))
            if r['status'] == 'normal':
                normal_students.add(key)
            elif r['status'] == 'late':
                late_students.add(key)

        # 如果某个学生既有正常又有迟到，以迟到为准（从正常集合中移除）
        normal_students -= late_students

        # 按班级筛选后的总人数
        class_name = self.combo_class.currentData()
        all_students = self.ctx.student_service.get_all_students()
        if class_name:
            all_students = [s for s in all_students if s.get('class_name') == class_name]
        total_students = len(all_students)
        checked_in = len(normal_students) + len(late_students)
        attendance_rate = (checked_in / total_students * 100) if total_students > 0 else 0
        absent_count = total_students - checked_in

        # 更新统计标签
        if hasattr(self, 'stats_labels'):
            if '正常' in self.stats_labels:
                self.stats_labels['正常'].setText(str(len(normal_students)))
            if '迟到' in self.stats_labels:
                self.stats_labels['迟到'].setText(str(len(late_students)))
            if '缺勤' in self.stats_labels:
                self.stats_labels['缺勤'].setText(str(absent_count))
            if '出勤率' in self.stats_labels:
                self.stats_labels['出勤率'].setText(f'{attendance_rate:.0f}%')
            if '总计' in self.stats_labels:
                self.stats_labels['总计'].setText(str(total_students))

    def showEvent(self, event):
        """面板显示时恢复定时器并刷新下拉列表"""
        super().showEvent(event)
        if hasattr(self, 'refresh_timer'):
            self.load_courses()
            self.load_classes()
            self.refresh_timer.start(5000)
            self.refresh_records()

    def hideEvent(self, event):
        """面板隐藏时停止定时器"""
        super().hideEvent(event)
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()

    def closeEvent(self, event):
        """关闭事件 - 完整清理"""
        # 停止定时器
        self.refresh_timer.stop()

        # 停止摄像头和识别线程
        self.stop_camera()

        # 确保所有线程都已停止
        if self.recognition_thread:
            self.recognition_thread.wait(2000)  # 等待最多2秒

        super().closeEvent(event)