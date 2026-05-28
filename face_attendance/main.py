"""
程序入口
人脸识别考勤系统
"""
import sys
import os
import argparse

# CUDA/cuDNN DLL PATH（onnxruntime-gpu 需要，CPU 版本自动跳过）
_site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')
for _lib in ['nvidia/cudnn/bin', 'nvidia/cublas/bin']:
    _path = os.path.join(_site_packages, _lib)
    if os.path.isdir(_path) and _path not in os.environ.get('PATH', ''):
        os.environ['PATH'] = _path + ';' + os.environ.get('PATH', '')

# 必须在 PyQt5 之前导入 onnxruntime，否则 DLL 加载冲突
try:
    import onnxruntime
except ImportError as e:
    print(f"[错误] onnxruntime 未安装: {e}")
    print("请执行: pip install onnxruntime insightface")
    print(f"当前 Python: {sys.executable}")
    input("按 Enter 退出...")
    sys.exit(1)

import config

# 解析命令行参数，在 AppContext 创建前确定性能配置
parser = argparse.ArgumentParser(description='人脸识别考勤系统')
parser.add_argument('--cpu', action='store_const', const='cpu', dest='profile',
                    help='强制低配模式 (集成显卡/老电脑)')
parser.add_argument('--gpu', action='store_const', const='gpu', dest='profile',
                    help='强制高性能模式 (需要 NVIDIA 显卡)')
args, _ = parser.parse_known_args()
if args.profile:
    config.PERFORMANCE_PROFILE = args.profile
config.auto_detect_profile()

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
from app_context import AppContext
from gui.main_window import MainWindow
from gui.login_dialog import LoginDialog


def ensure_default_admin(ctx: AppContext):
    """确保存在默认管理员账户"""
    admin_user = ctx.db.get_user('admin')
    if admin_user is None:
        ctx.db.add_user('admin', 'admin123', 'admin')
        print("[初始化] 已创建默认管理员账户: admin / admin123")


def main():
    """主函数"""
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # QMessageBox "OK" 按钮全局样式
    app.setStyleSheet("""
        QMessageBox QPushButton {
            background-color: #E0E0E0; color: #000000;
            border: 1px solid #BDBDBD; border-radius: 6px;
            padding: 8px 24px; font-size: 14px; font-weight: 700;
            min-width: 80px; min-height: 32px;
        }
        QMessageBox QPushButton:hover { background-color: #D0D0D0; }
        QMessageBox QPushButton:pressed { background-color: #BDBDBD; }
    """)

    font = app.font()
    font.setFamily("Microsoft YaHei")
    app.setFont(font)

    # 创建应用上下文 (所有共享实例的唯一来源)
    ctx = AppContext()

    # 确保存在默认管理员账户
    ensure_default_admin(ctx)

    # 主循环：登录 -> 主界面 -> 退出登录 -> 返回登录
    while True:
        login_dialog = LoginDialog(ctx)
        if login_dialog.exec_() != LoginDialog.Accepted:
            break

        window = MainWindow(ctx)
        window.show()

        app.exec_()

        if ctx.session.current_user is None:
            continue
        else:
            break

    sys.exit(0)


if __name__ == '__main__':
    main()
