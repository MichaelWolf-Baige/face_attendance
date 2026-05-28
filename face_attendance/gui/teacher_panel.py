"""
教师管理面板
包含学生管理、课程管理、考勤记录和数据导出
Apple 风格设计
"""
import os
from datetime import datetime, date
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QGroupBox, QLineEdit, QComboBox, QMessageBox,
    QHeaderView, QFileDialog, QDateEdit, QTabWidget,
    QFormLayout, QDialog, QDialogButtonBox, QFrame,
    QSpacerItem, QSizePolicy, QProgressDialog, QInputDialog
)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt5.QtGui import QColor
from utils.logger import get_logger
logger = get_logger(__name__)

from utils.excel_exporter import ExcelExporter
from .register_dialog import RegisterDialog
from .edit_student_dialog import EditStudentDialog
from .edit_course_dialog import EditCourseDialog
from .apple_style import (
    COLORS, RADIUS, get_button_style, INPUT_STYLE,
    SEARCH_INPUT_STYLE, COMBO_STYLE, TABLE_STYLE,
    TAB_STYLE, GROUP_BOX_STYLE, DATE_EDIT_STYLE, ICONS,
    get_status_badge_style
)
from .widgets import EmptyStateWidget, show_toast, show_confirm, show_warning, NoFocusDelegate


class ImportWorker(QThread):
    """后台批量导入线程 - 支持取消和错误日志"""
    progress_signal = pyqtSignal(int, int, str)  # current, total, status
    finished_signal = pyqtSignal(int, list, str)  # success_count, errors, log_path

    def __init__(self, student_service, dir_path, class_name=None, parent=None):
        super().__init__(parent)
        self.student_service = student_service
        self.dir_path = dir_path
        self.class_name = class_name
        self._cancelled = False

    def cancel(self):
        """请求取消导入"""
        self._cancelled = True

    def run(self):
        # 错误日志写入项目目录
        log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_path = os.path.join(log_dir, f'import_errors_{timestamp}.log')

        kwargs = dict(
            progress_callback=self._on_progress,
            cancel_check=lambda: self._cancelled,
            error_log_path=log_path
        )

        if self.class_name:
            # 优先用 class_dir 模式（需要内部有 train/test/val）
            kwargs['class_dir'] = self.dir_path
            kwargs['class_name'] = self.class_name
            logger.info(f"[ImportWorker] 走 register_from_class_dir, dir={self.dir_path}, class={self.class_name}")
            imported, errors = self.student_service.register_from_class_dir(**kwargs)
            # 兜底：如果 class_dir 模式下没找到任何学生，用递归扫描模式
            if imported == 0:
                kwargs.pop('class_dir', None)
                kwargs['dir_path'] = self.dir_path
                kwargs['class_name'] = self.class_name
                logger.info(f"[ImportWorker] class_dir无结果，兜底 register_from_directory, class={self.class_name}")
                imported, errors = self.student_service.register_from_directory(**kwargs)
        else:
            kwargs['dir_path'] = self.dir_path
            logger.info(f"[ImportWorker] 走 register_from_directory, class_name=None")
            imported, errors = self.student_service.register_from_directory(**kwargs)

        # 如果没有任何错误，删除空日志文件
        if not errors and os.path.exists(log_path):
            try:
                os.remove(log_path)
                log_path = ""
            except OSError:
                pass

        self.finished_signal.emit(imported, errors, log_path)

    def _on_progress(self, current, total, status):
        self.progress_signal.emit(current, total, status)


