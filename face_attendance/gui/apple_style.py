"""
Apple 风格样式模块
提供统一的苹果设计风格样式
"""

# ==================== 颜色配置 ====================
# 苹果设计系统配色
COLORS = {
    # 主色调
    'primary': '#007AFF',        # 苹果蓝
    'primary_hover': '#0056CC',  # 悬停状态
    'primary_light': '#E5F1FF',  # 浅蓝背景

    # 功能色
    'success': '#34C759',        # 绿色
    'success_hover': '#248A3D',
    'warning': '#FF9500',        # 橙色
    'danger': '#FF3B30',         # 红色
    'danger_hover': '#D70015',

    # 中性色
    'background': '#F5F5F7',     # 主背景
    'surface': '#FFFFFF',        # 卡片背景
    'sidebar': '#1D1D1F',        # 导航栏背景
    'sidebar_hover': '#3A3A3C',  # 导航栏悬停
    'sidebar_active': '#007AFF', # 导航栏选中

    # 文字颜色
    'text_primary': '#1D1D1F',   # 主文字
    'text_secondary': '#86868B', # 次要文字
    'text_light': '#FFFFFF',     # 浅色文字
    'text_placeholder': '#AEAEB2', # 占位符

    # 边框和分割线
    'border': '#D1D1D6',
    'divider': '#E5E5EA',

    # 表格
    'table_header': '#F2F2F7',
    'table_alternate': '#FAFAFA',
    'table_selected': '#E5F1FF',

    # 视频区域
    'video_bg': '#1C1C1E',
    'video_border': '#007AFF',

    # 侧边栏半透明颜色
    'sidebar_text_secondary': 'rgba(255, 255, 255, 0.5)',
    'sidebar_divider': 'rgba(255, 255, 255, 0.1)',
    'sidebar_user_bg': 'rgba(255, 255, 255, 0.05)',
}

# ==================== 字体配置 ====================
# 使用更独特的字体组合，避免通用AI风格
FONTS = {
    # 主字体：使用苹方/PingFang作为主字体，更具设计感
    'family': '"PingFang SC", "HarmonyOS Sans SC", "Microsoft YaHei UI", sans-serif',
    # 数字/代码字体
    'mono': '"JetBrains Mono", "Fira Code", "Cascadia Code", Consolas, monospace',
    'title_size': '22px',
    'subtitle_size': '16px',
    'body_size': '14px',
    'small_size': '12px',
    'button_size': '14px',
    # 字重
    'weight_light': '300',
    'weight_regular': '400',
    'weight_medium': '500',
    'weight_semibold': '600',
    'weight_bold': '700',
}

# ==================== 圆角配置 ====================
RADIUS = {
    'small': '6px',
    'medium': '10px',
    'large': '14px',
    'xl': '20px',
}

# ==================== 阴影配置 ====================
SHADOWS = {
    'small': '0 1px 3px rgba(0, 0, 0, 0.08)',
    'medium': '0 4px 12px rgba(0, 0, 0, 0.1)',
    'large': '0 8px 24px rgba(0, 0, 0, 0.12)',
    'card': '0 2px 8px rgba(0, 0, 0, 0.06)',
}

# ==================== 动画配置 ====================
ANIMATION = {
    'transition': 'all 0.2s ease',
    'transition_slow': 'all 0.3s ease',
    'transition_fast': 'all 0.15s ease',
    'bounce': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
    'smooth': 'cubic-bezier(0.4, 0, 0.2, 1)',
    'ease_out': 'cubic-bezier(0, 0, 0.2, 1)',
}

# ==================== 渐变配置（增强独特性）====================
GRADIENTS = {
    # 主色渐变
    'primary': f'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COLORS["primary"]}, stop:1 #0055CC)',
    # 侧边栏渐变
    'sidebar': 'qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1a1a1c, stop:1 #2d2d30)',
    # 成功渐变
    'success': f'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS["success"]}, stop:1 #28a745)',
    # 危险渐变
    'danger': f'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS["danger"]}, stop:1 #dc3545)',
    # 金色渐变（用于强调）
    'gold': 'qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f5af19, stop:1 #f12711)',
    # 玻璃效果背景
    'glass': 'qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255,255,255,0.15), stop:1 rgba(255,255,255,0.05))',
}

