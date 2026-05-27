"""
演示数据生成脚本
创建示例目录结构和空数据库，无需真实人脸数据即可验证系统启动
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from database.db_manager import DatabaseManager
from utils.security import hash_password


def create_demo_db():
    """创建空数据库并添加演示账号"""
    db_path = os.path.join(BASE_DIR, 'face_attendance.db')
    if os.path.exists(db_path):
        print(f"[跳过] 数据库已存在: {db_path}")
        return

    db = DatabaseManager(db_path)

    # 创建默认管理员账号
    db.add_user('admin', hash_password('admin123'), role='admin')
    print("[OK] 创建默认账号: admin / admin123")

    # 创建示例课程
    db.add_course(
        course_code='CS101',
        course_name='计算机视觉',
        teacher_name='张老师',
        start_time='08:00',
        end_time='09:40'
    )
    db.add_course(
        course_code='CS102',
        course_name='机器学习',
        teacher_name='李老师',
        start_time='10:00',
        end_time='11:40'
    )
    print("[OK] 创建示例课程: 计算机视觉, 机器学习")


def create_demo_dirs():
    """创建示例数据目录结构"""
    demo_root = os.path.join(os.path.dirname(BASE_DIR), 'demo_data')
    classes = ['计算机科学1班', '计算机科学2班']

    for cls in classes:
        for subset in ['train', 'test', 'val']:
            # 创建两个示例学生目录
            for sid, name in [('1', '张三'), ('2', '李四')]:
                dir_path = os.path.join(demo_root, cls, subset, f'{sid}_{name}')
                os.makedirs(dir_path, exist_ok=True)

    print(f"[OK] 创建演示目录结构: {demo_root}")
    print("      请将学生照片放入对应目录后运行 import_data.py 导入")


if __name__ == '__main__':
    print("=" * 50)
    print("人脸识别考勤系统 - 演示环境初始化")
    print("=" * 50)

    create_demo_db()
    create_demo_dirs()

    print()
    print("初始化完成！运行 python main.py 启动系统")
    print("首次运行时，InsightFace模型会自动下载（约200MB）")
