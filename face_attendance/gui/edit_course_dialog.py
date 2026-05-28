"""
课程编辑对话框
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTimeEdit, QFrame,
    QSizePolicy, QWidget
)
from PyQt5.QtCore import Qt, QTime

from .apple_style import (
    COLORS, RADIUS, get_button_style, ICONS
)
from .widgets import show_toast


class EditCourseDialog(QDialog):
    """课程编辑/新建对话框"""

    def __init__(self, ctx, course_data: dict = None, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.is_new_mode = course_data is None

        if self.is_new_mode:
            self.course_data = {
                'course_code': '', 'course_name': '',
                'teacher_name': '', 'start_time': '08:00', 'end_time': '09:40'
            }
        else:
            self.course_data = course_data

        self.init_ui()

    def init_ui(self):
        title_text = "新建课程" if self.is_new_mode else f"编辑课程 - {self.course_data.get('course_name', '')}"
        self.setWindowTitle(title_text)
        self.setFixedSize(620, 620)
        self.setStyleSheet(f"background-color: {COLORS['background']};")

        root = QVBoxLayout(self)
        root.setSpacing(20)
        root.setContentsMargins(32, 32, 32, 32)

        # ── 主卡片 ──
        card = QFrame()
        card.setObjectName("infoCard")
        card.setStyleSheet(f"""
            QFrame#infoCard {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['divider']};
                border-radius: {RADIUS['large']};
            }}
        """)
        body = QVBoxLayout(card)
        body.setContentsMargins(32, 28, 32, 28)
        body.setSpacing(20)

        # 标题
        hdr = QHBoxLayout()
        icon = QLabel(ICONS['courses'])
        icon.setStyleSheet("font-size: 22px; background: transparent;")
        hdr.addWidget(icon)
        title = QLabel(title_text)
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 20px; font-weight: 700; background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        body.addLayout(hdr)

        sep = QFrame(); sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS['divider']};")
        body.addWidget(sep)

        # ── 字段（不在额外嵌套卡片内，直接用 label + input）──

        self.edit_code = QLineEdit()
        self.edit_code.setPlaceholderText("如: CS101")
        self.edit_code.setText(self.course_data.get('course_code', ''))
        body.addLayout(self._labeled_input("课程代码 *", self.edit_code))

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("如: 计算机视觉")
        self.edit_name.setText(self.course_data.get('course_name', ''))
        body.addLayout(self._labeled_input("课程名称 *", self.edit_name))

        self.edit_teacher = QLineEdit()
        self.edit_teacher.setPlaceholderText("如: 张教授")
        self.edit_teacher.setText(self.course_data.get('teacher_name', '') or '')
        body.addLayout(self._labeled_input("授课教师", self.edit_teacher))

        # ── 上课时间 ──
        body.addLayout(self._time_row("上课时间"))

        body.addStretch()
        root.addWidget(card, 1)

        # ── 按钮 ──
        btns = QHBoxLayout()
        btns.setSpacing(16)
        btn_cancel = QPushButton("取 消")
        btn_cancel.setMinimumHeight(54)
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(get_button_style('secondary'))
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel, 1)
        btn_save = QPushButton("保 存")
        btn_save.setMinimumHeight(54)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(get_button_style('primary'))
        btn_save.clicked.connect(self.save_course)
        btns.addWidget(btn_save, 1)
        root.addLayout(btns)

    # ────────────── helpers ──────────────

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

    def _make_time_picker(self, default_hour: int, default_min: int):
        """创建 QTimeEdit（隐藏原生按钮）+ ▲▼ 按钮 的紧凑组件"""
        container = QWidget()
        row = QHBoxLayout(container)
        row.setSpacing(4)
        row.setContentsMargins(0, 0, 0, 0)

        editor = QTimeEdit()
        editor.setDisplayFormat("HH:mm")
        editor.setButtonSymbols(QTimeEdit.NoButtons)
        editor.setMinimumHeight(46)
        editor.setStyleSheet(f"""
            QTimeEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 2px solid {COLORS['divider']};
                border-radius: {RADIUS['medium']};
                padding: 0 14px;
                font-size: 16px;
                font-weight: 600;
                letter-spacing: 2px;
            }}
            QTimeEdit:hover {{ border-color: {COLORS['text_placeholder']}; }}
            QTimeEdit:focus {{
                border-color: {COLORS['primary']};
                background-color: {COLORS['surface']};
            }}
        """)
        editor.setTime(QTime(default_hour, default_min))
        row.addWidget(editor, 1)

        # ▲ ▼ 按钮
        btn_css = f"""
            QPushButton {{
                background-color: {COLORS['table_header']};
                color: {COLORS['text_secondary']};
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                min-width: 26px;
                min-height: 20px;
                max-height: 20px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_light']};
                color: {COLORS['primary']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['primary']};
                color: #FFFFFF;
            }}
        """
        btn_col = QVBoxLayout()
        btn_col.setSpacing(2)
        btn_col.setContentsMargins(0, 0, 0, 0)

        btn_up = QPushButton("▲")
        btn_up.setStyleSheet(btn_css)
        btn_up.setCursor(Qt.PointingHandCursor)
        btn_up.clicked.connect(lambda: editor.stepUp())
        btn_col.addWidget(btn_up)

        btn_down = QPushButton("▼")
        btn_down.setStyleSheet(btn_css)
        btn_down.setCursor(Qt.PointingHandCursor)
        btn_down.clicked.connect(lambda: editor.stepDown())
        btn_col.addWidget(btn_down)

        row.addLayout(btn_col)
        return container, editor

    def _time_row(self, label: str) -> QVBoxLayout:
        """标签 + 两个时间选择器"""
        lay = QVBoxLayout()
        lay.setSpacing(8)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px; font-weight: 600; background: transparent;")
        lay.addWidget(lbl)

        row = QHBoxLayout()
        row.setSpacing(14)

        start_h, start_m = 8, 0
        end_h, end_m = 9, 40
        if self.course_data.get('start_time'):
            try:
                start_h, start_m = map(int, self.course_data['start_time'].split(':'))
            except Exception:
                pass
        if self.course_data.get('end_time'):
            try:
                end_h, end_m = map(int, self.course_data['end_time'].split(':'))
            except Exception:
                pass

        self._start_container, self.edit_start_time = self._make_time_picker(start_h, start_m)
        row.addWidget(self._start_container, 1)

        dash = QLabel("—")
        dash.setStyleSheet(f"color: {COLORS['text_placeholder']}; font-size: 16px; background-color: {COLORS['surface']};")
        dash.setFixedWidth(20)
        dash.setAlignment(Qt.AlignCenter)
        row.addWidget(dash)

        self._end_container, self.edit_end_time = self._make_time_picker(end_h, end_m)
        row.addWidget(self._end_container, 1)

        lay.addLayout(row)
        return lay

    # ────────────── 保存 ──────────────

    def save_course(self):
        code = self.edit_code.text().strip()
        name = self.edit_name.text().strip()
        teacher = self.edit_teacher.text().strip()
        start_time = self.edit_start_time.time().toString("HH:mm")
        end_time = self.edit_end_time.time().toString("HH:mm")

        if not code:
            show_toast(self, "请输入课程代码", "warning", 2500)
            self.edit_code.setFocus()
            return
        if not name:
            show_toast(self, "请输入课程名称", "warning", 2500)
            self.edit_name.setFocus()
            return
        if self.edit_start_time.time() >= self.edit_end_time.time():
            show_toast(self, "结束时间必须晚于开始时间", "warning", 2500)
            self.edit_end_time.setFocus()
            return

        try:
            if self.is_new_mode:
                self.ctx.course_service.add_course(code, name, teacher, start_time, end_time)
                show_toast(self, "课程创建成功", "success", 2500)
            else:
                self.ctx.course_service.update_course(
                    self.course_data['id'],
                    course_code=code, course_name=name,
                    teacher_name=teacher,
                    start_time=start_time, end_time=end_time
                )
                show_toast(self, "课程信息已更新", "success", 2500)
            self.accept()
        except Exception as e:
            show_toast(self, f"保存失败: {str(e)}", "error", 3000)