class TeacherPanel(QWidget):
    """教师管理面板"""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)

        self.ctx = ctx
        self.student_service = ctx.student_service
        self.course_service = ctx.course_service
        self.attendance_service = ctx.attendance_service

        self.init_ui()

    def init_ui(self):
        """初始化UI - Apple风格（移除横向标签页，仅保留内容区域）"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # 使用 QStackedWidget 替代 QTabWidget，隐藏横向导航
        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().hide()  # 隐藏标签栏
        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['divider']};
                border-radius: {RADIUS['large']};
                top: 0px;
            }}
        """)

        # 学生管理标签页
        self.tab_students = self.create_students_tab()
        self.tab_widget.addTab(self.tab_students, "学生管理")

        # 课程管理标签页
        self.tab_courses = self.create_courses_tab()
        self.tab_widget.addTab(self.tab_courses, "课程管理")

        # 考勤记录标签页
        self.tab_records = self.create_records_tab()
        self.tab_widget.addTab(self.tab_records, "考勤记录")

        # 数据导出标签页
        self.tab_export = self.create_export_tab()
        self.tab_widget.addTab(self.tab_export, "数据导出")

        layout.addWidget(self.tab_widget)

    def create_students_tab(self) -> QWidget:
        """创建学生管理标签页 - Apple风格"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 搜索框
        search_layout = QHBoxLayout()

        search_icon = QLabel(ICONS['search'])
        search_icon.setStyleSheet("font-size: 16px;")
        search_layout.addWidget(search_icon)

        self.edit_search_student = QLineEdit()
        self.edit_search_student.setPlaceholderText("搜索学号、姓名或班级...")
        self.edit_search_student.setMinimumHeight(40)
        self.edit_search_student.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['table_header']};
                color: {COLORS['text_primary']};
                border: 2px solid transparent;
                border-radius: {RADIUS['medium']};
                padding: 0 16px;
                font-size: 14px;
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
        self.edit_search_student.textChanged.connect(self.search_students)
        search_layout.addWidget(self.edit_search_student, 1)
        layout.addLayout(search_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_add_student = QPushButton(f"{ICONS['add']}  添加学生")
        self.btn_add_student.setMinimumHeight(40)
        self.btn_add_student.setCursor(Qt.PointingHandCursor)
        self.btn_add_student.setStyleSheet(get_button_style('primary'))
        self.btn_add_student.setToolTip("添加新学生并注册人脸")
        self.btn_add_student.clicked.connect(self.add_student)
        btn_layout.addWidget(self.btn_add_student)

        self.btn_import_students = QPushButton("批量导入")
        self.btn_import_students.setMinimumHeight(40)
        self.btn_import_students.setCursor(Qt.PointingHandCursor)
        self.btn_import_students.setStyleSheet(get_button_style('secondary'))
        self.btn_import_students.setToolTip("从文件夹批量导入学生照片并注册")
        self.btn_import_students.clicked.connect(self.import_students)
        btn_layout.addWidget(self.btn_import_students)

        self.btn_edit_student = QPushButton(f"{ICONS['edit']}  编辑学生")
        self.btn_edit_student.setMinimumHeight(40)
        self.btn_edit_student.setCursor(Qt.PointingHandCursor)
        self.btn_edit_student.setStyleSheet(get_button_style('secondary'))
        self.btn_edit_student.setToolTip("编辑选中学生的信息和照片")
        self.btn_edit_student.clicked.connect(self.edit_student)
        btn_layout.addWidget(self.btn_edit_student)

        self.btn_delete_student = QPushButton(f"{ICONS['delete']}  删除学生")
        self.btn_delete_student.setMinimumHeight(40)
        self.btn_delete_student.setCursor(Qt.PointingHandCursor)
        self.btn_delete_student.setStyleSheet(get_button_style('danger'))
        self.btn_delete_student.setToolTip("删除选中的学生及人脸数据")
        self.btn_delete_student.clicked.connect(self.delete_student)
        btn_layout.addWidget(self.btn_delete_student)

        self.btn_refresh_students = QPushButton(ICONS['refresh'])
        self.btn_refresh_students.setMinimumHeight(40)
        self.btn_refresh_students.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_students.setStyleSheet(get_button_style('ghost'))
        self.btn_refresh_students.setToolTip("刷新学生列表")
        self.btn_refresh_students.clicked.connect(self.refresh_students)
        btn_layout.addWidget(self.btn_refresh_students)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 学生列表表格
        self.students_table = QTableWidget()
        self.students_table.setColumnCount(4)
        self.students_table.setHorizontalHeaderLabels(["学号", "姓名", "班级", "注册时间"])
        self.students_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.students_table.setAlternatingRowColors(True)
        self.students_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.students_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.students_table.verticalHeader().setVisible(False)
        self.students_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.students_table.customContextMenuRequested.connect(self._on_student_context_menu)
        self.students_table.doubleClicked.connect(self.edit_student)
        self.students_table.setStyleSheet(f"""
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
                padding: 14px;
                border: none;
                border-bottom: 1px solid {COLORS['divider']};
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        self.students_table.setItemDelegate(NoFocusDelegate())
        self.students_table.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.students_table)

        # 缓存学生列表用于搜索
        self._all_students = []

        # 初始加载
        self.refresh_students()

        return widget

    def create_courses_tab(self) -> QWidget:
        """创建课程管理标签页 - Apple风格优化版"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 搜索框
        search_layout = QHBoxLayout()

        search_icon = QLabel(ICONS['search'])
        search_icon.setStyleSheet("font-size: 16px;")
        search_layout.addWidget(search_icon)

        self.edit_search_course = QLineEdit()
        self.edit_search_course.setPlaceholderText("搜索课程代码或名称...")
        self.edit_search_course.setMinimumHeight(40)
        self.edit_search_course.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['table_header']};
                color: {COLORS['text_primary']};
                border: 2px solid transparent;
                border-radius: {RADIUS['medium']};
                padding: 0 16px;
                font-size: 14px;
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
        self.edit_search_course.textChanged.connect(self.search_courses)
        search_layout.addWidget(self.edit_search_course, 1)
        layout.addLayout(search_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        # 新建课程按钮（主要操作）
        self.btn_add_course = QPushButton(f"{ICONS['add']}  新建课程")
        self.btn_add_course.setMinimumHeight(40)
        self.btn_add_course.setCursor(Qt.PointingHandCursor)
        self.btn_add_course.setStyleSheet(get_button_style('primary'))
        self.btn_add_course.setToolTip("创建新的课程")
        self.btn_add_course.clicked.connect(self.add_course)
        btn_layout.addWidget(self.btn_add_course)

        self.btn_edit_course = QPushButton(f"{ICONS['edit']}  编辑课程")
        self.btn_edit_course.setMinimumHeight(40)
        self.btn_edit_course.setCursor(Qt.PointingHandCursor)
        self.btn_edit_course.setStyleSheet(get_button_style('secondary'))
        self.btn_edit_course.setToolTip("编辑选中课程的信息")
        self.btn_edit_course.clicked.connect(self.edit_course)
        btn_layout.addWidget(self.btn_edit_course)

        self.btn_delete_course = QPushButton(f"{ICONS['delete']}  删除选中课程")
        self.btn_delete_course.setMinimumHeight(40)
        self.btn_delete_course.setCursor(Qt.PointingHandCursor)
        self.btn_delete_course.setStyleSheet(get_button_style('danger'))
        self.btn_delete_course.setToolTip("删除选中的课程")
        self.btn_delete_course.clicked.connect(self.delete_course)
        btn_layout.addWidget(self.btn_delete_course)

        self.btn_refresh_courses = QPushButton(ICONS['refresh'])
        self.btn_refresh_courses.setMinimumHeight(40)
        self.btn_refresh_courses.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_courses.setStyleSheet(get_button_style('ghost'))
        self.btn_refresh_courses.setToolTip("刷新课程列表")
        self.btn_refresh_courses.clicked.connect(self.refresh_courses)
        btn_layout.addWidget(self.btn_refresh_courses)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 课程列表表格
        self.courses_table = QTableWidget()
        self.courses_table.setColumnCount(4)
        self.courses_table.setHorizontalHeaderLabels(["ID", "课程代码", "课程名称", "教师"])
        self.courses_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.courses_table.setAlternatingRowColors(True)
        self.courses_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.courses_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.courses_table.verticalHeader().setVisible(False)
        self.courses_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.courses_table.customContextMenuRequested.connect(self._on_course_context_menu)
        self.courses_table.doubleClicked.connect(self.edit_course)
        self.courses_table.setStyleSheet(f"""
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
                padding: 14px;
                border: none;
                border-bottom: 1px solid {COLORS['divider']};
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        self.courses_table.setItemDelegate(NoFocusDelegate())
        self.courses_table.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.courses_table)

        # 缓存课程列表用于搜索
        self._all_courses = []

        # 初始加载
        self.refresh_courses()

        return widget

    def create_records_tab(self) -> QWidget:
        """创建考勤记录标签页 - Apple风格优化版"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 筛选条件行
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(16)

        course_label = QLabel(f"{ICONS['courses']} 课程")
        course_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        filter_layout.addWidget(course_label)

        combo_css = f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['small']};
                padding: 10px 36px 10px 14px;
                font-size: 14px;
            }}
            QComboBox:hover {{ border-color: {COLORS['primary']}; }}
            QComboBox:focus  {{ border-color: {COLORS['primary']}; }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border: none;
                border-left: 1px solid {COLORS['divider']};
            }}
            QComboBox::down-arrow {{ width: 12px; height: 12px; }}
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
        """

        self.combo_filter_course = QComboBox()
        self.combo_filter_course.setMinimumWidth(160)
        self.combo_filter_course.setMinimumHeight(40)
        self.combo_filter_course.setStyleSheet(combo_css)
        filter_layout.addWidget(self.combo_filter_course)

        # 日期选择
        date_label = QLabel(f"{ICONS['attendance']} 日期")
        date_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        filter_layout.addWidget(date_label)

        self.date_filter = QDateEdit()
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setMinimumHeight(40)
        self.date_filter.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['small']};
                padding: 10px 36px 10px 14px;
                font-size: 14px;
                min-width: 120px;
            }}
            QDateEdit:hover {{ border-color: {COLORS['primary']}; }}
            QDateEdit:focus  {{ border-color: {COLORS['primary']}; }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border: none;
                border-left: 1px solid {COLORS['divider']};
            }}
            QDateEdit::down-arrow {{ width: 12px; height: 12px; }}
            QCalendarWidget {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['medium']};
            }}
            QCalendarWidget QToolButton {{
                color: {COLORS['text_primary']};
                border-radius: {RADIUS['small']};
                padding: 6px 12px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {COLORS['primary_light']};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['primary_light']};
                selection-color: {COLORS['primary']};
            }}
        """)
        filter_layout.addWidget(self.date_filter)

        # 状态筛选
        status_label = QLabel("状态")
        status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        filter_layout.addWidget(status_label)

        self.combo_filter_status = QComboBox()
        self.combo_filter_status.addItems(["全部状态", "正常", "迟到", "缺勤"])
        self.combo_filter_status.setMinimumWidth(100)
        self.combo_filter_status.setMinimumHeight(40)
        self.combo_filter_status.setStyleSheet(combo_css)
        filter_layout.addWidget(self.combo_filter_status)

        # 查询按钮
        self.btn_query_records = QPushButton(f"{ICONS['search']} 查询")
        self.btn_query_records.setMinimumHeight(40)
        self.btn_query_records.setCursor(Qt.PointingHandCursor)
        self.btn_query_records.setStyleSheet(get_button_style('primary'))
        self.btn_query_records.setToolTip("根据条件查询考勤记录")
        self.btn_query_records.clicked.connect(self.query_records)
        filter_layout.addWidget(self.btn_query_records)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 统计行
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(28)

        self.stats_total = self._create_stat_item("总计", "0", COLORS['text_primary'])
        stats_layout.addWidget(self.stats_total)

        self._add_stat_divider(stats_layout)
        self.stats_normal = self._create_stat_item("正常", "0", COLORS['success'])
        stats_layout.addWidget(self.stats_normal)

        self._add_stat_divider(stats_layout)
        self.stats_late = self._create_stat_item("迟到", "0", COLORS['warning'])
        stats_layout.addWidget(self.stats_late)

        self._add_stat_divider(stats_layout)
        self.stats_absent = self._create_stat_item("缺勤", "0", COLORS['danger'])
        stats_layout.addWidget(self.stats_absent)

        stats_layout.addStretch()
        layout.addLayout(stats_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.btn_edit_record = QPushButton(f"{ICONS['edit']}  修改状态")
        self.btn_edit_record.setMinimumHeight(40)
        self.btn_edit_record.setCursor(Qt.PointingHandCursor)
        self.btn_edit_record.setStyleSheet(get_button_style('secondary'))
        self.btn_edit_record.setToolTip("修改选中考勤记录的状态（正常/迟到/缺勤）")
        self.btn_edit_record.clicked.connect(self.edit_record_status)
        btn_layout.addWidget(self.btn_edit_record)

        self.btn_delete_record = QPushButton(f"{ICONS['delete']}  删除记录")
        self.btn_delete_record.setMinimumHeight(40)
        self.btn_delete_record.setCursor(Qt.PointingHandCursor)
        self.btn_delete_record.setStyleSheet(get_button_style('danger'))
        self.btn_delete_record.setToolTip("删除选中的考勤记录（Ctrl多选可批量删除）")
        self.btn_delete_record.clicked.connect(self.delete_records)
        btn_layout.addWidget(self.btn_delete_record)

        self.btn_refresh_records = QPushButton(ICONS['refresh'])
        self.btn_refresh_records.setMinimumHeight(40)
        self.btn_refresh_records.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_records.setStyleSheet(get_button_style('ghost'))
        self.btn_refresh_records.setToolTip("刷新考勤记录")
        self.btn_refresh_records.clicked.connect(self.query_records)
        btn_layout.addWidget(self.btn_refresh_records)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 记录表格（隐藏ID列）
        self.records_table = QTableWidget()
        self.records_table.setColumnCount(6)
        self.records_table.setHorizontalHeaderLabels(
            ["时间", "学号", "姓名", "课程", "状态", "置信度"]
        )
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.setAlternatingRowColors(True)
        self.records_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.records_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.records_table.verticalHeader().setVisible(False)
        self.records_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.records_table.customContextMenuRequested.connect(self._on_record_context_menu)
        self.records_table.setSortingEnabled(True)
        self.records_table.setStyleSheet(f"""
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
                padding: 14px;
                border: none;
                border-bottom: 1px solid {COLORS['divider']};
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
        """)
        self.records_table.setItemDelegate(NoFocusDelegate())
        self.records_table.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.records_table)

        # 初始加载
        self.refresh_courses_filter()
        # 初始化统计显示（确保状态栏默认显示）
        self._init_stats_display()
        self.query_records()

        return widget

    def _init_stats_display(self):
        """初始化统计显示（确保状态栏默认显示）"""
        self.stats_total.setText("📊 总计: 0")
        self.stats_normal.setText("✅ 正常: 0")
        self.stats_late.setText("⏰ 迟到: 0")
        self.stats_absent.setText("❌ 缺勤: 0")

    def _create_stat_item(self, label: str, value: str, color: str) -> QLabel:
        """创建统计项"""
        # 添加图标增强视觉效果
        icons = {
            "总计": "📊",
            "正常": "✅",
            "迟到": "⏰",
            "缺勤": "❌"
        }
        icon = icons.get(label, "")
        container = QLabel(f"{icon} {label}: {value}")
        container.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 15px;
                font-weight: 600;
                padding: 4px 8px;
            }}
        """)
        return container

    def _add_stat_divider(self, layout: QHBoxLayout):
        """添加统计分隔线"""
        divider = QLabel("|")
        divider.setStyleSheet(f"color: {COLORS['divider']}; font-size: 16px;")
        layout.addWidget(divider)

    def create_export_tab(self) -> QWidget:
        """创建数据导出标签页 - Apple风格优化版"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        combo_css = f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['small']};
                padding: 10px 36px 10px 14px;
                font-size: 14px;
            }}
            QComboBox:hover {{ border-color: {COLORS['primary']}; }}
            QComboBox:focus  {{ border-color: {COLORS['primary']}; }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border: none;
                border-left: 1px solid {COLORS['divider']};
            }}
            QComboBox::down-arrow {{ width: 12px; height: 12px; }}
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
        """

        # 表单区域
        form_layout = QVBoxLayout()
        form_layout.setSpacing(16)

        # 课程选择
        course_row = QHBoxLayout()
        course_row.setSpacing(12)
        course_label = QLabel("选择课程")
        course_label.setFixedWidth(80)
        course_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600;")
        course_row.addWidget(course_label)

        self.combo_export_course = QComboBox()
        self.combo_export_course.setMinimumHeight(40)
        self.combo_export_course.setStyleSheet(combo_css)
        self.combo_export_course.currentIndexChanged.connect(self._update_export_summary)
        course_row.addWidget(self.combo_export_course, 1)
        form_layout.addLayout(course_row)

        # 日期范围
        date_row = QHBoxLayout()
        date_row.setSpacing(12)
        date_label = QLabel("日期范围")
        date_label.setFixedWidth(80)
        date_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600;")
        date_row.addWidget(date_label)

        date_css = f"""
            QDateEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['small']};
                padding: 10px 36px 10px 14px;
                font-size: 14px;
                min-width: 120px;
            }}
            QDateEdit:hover {{ border-color: {COLORS['primary']}; }}
            QDateEdit:focus  {{ border-color: {COLORS['primary']}; }}
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border: none;
                border-left: 1px solid {COLORS['divider']};
            }}
            QDateEdit::down-arrow {{ width: 12px; height: 12px; }}
            QCalendarWidget {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['medium']};
            }}
            QCalendarWidget QToolButton {{
                color: {COLORS['text_primary']};
                border-radius: {RADIUS['small']};
                padding: 6px 12px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {COLORS['primary_light']};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {COLORS['text_primary']};
                selection-background-color: {COLORS['primary_light']};
                selection-color: {COLORS['primary']};
            }}
        """

        self.export_start_date = QDateEdit()
        self.export_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.export_start_date.setCalendarPopup(True)
        self.export_start_date.setMinimumHeight(40)
        self.export_start_date.setStyleSheet(date_css)
        self.export_start_date.dateChanged.connect(self._update_export_summary)
        date_row.addWidget(self.export_start_date)

        to_label = QLabel("  —  ")
        to_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 14px;")
        date_row.addWidget(to_label)

        self.export_end_date = QDateEdit()
        self.export_end_date.setDate(QDate.currentDate())
        self.export_end_date.setCalendarPopup(True)
        self.export_end_date.setMinimumHeight(40)
        self.export_end_date.setStyleSheet(date_css)
        self.export_end_date.dateChanged.connect(self._update_export_summary)
        date_row.addWidget(self.export_end_date)
        date_row.addStretch()
        form_layout.addLayout(date_row)

        layout.addLayout(form_layout)

        # 数据摘要
        self.export_summary_label = QLabel("将导出: 0 条考勤记录")
        self.export_summary_label.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_secondary']};
                font-size: 14px;
                font-weight: 500;
                padding: 4px 0;
            }}
        """)
        layout.addWidget(self.export_summary_label)

        # 导出按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(16)

        self.btn_export_excel = QPushButton(f"{ICONS['export']}  导出考勤记录")
        self.btn_export_excel.setMinimumHeight(50)
        self.btn_export_excel.setCursor(Qt.PointingHandCursor)
        self.btn_export_excel.setStyleSheet(get_button_style('primary'))
        self.btn_export_excel.setToolTip("按条件导出考勤记录到Excel文件")
        self.btn_export_excel.clicked.connect(self.export_to_excel)
        btn_layout.addWidget(self.btn_export_excel, 1)

        self.btn_export_students = QPushButton(f"{ICONS['students']}  导出学生名单")
        self.btn_export_students.setMinimumHeight(50)
        self.btn_export_students.setCursor(Qt.PointingHandCursor)
        self.btn_export_students.setStyleSheet(get_button_style('secondary'))
        self.btn_export_students.setToolTip("导出全部学生名单到Excel文件")
        self.btn_export_students.clicked.connect(self.export_students_list)
        btn_layout.addWidget(self.btn_export_students, 1)

        layout.addLayout(btn_layout)
        layout.addStretch()

        # 初始加载课程列表
        self.refresh_export_courses()
        # 延迟更新摘要（等待课程列表加载）
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._update_export_summary)

        return widget

    def _update_export_summary(self):
        """更新导出摘要"""
        try:
            course_id = self.combo_export_course.currentData()
            start_date = self.export_start_date.date().toPyDate()
            end_date = self.export_end_date.date().toPyDate()

            # 获取记录数量
            records = self.attendance_service.export_records(course_id, start_date, end_date)
            count = len(records)

            # 获取学生数量（去重）
            student_ids = set()
            for r in records:
                if r.get('学号'):
                    student_ids.add(r['学号'])
            student_count = len(student_ids)

            course_name = "全部课程"
            if course_id:
                course_data = self.course_service.get_course(course_id)
                if course_data:
                    course_name = course_data.get('course_name', '')

            # 格式化日期范围显示
            if start_date == end_date:
                date_range = start_date.strftime('%Y-%m-%d')
            else:
                date_range = f"{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"

            self.export_summary_label.setText(
                f"导出范围: {course_name} | 日期: {date_range} | "
                f"共 {count} 条记录, {student_count} 名学生"
            )
        except Exception:
            pass

    def switch_tab(self, index: int):
        """切换标签页"""
        self.tab_widget.setCurrentIndex(index)
        # 切换到导出标签页时，同步查询条件并刷新摘要信息
        if index == 3:  # 数据导出标签页
            self._sync_query_to_export()
            self._update_export_summary()

    def _sync_query_to_export(self):
        """将考勤记录查询条件同步到导出界面"""
        try:
            # 同步课程选择
            query_course_id = self.combo_filter_course.currentData()
            if query_course_id is not None:
                # 在导出课程下拉框中找到对应的课程
                for i in range(self.combo_export_course.count()):
                    if self.combo_export_course.itemData(i) == query_course_id:
                        self.combo_export_course.setCurrentIndex(i)
                        break
            else:
                # 如果查询选择的是"全部课程"，导出也选择"全部课程"
                self.combo_export_course.setCurrentIndex(0)

            # 同步日期选择（将单日期同步到日期范围）
            query_date = self.date_filter.date()
            self.export_start_date.setDate(query_date)
            self.export_end_date.setDate(query_date)
        except Exception:
            pass

    # ==================== 学生管理方法 ====================

    def add_student(self):
        """添加学生"""
        dialog = RegisterDialog(self.ctx, self)
        if dialog.exec_():
            self.refresh_students()
            self.students_table.clearFocus()
            # 刷新考勤服务的人脸数据库
            self.attendance_service.refresh_face_database()

    def import_students(self):
        """批量导入学生 - 自动从目录名提取班级，后台线程不阻塞UI"""
        dir_path = QFileDialog.getExistingDirectory(self, "选择学生图片目录")
        if not dir_path:
            return

        # 尝试从目录名提取班级名（如选 23人工智能1班/train → 向上找到 23人工智能1班）
        import re
        class_name = None
        class_root = dir_path
        for path in [dir_path, os.path.dirname(dir_path)]:
            m = re.search(r'(\d+.*班)', os.path.basename(path))
            if m:
                class_name = m.group(1)
                class_root = path  # 用班级根目录而非子目录
                break
        if not class_name:
            class_name, ok = QInputDialog.getText(
                self, "班级名称", "请输入班级名称（如 23人工智能1班）：")
            if not ok or not class_name.strip():
                return
            class_name = class_name.strip()

        logger.info(f"[GUI导入] dir_path={class_root}, class_name={class_name}")

        import_service = self.ctx.student_service

        # 创建进度对话框
        self._import_progress = QProgressDialog("正在初始化...", "取消", 0, 100, self)
        self._import_progress.setWindowTitle("批量导入")
        self._import_progress.setWindowModality(Qt.WindowModal)
        self._import_progress.setMinimumDuration(0)
        self._import_progress.setAutoClose(False)
        self._import_progress.setAutoReset(False)

        # 创建后台线程（传班级根目录，不是子目录）
        self._import_worker = ImportWorker(import_service, class_root, class_name=class_name)
        self._import_worker.progress_signal.connect(self._on_import_progress)
        self._import_worker.finished_signal.connect(self._on_import_finished)
        self._import_progress.canceled.connect(self._import_worker.cancel)
        self._import_worker.start()

    def _on_import_progress(self, current, total, status):
        """导入进度更新"""
        if hasattr(self, '_import_progress') and self._import_progress:
            self._import_progress.setLabelText(status)
            self._import_progress.setMaximum(total)
            self._import_progress.setValue(current)

    def _on_import_finished(self, success_count, errors, log_path):
        """导入完成回调"""
        if hasattr(self, '_import_progress') and self._import_progress:
            self._import_progress.close()
            self._import_progress = None
        self._import_worker = None

        msg = f"成功导入 {success_count} 名学生"
        if errors:
            msg += f"\n\n详情:\n" + "\n".join(errors[:8])
            if len(errors) > 8:
                msg += f"\n... 还有 {len(errors) - 8} 条"
            if log_path:
                msg += f"\n\n完整错误日志:\n{log_path}"
            show_warning(self, "导入完成", msg)
        else:
            show_toast(self, msg, "success", 4000)
        self.refresh_students()
        self.attendance_service.refresh_face_database()

    def delete_student(self):
        """删除选中学生（选一个删一个，选多个批量删）"""
        rows = sorted(set(item.row() for item in self.students_table.selectedItems()))
        if not rows:
            QMessageBox.warning(self, "提示", "请先选中要删除的学生（Ctrl/Shift多选）")
            return

        if len(rows) == 1:
            sid = self.students_table.item(rows[0], 0).text()
            name = self.students_table.item(rows[0], 1).text()
            msg = f"确定要删除学生 {name} ({sid}) 吗？"
        else:
            msg = f"确定要删除选中的 {len(rows)} 名学生吗？\n此操作不可撤销！"

        if not show_confirm(self, "确认删除", msg):
            return

        deleted = 0
        for row in reversed(rows):
            sid = self.students_table.item(row, 0).text()
            success, _ = self.student_service.delete_student(sid)
            if success:
                deleted += 1

        self.refresh_students()
        if deleted:
            self.attendance_service.refresh_face_database()
        show_toast(self, f"已删除 {deleted} 人", "success")

    def refresh_students(self):
        """刷新学生列表"""
        self._all_students = self.student_service.get_all_students()
        self._display_students(self._all_students)

    def _display_students(self, students):
        """显示学生列表"""
        self.students_table.setRowCount(len(students))

        for row, student in enumerate(students):
            self.students_table.setItem(row, 0, QTableWidgetItem(student.get('student_id', '')))
            self.students_table.setItem(row, 1, QTableWidgetItem(student.get('name', '')))
            self.students_table.setItem(row, 2, QTableWidgetItem(student.get('class_name', '') or ''))

            created_at = student.get('created_at')
            time_str = created_at.strftime('%Y-%m-%d') if created_at else ''
            self.students_table.setItem(row, 3, QTableWidgetItem(time_str))

    def search_students(self):
        """搜索学生"""
        keyword = self.edit_search_student.text().strip().lower()
        if not keyword:
            self._display_students(self._all_students)
            return

        filtered = [s for s in self._all_students if
                    keyword in (s.get('student_id', '') or '').lower() or
                    keyword in (s.get('name', '') or '').lower() or
                    keyword in (s.get('class_name', '') or '').lower()]
        self._display_students(filtered)

    def edit_student(self):
        """编辑学生"""
        selected = self.students_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要编辑的学生")
            return

        row = selected[0].row()
        student_id = self.students_table.item(row, 0).text()

        # 获取学生完整信息
        student_data = self.student_service.get_student(student_id)
        if not student_data:
            QMessageBox.warning(self, "错误", "学生不存在")
            return

        dialog = EditStudentDialog(self.ctx, student_data, self)
        if dialog.exec_():
            self.refresh_students()
            self.students_table.clearFocus()
            self.attendance_service.refresh_face_database()

    # ==================== 课程管理方法 ====================

    def add_course(self):
        """添加课程 - 使用对话框方式"""
        dialog = EditCourseDialog(self.ctx, None, self)  # None 表示新建模式
        if dialog.exec_():
            self.refresh_courses()
            self.courses_table.clearFocus()
            self.refresh_courses_filter()
            self.refresh_export_courses()

    def delete_course(self):
        """删除选中课程（选一个删一个，选多个批量删）"""
        rows = sorted(set(item.row() for item in self.courses_table.selectedItems()))
        if not rows:
            QMessageBox.warning(self, "提示", "请先选中要删除的课程（Ctrl/Shift多选）")
            return

        if len(rows) == 1:
            cname = self.courses_table.item(rows[0], 2).text()
            msg = f"确定要删除课程 {cname} 吗？相关考勤记录将保留。"
        else:
            msg = f"确定要删除选中的 {len(rows)} 门课程吗？\n相关考勤记录将保留。此操作不可撤销！"

        if not show_confirm(self, "确认删除", msg):
            return

        deleted = 0
        for row in reversed(rows):
            course_id = self.courses_table.item(row, 0).data(Qt.UserRole)
            if course_id and self.course_service.delete_course(course_id):
                deleted += 1

        self.refresh_courses()
        self.refresh_courses_filter()
        show_toast(self, f"已删除 {deleted} 门课程", "success")
        self.refresh_export_courses()

    def refresh_courses(self):
        """刷新课程列表"""
        self._all_courses = self.course_service.get_all_courses()
        self._display_courses(self._all_courses)

    def _display_courses(self, courses):
        """显示课程列表"""
        self.courses_table.setRowCount(len(courses))

        for row, course in enumerate(courses):
            id_item = QTableWidgetItem(str(row + 1))
            id_item.setData(Qt.UserRole, course.get('id'))  # 存DB ID用于删除
            self.courses_table.setItem(row, 0, id_item)
            self.courses_table.setItem(row, 1, QTableWidgetItem(course.get('course_code', '')))
            self.courses_table.setItem(row, 2, QTableWidgetItem(course.get('course_name', '')))
            self.courses_table.setItem(row, 3, QTableWidgetItem(course.get('teacher_name', '') or ''))

    def search_courses(self):
        """搜索课程"""
        keyword = self.edit_search_course.text().strip().lower()
        if not keyword:
            self._display_courses(self._all_courses)
            return

        filtered = [c for c in self._all_courses if
                    keyword in (c.get('course_code', '') or '').lower() or
                    keyword in (c.get('course_name', '') or '').lower()]
        self._display_courses(filtered)

    def edit_course(self):
        """编辑课程"""
        selected = self.courses_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要编辑的课程")
            return

        row = selected[0].row()
        course_id = self.courses_table.item(row, 0).data(Qt.UserRole)

        # 获取课程完整信息
        course_data = self.course_service.get_course(course_id) if course_id else None
        if not course_data:
            QMessageBox.warning(self, "错误", "课程不存在")
            return

        dialog = EditCourseDialog(self.ctx, course_data, self)
        if dialog.exec_():
            self.refresh_courses()
            self.courses_table.clearFocus()
            self.refresh_courses_filter()
            self.refresh_export_courses()

    def refresh_courses_filter(self):
        """刷新记录查询的课程筛选"""
        self.combo_filter_course.clear()
        self.combo_filter_course.addItem("全部课程", None)
        for course in self.course_service.get_all_courses():
            self.combo_filter_course.addItem(
                course['course_name'],
                course['id']
            )

    def refresh_export_courses(self):
        """刷新导出页的课程列表"""
        self.combo_export_course.clear()
        self.combo_export_course.addItem("全部课程", None)
        for course in self.course_service.get_all_courses():
            self.combo_export_course.addItem(
                f"{course['course_name']} ({course['course_code']})",
                course['id']
            )

    # ==================== 考勤记录方法 ====================

    def query_records(self):
        """查询考勤记录"""
        try:
            course_id = self.combo_filter_course.currentData()
            query_date = self.date_filter.date().toPyDate()
            status_filter = self.combo_filter_status.currentText()

            records = self.attendance_service.get_attendance_records(
                course_id=course_id,
                date=query_date
            )

            # 确保records不为None
            if records is None:
                records = []

            # 状态筛选
            if status_filter != "全部状态":
                status_map = {"正常": "normal", "迟到": "late", "缺勤": "absent"}
                target_status = status_map.get(status_filter, None)
                if target_status:
                    records = [r for r in records if r.get('status') == target_status]

            # 统计计数
            total = len(records)
            normal_count = sum(1 for r in records if r.get('status') == 'normal')
            late_count = sum(1 for r in records if r.get('status') == 'late')
            absent_count = sum(1 for r in records if r.get('status') == 'absent')

            # 更新统计卡片（确保状态栏显示）
            self.stats_total.setText(f"总计: {total}")
            self.stats_normal.setText(f"正常: {normal_count}")
            self.stats_late.setText(f"迟到: {late_count}")
            self.stats_absent.setText(f"缺勤: {absent_count}")

            # 更新表格（无ID列，但将ID存储在时间单元格的userData中）
            self.records_table.setRowCount(len(records))
            for row, record in enumerate(records):
                record_id = record.get('id', '')
                time_str = record['check_time'].strftime('%H:%M:%S') if record['check_time'] else ''
                time_item = QTableWidgetItem(time_str)
                time_item.setData(Qt.UserRole, record_id)  # 存储ID
                self.records_table.setItem(row, 0, time_item)
                self.records_table.setItem(row, 1, QTableWidgetItem(str(record.get('student_no', ''))))
                self.records_table.setItem(row, 2, QTableWidgetItem(str(record.get('student_name', ''))))
                self.records_table.setItem(row, 3, QTableWidgetItem(str(record.get('course_name', '') or '')))

                status = record.get('status', 'normal')
                status_text = '正常' if status == 'normal' else ('迟到' if status == 'late' else '缺勤')
                status_item = QTableWidgetItem(status_text)
                status_item.setTextAlignment(Qt.AlignCenter)

                if status == 'normal':
                    status_item.setForeground(QColor(COLORS['success']))
                elif status == 'late':
                    status_item.setForeground(QColor(COLORS['warning']))
                else:
                    status_item.setForeground(QColor(COLORS['danger']))
                self.records_table.setItem(row, 4, status_item)

                confidence = record.get('confidence')
                confidence_text = f'{confidence:.0%}' if confidence else ''
                self.records_table.setItem(row, 5, QTableWidgetItem(confidence_text))
        except Exception as e:
            # 发生异常时确保状态栏仍显示默认值
            self.stats_total.setText("📊 总计: 0")
            self.stats_normal.setText("✅ 正常: 0")
            self.stats_late.setText("⏰ 迟到: 0")
            self.stats_absent.setText("❌ 缺勤: 0")
            self.records_table.setRowCount(0)

    def edit_record_status(self):
        """修改考勤记录状态"""
        selected = self.records_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选择要修改的记录")
            return
        row = selected[0].row()

        # 从时间单元格获取存储的record_id
        time_item = self.records_table.item(row, 0)
        record_id = time_item.data(Qt.UserRole) if time_item else None

        if record_id is None:
            QMessageBox.warning(self, "错误", "无法获取记录ID")
            return

        current_status = self.records_table.item(row, 4).text()

        # 弹出选择框
        status_options = ['normal', 'late', 'absent']
        status_names = ['正常', '迟到', '缺勤']
        current_idx = status_names.index(current_status) if current_status in status_names else 0

        choice, ok = QInputDialog.getItem(
            self, "修改状态",
            "选择新状态:", status_names, current_idx, False
        )

        if ok and choice:
            new_status = status_options[status_names.index(choice)]
            if self.attendance_service.update_attendance_record(record_id, status=new_status):
                show_toast(self, "状态已更新", "success")
                self.query_records()
            else:
                show_toast(self, "更新失败", "error")

    def delete_records(self):
        """删除选中的考勤记录（选一行删一行，选多行批量删）"""
        rows = sorted(set(item.row() for item in self.records_table.selectedItems()))
        if not rows:
            QMessageBox.warning(self, "提示", "请先选中要删除的记录（Ctrl/Shift多选）")
            return

        if len(rows) == 1:
            name = self.records_table.item(rows[0], 2).text()
            msg = f"确定要删除 {name} 的考勤记录吗？"
        else:
            msg = f"确定要删除选中的 {len(rows)} 条考勤记录吗？\n此操作不可撤销！"

        if not show_confirm(self, "确认删除", msg):
            return

        deleted = 0
        for row in reversed(rows):
            time_item = self.records_table.item(row, 0)
            record_id = time_item.data(Qt.UserRole) if time_item else None
            if record_id and self.attendance_service.delete_attendance_record(record_id):
                deleted += 1

        show_toast(self, f"已删除 {deleted} 条记录", "success")
        self.query_records()

    # ==================== 右键菜单方法 ====================

    def _on_student_context_menu(self, pos):
        """学生表格右键菜单"""
        from PyQt5.QtWidgets import QMenu, QAction
        item = self.students_table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        self.students_table.selectRow(row)
        menu = QMenu(self)
        menu.addAction(f"{ICONS['edit']} 编辑学生", self.edit_student)
        menu.addAction(f"{ICONS['delete']} 删除学生", self.delete_student)
        menu.exec_(self.students_table.viewport().mapToGlobal(pos))

    def _on_course_context_menu(self, pos):
        """课程表格右键菜单"""
        from PyQt5.QtWidgets import QMenu, QAction
        item = self.courses_table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        self.courses_table.selectRow(row)
        menu = QMenu(self)
        menu.addAction(f"{ICONS['edit']} 编辑课程", self.edit_course)
        menu.addAction(f"{ICONS['delete']} 删除课程", self.delete_course)
        menu.exec_(self.courses_table.viewport().mapToGlobal(pos))

    def _on_record_context_menu(self, pos):
        """考勤记录表格右键菜单"""
        from PyQt5.QtWidgets import QMenu, QAction
        item = self.records_table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        self.records_table.selectRow(row)
        menu = QMenu(self)
        menu.addAction(f"{ICONS['edit']} 修改状态", self.edit_record_status)
        menu.addAction(f"{ICONS['delete']} 删除记录", self.delete_records)
        menu.exec_(self.records_table.viewport().mapToGlobal(pos))

    # ==================== 导出方法 ====================

    def export_to_excel(self):
        """导出考勤记录到Excel"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存Excel文件",
            f"考勤记录_{datetime.now().strftime('%Y%m%d')}.xlsx",
            "Excel文件 (*.xlsx)"
        )

        if not file_path:
            return

        course_id = self.combo_export_course.currentData()
        start_date = self.export_start_date.date().toPyDate()
        end_date = self.export_end_date.date().toPyDate()

        records = self.attendance_service.export_records(course_id, start_date, end_date)

        if not records:
            show_toast(self, "没有可导出的记录", "warning", 3000)
            return

        if ExcelExporter.export_attendance_records(records, file_path):
            show_toast(self, f"成功导出 {len(records)} 条记录", "success", 4000)
        else:
            show_toast(self, "导出失败，请重试", "error", 4000)

    def export_students_list(self):
        """导出学生名单"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存Excel文件",
            f"学生名单_{datetime.now().strftime('%Y%m%d')}.xlsx",
            "Excel文件 (*.xlsx)"
        )

        if not file_path:
            return

        students = self.student_service.get_all_students()

        if not students:
            show_toast(self, "没有学生数据可导出", "warning", 3000)
            return

        if ExcelExporter.export_student_list(students, file_path):
            show_toast(self, f"成功导出 {len(students)} 名学生", "success", 4000)
        else:
            show_toast(self, "导出失败，请重试", "error", 4000)