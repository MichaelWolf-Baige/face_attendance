"""
手动补签对话框
教师从名单中直接选择未打卡学生，批量标记出勤
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QComboBox, QLineEdit, QHeaderView, QMessageBox,
    QFrame, QCheckBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from .apple_style import (
    COLORS, RADIUS, get_button_style, ICONS
)


class MakeupCheckInDialog(QDialog):
    """手动补签对话框"""

    def __init__(self, ctx, course_id=None, class_name=None, parent=None):
        super().__init__(parent)

        self.ctx = ctx
        self.course_id = course_id
        self.class_name = class_name
        self.checkboxes = {}  # row -> QCheckBox
        self.student_list = []     # current visible student list (filtered)
        self._full_student_list = []  # unfiltered list for current class

        self.init_ui()
        self.load_students()

    def init_ui(self):
        self.setWindowTitle("手动补签")
        self.setMinimumSize(650, 600)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 标题
        title = QLabel("手动补签 — 选择未打卡学生")
        title.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_primary']};
                font-size: 18px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(title)

        # 说明文字
        hint = QLabel("以下为今日尚未通过人脸识别打卡的学生，勾选后可直接标记出勤。")
        hint.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        # 工具栏：班级筛选 + 全选
        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)

        toolbar.addWidget(QLabel("班级筛选:"))
        self.combo_class = QComboBox()
        self.combo_class.setMinimumWidth(160)
        self.combo_class.setStyleSheet(self._combo_style())
        self.combo_class.currentIndexChanged.connect(self._on_class_changed)
        toolbar.addWidget(self.combo_class)

        toolbar.addSpacing(12)
        toolbar.addWidget(QLabel("搜索:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入学号或姓名过滤...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['small']};
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {COLORS['primary']}; }}
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        toolbar.addWidget(self.search_input)

        toolbar.addStretch()

        self.btn_select_all = QPushButton("全选")
        self.btn_select_all.setCursor(Qt.PointingHandCursor)
        self.btn_select_all.setStyleSheet(get_button_style('secondary'))
        self.btn_select_all.clicked.connect(self._select_all)
        toolbar.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("取消全选")
        self.btn_deselect_all.setCursor(Qt.PointingHandCursor)
        self.btn_deselect_all.setStyleSheet(get_button_style('secondary'))
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        toolbar.addWidget(self.btn_deselect_all)

        layout.addLayout(toolbar)

        # 学生表格
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["", "学生信息"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 40)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface']};
                alternate-background-color: {COLORS['table_alternate']};
                border: 1px solid {COLORS['divider']};
                border-radius: {RADIUS['medium']};
                gridline-color: {COLORS['divider']};
                font-size: 14px;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border-bottom: 1px solid {COLORS['divider']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['table_header']};
                color: {COLORS['text_secondary']};
                font-weight: 600;
                padding: 10px 12px;
                border: none;
                border-bottom: 1px solid {COLORS['divider']};
                font-size: 12px;
            }}
        """)
        layout.addWidget(self.table)

        # 状态选择
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['divider']};
                border-radius: {RADIUS['medium']};
            }}
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(16, 12, 16, 12)
        status_layout.setSpacing(16)

        status_layout.addWidget(QLabel("补签状态:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(["正常", "迟到"])
        self.combo_status.setMinimumWidth(120)
        self.combo_status.setStyleSheet(self._combo_style())
        status_layout.addWidget(self.combo_status)

        status_layout.addSpacing(24)
        status_layout.addWidget(QLabel("备注:"))
        self.remark_input = QLineEdit()
        self.remark_input.setPlaceholderText("可选，如\"戴口罩未识别\"")
        self.remark_input.setMinimumWidth(200)
        self.remark_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['background']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['small']};
                padding: 8px 12px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['primary']};
            }}
        """)
        status_layout.addWidget(self.remark_input)
        status_layout.addStretch()

        layout.addWidget(status_frame)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setMinimumSize(100, 40)
        self.btn_cancel.setCursor(Qt.PointingHandCursor)
        self.btn_cancel.setStyleSheet(get_button_style('secondary'))
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton("确认补签")
        self.btn_confirm.setMinimumSize(140, 40)
        self.btn_confirm.setCursor(Qt.PointingHandCursor)
        self.btn_confirm.setStyleSheet(get_button_style('primary'))
        self.btn_confirm.clicked.connect(self._do_makeup)
        btn_layout.addWidget(self.btn_confirm)

        layout.addLayout(btn_layout)

    def _combo_style(self):
        return f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['small']};
                padding: 8px 32px 8px 12px;
                font-size: 14px;
            }}
            QComboBox:hover {{ border-color: {COLORS['primary']}; }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
                border-left: 1px solid {COLORS['divider']};
            }}
        """

    def load_students(self):
        """加载班级列表和未打卡学生"""
        students = self.ctx.student_service.get_all_students()
        classes = sorted(set(
            s.get('class_name') for s in students
            if s.get('class_name')
        ))

        self.combo_class.blockSignals(True)
        self.combo_class.clear()
        self.combo_class.addItem("全部班级", None)
        for cls in classes:
            self.combo_class.addItem(cls, cls)
        if self.class_name:
            idx = self.combo_class.findData(self.class_name)
            if idx >= 0:
                self.combo_class.setCurrentIndex(idx)
        self.combo_class.blockSignals(False)

        self._refresh_table()

    def _on_class_changed(self):
        self.search_input.clear()
        self._refresh_table()

    def _on_search_changed(self, text):
        self._refresh_table()

    def _get_unchecked(self):
        class_name = self.combo_class.currentData()
        return self.ctx.attendance_service.get_unchecked_students(
            course_id=self.course_id,
            class_name=class_name
        )

    def _filter_students(self, students, search_text):
        if not search_text:
            return students
        text = search_text.strip().lower()
        return [
            s for s in students
            if text in s.get('student_id', '').lower()
            or text in s.get('name', '').lower()
            or text in s.get('class_name', '').lower()
        ]

    def _refresh_table(self):
        self.checkboxes.clear()
        self._full_student_list = self._get_unchecked()
        search_text = self.search_input.text().strip() if hasattr(self, 'search_input') else ''
        self.student_list = self._filter_students(self._full_student_list, search_text)

        self.table.setRowCount(len(self.student_list))
        for row, student in enumerate(self.student_list):
            cb = QCheckBox()
            cb.setChecked(False)
            self.checkboxes[row] = cb

            container = QFrame()
            container_layout = QHBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            container_layout.addWidget(cb)
            container_layout.addStretch()
            self.table.setCellWidget(row, 0, container)

            info = f"{student['student_id']}  {student['name']}"
            if student.get('class_name'):
                info += f"    [{student['class_name']}]"
            item = QTableWidgetItem(info)
            self.table.setItem(row, 1, item)

        self._update_count()

    def _select_all(self):
        for row in range(self.table.rowCount()):
            if row in self.checkboxes:
                self.checkboxes[row].setChecked(True)
        self._update_count()

    def _deselect_all(self):
        for row in range(self.table.rowCount()):
            if row in self.checkboxes:
                self.checkboxes[row].setChecked(False)
        self._update_count()

    def _update_count(self):
        checked = sum(1 for cb in self.checkboxes.values() if cb.isChecked())
        total = len(self.student_list)
        self.btn_confirm.setText(f"确认补签 ({checked}/{total})")

    def _do_makeup(self):
        selected = []
        for row, cb in self.checkboxes.items():
            if cb.isChecked() and row < len(self.student_list):
                selected.append(self.student_list[row])

        if not selected:
            QMessageBox.warning(self, "提示", "请至少选择一名学生")
            return

        status = 'normal' if self.combo_status.currentText() == '正常' else 'late'
        remark = self.remark_input.text().strip() or None

        reply = QMessageBox.question(
            self, "确认补签",
            f"将为 {len(selected)} 名学生补签为「{self.combo_status.currentText()}」，确认？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        success_count = 0
        fail_msgs = []
        for student in selected:
            ok, msg = self.ctx.attendance_service.manual_makeup_check_in(
                student['student_id'],
                course_id=self.course_id,
                status=status,
                remark=remark
            )
            if ok:
                success_count += 1
            else:
                fail_msgs.append(msg)

        summary = f"补签完成：成功 {success_count} 人"
        if fail_msgs:
            summary += f"，跳过 {len(fail_msgs)} 人"
            detail = "\n".join(fail_msgs[:5])
            if len(fail_msgs) > 5:
                detail += f"\n...等共 {len(fail_msgs)} 条"
            QMessageBox.information(self, "补签结果", f"{summary}\n\n{detail}")
        else:
            QMessageBox.information(self, "补签结果", summary)

        self.accept()