# ==================== 图标配置 ====================
ICONS = {
    # 导航图标
    'attendance': '📅',
    'students': '👥',
    'courses': '📚',
    'records': '📊',
    'export': '📤',
    # 操作图标
    'add': '➕',
    'edit': '✏️',
    'delete': '🗑️',
    'refresh': '🔄',
    'search': '🔍',
    'camera': '📷',
    'capture': '📸',
    # 状态图标
    'success': '✅',
    'warning': '⚠️',
    'error': '❌',
    'info': 'ℹ️',
    'loading': '⏳',
    # 空状态图标
    'empty_students': '👥',
    'empty_courses': '📚',
    'empty_records': '📋',
    'empty_search': '🔍',
}


# ==================== 主窗口样式 ====================
MAIN_WINDOW_STYLE = f"""
QMainWindow {{
    background-color: {COLORS['background']};
}}
"""


# ==================== 导航栏样式 ====================
NAVIGATION_STYLE = f"""
QFrame {{
    background-color: {COLORS['sidebar']};
    border: none;
}}

QLabel#titleLabel {{
    color: {COLORS['text_light']};
    font-size: 20px;
    font-weight: 600;
    padding: 24px 16px;
    background-color: transparent;
}}

QPushButton {{
    background-color: transparent;
    color: {COLORS['text_light']};
    border: none;
    padding: 16px 20px;
    text-align: left;
    font-size: {FONTS['body_size']};
    font-weight: 500;
    border-radius: {RADIUS['medium']};
    margin: 4px 8px;
}}

QPushButton:hover {{
    background-color: {COLORS['sidebar_hover']};
}}

QPushButton:checked {{
    background-color: {COLORS['sidebar_active']};
    color: {COLORS['text_light']};
}}

QFrame#userFrame {{
    background-color: rgba(0, 0, 0, 0.3);
    border-radius: {RADIUS['medium']};
    margin: 8px;
    padding: 12px;
}}

QLabel#userLabel {{
    color: rgba(255, 255, 255, 0.8);
    font-size: {FONTS['small_size']};
}}

QLabel#versionLabel {{
    color: rgba(255, 255, 255, 0.4);
    font-size: {FONTS['small_size']};
    padding: 16px;
}}
"""


# ==================== 按钮样式 ====================
def get_button_style(style_type='primary'):
    """获取按钮样式"""
    styles = {
        'primary': f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: #FFFFFF;
                border: none;
                border-radius: {RADIUS['medium']};
                padding: 12px 24px;
                font-size: 15px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_hover']};
            }}
            QPushButton:pressed {{
                background-color: #004499;
            }}
            QPushButton:disabled {{
                background-color: #B0B0B5;
                color: #E5E5E5;
            }}
        """,
        'success': f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: #FFFFFF;
                border: none;
                border-radius: {RADIUS['medium']};
                padding: 12px 24px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLORS['success_hover']};
            }}
            QPushButton:pressed {{
                background-color: #1A7F37;
            }}
            QPushButton:disabled {{
                background-color: #B0B0B5;
                color: #E5E5E5;
            }}
        """,
        'danger': f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: #FFFFFF;
                border: none;
                border-radius: {RADIUS['medium']};
                padding: 12px 24px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger_hover']};
            }}
            QPushButton:pressed {{
                background-color: #B50000;
            }}
            QPushButton:disabled {{
                background-color: #B0B0B5;
                color: #E5E5E5;
            }}
        """,
        'secondary': f"""
            QPushButton {{
                background-color: {COLORS['table_header']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: {RADIUS['medium']};
                padding: 12px 24px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['divider']};
                border-color: {COLORS['text_placeholder']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['border']};
            }}
            QPushButton:disabled {{
                background-color: {COLORS['table_header']};
                color: {COLORS['text_placeholder']};
            }}
        """,
        'ghost': f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['primary']};
                border: none;
                border-radius: {RADIUS['medium']};
                padding: 12px 24px;
                font-size: {FONTS['button_size']};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS['primary_light']};
            }}
            QPushButton:pressed {{
                background-color: #CCE0FF;
            }}
        """,
    }
    return styles.get(style_type, styles['primary'])


# 登录按钮样式
LOGIN_BUTTON_STYLE = f"""
QPushButton {{
    background-color: {COLORS['primary']};
    color: {COLORS['text_light']};
    border: none;
    border-radius: {RADIUS['medium']};
    padding: 14px 32px;
    font-size: {FONTS['button_size']};
    font-weight: 600;
}}
QPushButton:hover {{
    background-color: {COLORS['primary_hover']};
}}
QPushButton:pressed {{
    background-color: #004499;
}}
"""

# 注销按钮样式
LOGOUT_BUTTON_STYLE = f"""
QPushButton {{
    background-color: rgba(255, 59, 48, 0.2);
    color: #FF6B6B;
    border: none;
    border-radius: {RADIUS['small']};
    padding: 10px 16px;
    font-size: {FONTS['small_size']};
    font-weight: 500;
}}
QPushButton:hover {{
    background-color: rgba(255, 59, 48, 0.3);
}}
"""

# 必填字段星号样式
REQUIRED_ASTERISK_STYLE = f"""
QLabel {{
    color: {COLORS['danger']};
    font-size: {FONTS['body_size']};
    font-weight: 600;
}}
"""


# ==================== 输入框样式 ====================
INPUT_STYLE = f"""
QLineEdit {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['small']};
    padding: 10px 14px;
    font-size: {FONTS['body_size']};
    selection-background-color: {COLORS['primary_light']};
}}
QLineEdit:hover {{
    border-color: {COLORS['text_placeholder']};
}}
QLineEdit:focus {{
    border-color: {COLORS['primary']};
    border-width: 2px;
    padding: 9px 13px;
}}
QLineEdit:disabled {{
    background-color: {COLORS['table_header']};
    color: {COLORS['text_secondary']};
}}
QLineEdit::placeholder {{
    color: {COLORS['text_placeholder']};
}}
"""

# 搜索框样式
SEARCH_INPUT_STYLE = f"""
QLineEdit {{
    background-color: {COLORS['table_header']};
    color: {COLORS['text_primary']};
    border: 1px solid transparent;
    border-radius: {RADIUS['medium']};
    padding: 10px 16px;
    font-size: {FONTS['body_size']};
}}
QLineEdit:hover {{
    background-color: {COLORS['divider']};
}}
QLineEdit:focus {{
    background-color: {COLORS['surface']};
    border-color: {COLORS['primary']};
}}
"""


# ==================== 下拉框样式 ====================
COMBO_STYLE = f"""
QComboBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['small']};
    padding: 10px 14px;
    font-size: {FONTS['body_size']};
    min-width: 120px;
}}
QComboBox:hover {{
    border-color: {COLORS['text_placeholder']};
}}
QComboBox:focus {{
    border-color: {COLORS['primary']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['small']};
    selection-background-color: {COLORS['primary_light']};
    selection-color: {COLORS['text_primary']};
    padding: 4px;
}}
"""


# ==================== 表格样式 ====================
TABLE_STYLE = f"""
QTableWidget {{
    background-color: {COLORS['surface']};
    alternate-background-color: {COLORS['table_alternate']};
    border: 1px solid {COLORS['divider']};
    border-radius: {RADIUS['medium']};
    gridline-color: {COLORS['divider']};
    font-size: {FONTS['body_size']};
}}
QTableWidget::item {{
    padding: 12px 16px;
    border-bottom: 1px solid {COLORS['divider']};
}}
QTableWidget::item:selected {{
    background-color: {COLORS['table_selected']};
    color: {COLORS['text_primary']};
}}
QTableWidget::item:hover {{
    background-color: {COLORS['table_header']};
}}
QTableWidget {{
    outline: 0px;
}}
QTableWidget::item:focus {{
    outline: 0px;
    border: none;
}}
QHeaderView::section {{
    background-color: {COLORS['table_header']};
    color: {COLORS['text_secondary']};
    font-weight: 600;
    padding: 14px 16px;
    border: none;
    border-bottom: 1px solid {COLORS['divider']};
    font-size: {FONTS['small_size']};
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
QHeaderView::section:first {{
    border-top-left-radius: {RADIUS['medium']};
}}
QHeaderView::section:last {{
    border-top-right-radius: {RADIUS['medium']};
}}
"""


# ==================== 标签页样式 ====================
TAB_STYLE = f"""
QTabWidget::pane {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['divider']};
    border-radius: {RADIUS['medium']};
    top: -1px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {COLORS['text_secondary']};
    padding: 12px 24px;
    margin-right: 4px;
    border-top-left-radius: {RADIUS['small']};
    border-top-right-radius: {RADIUS['small']};
    font-size: {FONTS['body_size']};
    font-weight: 500;
}}

QTabBar::tab:hover {{
    background-color: {COLORS['table_header']};
    color: {COLORS['text_primary']};
}}

QTabBar::tab:selected {{
    background-color: {COLORS['surface']};
    color: {COLORS['primary']};
    font-weight: 600;
}}
"""


# ==================== 分组框样式 ====================
GROUP_BOX_STYLE = f"""
QGroupBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['divider']};
    border-radius: {RADIUS['medium']};
    margin-top: 20px;
    padding: 20px 16px 16px 16px;
    font-size: {FONTS['body_size']};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 8px;
    color: {COLORS['text_primary']};
    font-weight: 600;
    font-size: {FONTS['subtitle_size']};
}}
"""


# ==================== 对话框样式 ====================
DIALOG_STYLE = f"""
QDialog {{
    background-color: {COLORS['background']};
}}
"""

# 登录对话框样式
LOGIN_DIALOG_STYLE = f"""
QDialog {{
    background-color: {COLORS['surface']};
}}
QLabel#titleLabel {{
    color: {COLORS['text_primary']};
    font-size: 24px;
    font-weight: 700;
}}
QLabel#hintLabel {{
    color: {COLORS['text_secondary']};
    font-size: {FONTS['small_size']};
}}
QLabel#label {{
    color: {COLORS['text_primary']};
    font-size: {FONTS['body_size']};
}}
QFrame#separator {{
    background-color: {COLORS['divider']};
    max-height: 1px;
}}
"""


# ==================== 视频显示区域样式 ====================
VIDEO_LABEL_STYLE = f"""
QLabel {{
    background-color: {COLORS['video_bg']};
    color: {COLORS['text_secondary']};
    font-size: {FONTS['subtitle_size']};
    border: 2px solid {COLORS['video_border']};
    border-radius: {RADIUS['large']};
}}
"""


# ==================== 消息框样式 ====================
MESSAGE_BOX_STYLE = f"""
QMessageBox {{
    background-color: {COLORS['surface']};
}}
QMessageBox QLabel {{
    color: {COLORS['text_primary']};
    font-size: {FONTS['body_size']};
}}
QMessageBox QPushButton {{
    background-color: #E0E0E0;
    color: #000000;
    border: 1px solid #BDBDBD;
    border-radius: {RADIUS['medium']};
    padding: 10px 28px;
    font-size: 14px;
    font-weight: 700;
    min-width: 90px;
    min-height: 36px;
}}
QMessageBox QPushButton:hover {{
    background-color: #D0D0D0;
}}
QMessageBox QPushButton:pressed {{
    background-color: #BDBDBD;
}}
"""


# ==================== 日期选择器样式 ====================
DATE_EDIT_STYLE = f"""
QDateEdit {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['small']};
    padding: 10px 14px;
    font-size: {FONTS['body_size']};
    min-width: 100px;
}}
QDateEdit:hover {{
    border-color: {COLORS['text_placeholder']};
}}
QDateEdit:focus {{
    border-color: {COLORS['primary']};
}}
QDateEdit::drop-down {{
    border: none;
    width: 24px;
}}
QDateEdit::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {COLORS['text_secondary']};
    margin-right: 8px;
}}
"""

# 时间选择器样式
TIME_EDIT_STYLE = f"""
QTimeEdit {{
    background-color: {COLORS['surface']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['small']};
    padding: 10px 14px;
    padding-right: 36px;
    font-size: {FONTS['body_size']};
    min-width: 80px;
}}
QTimeEdit:hover {{
    border-color: {COLORS['text_placeholder']};
}}
QTimeEdit:focus {{
    border-color: {COLORS['primary']};
}}
/* 下拉按钮区域 */
QTimeEdit::drop-down {{
    border: none;
    width: 32px;
    subcontrol-position: center right;
}}
/* 向上按钮 */
QTimeEdit::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 28px;
    height: 18px;
    background-color: {COLORS['primary_light']};
    border: none;
    border-top-right-radius: {RADIUS['small']};
    margin: 2px 2px 0 0;
}}
QTimeEdit::up-button:hover {{
    background-color: {COLORS['primary']};
}}
QTimeEdit::up-button:pressed {{
    background-color: {COLORS['primary_hover']};
}}
/* 向上箭头 - 更明显的三角形 */
QTimeEdit::up-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-bottom: 7px solid {COLORS['primary']};
    width: 10px;
    height: 10px;
}}
QTimeEdit::up-button:hover QTimeEdit::up-arrow {{
    border-bottom-color: white;
}}
/* 向下按钮 */
QTimeEdit::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 28px;
    height: 18px;
    background-color: {COLORS['primary_light']};
    border: none;
    border-bottom-right-radius: {RADIUS['small']};
    margin: 0 2px 2px 0;
}}
QTimeEdit::down-button:hover {{
    background-color: {COLORS['primary']};
}}
QTimeEdit::down-button:pressed {{
    background-color: {COLORS['primary_hover']};
}}
/* 向下箭头 - 更明显的三角形 */
QTimeEdit::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 7px solid {COLORS['primary']};
    width: 10px;
    height: 10px;
}}
QTimeEdit::down-button:hover QTimeEdit::down-arrow {{
    border-top-color: white;
}}
"""

# 日历弹出样式
CALENDAR_STYLE = f"""
QCalendarWidget {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: {RADIUS['medium']};
}}
QCalendarWidget QToolButton {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    border-radius: {RADIUS['small']};
    padding: 6px 12px;
}}
QCalendarWidget QToolButton:hover {{
    background-color: {COLORS['table_header']};
}}
QCalendarWidget QSpinBox {{
    background-color: transparent;
    color: {COLORS['text_primary']};
    border: none;
}}
"""


# ==================== 滚动条样式 ====================
SCROLL_STYLE = f"""
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS['text_placeholder']};
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['text_secondary']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background-color: transparent;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    margin: 2px 4px;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLORS['text_placeholder']};
    border-radius: 4px;
    min-width: 32px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['text_secondary']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


# ==================== 工具提示样式 ====================
TOOLTIP_STYLE = f"""
QToolTip {{
    background-color: {COLORS['sidebar']};
    color: {COLORS['text_light']};
    border: none;
    border-radius: {RADIUS['small']};
    padding: 8px 12px;
    font-size: {FONTS['small_size']};
}}
"""


# ==================== 状态标签样式 ====================
STATUS_LABEL_STYLE = f"""
QLabel {{
    padding: 4px 12px;
    border-radius: {RADIUS['small']};
    font-size: {FONTS['small_size']};
    font-weight: 500;
}}
"""

# 统计信息标签
STATS_LABEL_STYLE = f"""
QLabel {{
    color: {COLORS['text_secondary']};
    padding: 12px 16px;
    font-size: {FONTS['body_size']};
    background-color: {COLORS['table_header']};
    border-radius: {RADIUS['medium']};
}}
"""

# ==================== 状态徽章样式 ====================
def get_status_badge_style(status):
    """获取状态徽章样式"""
    colors = {
        'normal': COLORS['success'],
        'late': COLORS['warning'],
        'absent': COLORS['danger']
    }
    bg_color = colors.get(status, COLORS['text_secondary'])
    return f"""
        QLabel {{
            background-color: {bg_color};
            color: white;
            padding: 4px 12px;
            border-radius: {RADIUS['small']};
            font-size: {FONTS['small_size']};
            font-weight: 500;
        }}
    """


# ==================== 应用全局样式 ====================
def get_app_style():
    """获取应用程序全局样式"""
    return f"""
    /* 全局设置 */
    QWidget {{
        font-family: {FONTS['family']};
        color: {COLORS['text_primary']};
    }}

    QMainWindow {{
        background-color: {COLORS['background']};
    }}

    /* 工具提示 */
    {TOOLTIP_STYLE}

    /* 滚动条 */
    {SCROLL_STYLE}

    /* 消息框 */
    {MESSAGE_BOX_STYLE}
    """


# ==================== 导出所有样式 ====================
__all__ = [
    'COLORS',
    'FONTS',
    'RADIUS',
    'SHADOWS',
    'ANIMATION',
    'GRADIENTS',
    'ICONS',
    'MAIN_WINDOW_STYLE',
    'NAVIGATION_STYLE',
    'LOGIN_BUTTON_STYLE',
    'LOGOUT_BUTTON_STYLE',
    'REQUIRED_ASTERISK_STYLE',
    'get_button_style',
    'INPUT_STYLE',
    'SEARCH_INPUT_STYLE',
    'COMBO_STYLE',
    'TABLE_STYLE',
    'TAB_STYLE',
    'GROUP_BOX_STYLE',
    'DIALOG_STYLE',
    'LOGIN_DIALOG_STYLE',
    'VIDEO_LABEL_STYLE',
    'MESSAGE_BOX_STYLE',
    'DATE_EDIT_STYLE',
    'TIME_EDIT_STYLE',
    'CALENDAR_STYLE',
    'SCROLL_STYLE',
    'TOOLTIP_STYLE',
    'STATUS_LABEL_STYLE',
    'STATS_LABEL_STYLE',
    'get_status_badge_style',
    'get_app_style',
]