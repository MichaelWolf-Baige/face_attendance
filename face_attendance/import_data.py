"""
导入现有学生数据脚本
从项目根目录的学生文件夹导入人脸数据
"""
import os

from app_context import AppContext


def import_existing_students():
    """导入现有学生数据"""
    # 数据目录
    data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    print(f"数据目录: {data_dir}")
    print("正在扫描学生数据目录...")

    # 使用 AppContext 统一管理依赖
    ctx = AppContext()
    student_service = ctx.student_service

    # 扫描学生目录
    # 格式: 学号_姓名/ 或 学号_姓名.jpg
    imported = 0
    errors = []

    for item in os.listdir(data_dir):
        item_path = os.path.join(data_dir, item)

        # 检查是否是学生目录 (格式: 5_方皓辉)
        if os.path.isdir(item_path) and '_' in item:
            parts = item.split('_', 1)
            if len(parts) == 2:
                student_id = parts[0].strip()
                name = parts[1].strip()

                # 获取目录中的图片
                images = [f for f in os.listdir(item_path)
                         if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

                if images:
                    # 使用第一张图片
                    image_path = os.path.join(item_path, images[0])
                    print(f"正在导入: {name} ({student_id}) - {images[0]}")

                    success, msg = student_service.register_student(
                        student_id=student_id,
                        name=name,
                        class_name="默认班级",
                        image_path=image_path
                    )

                    if success:
                        imported += 1
                        print(f"  [OK] {msg}")
                    else:
                        errors.append(f"{name}: {msg}")
                        print(f"  [FAIL] {msg}")

    print(f"\n导入完成: 成功 {imported} 名学生")
    if errors:
        print(f"\n失败记录:")
        for e in errors:
            print(f"  - {e}")

    return imported, errors


def add_sample_course():
    """添加示例课程"""
    from services.course_service import CourseService

    db = DatabaseManager(os.path.join(os.path.dirname(__file__), 'face_attendance.db'))
    course_service = CourseService(db)

    # 添加示例课程
    courses = [
        ('CS101', '计算机基础', '张老师', '08:00', '09:40'),
        ('CS201', '数据结构', '李老师', '10:00', '11:40'),
        ('CS301', '人工智能', '王老师', '14:00', '15:40'),
    ]

    for code, name, teacher, start, end in courses:
        result = course_service.add_course(code, name, teacher, start, end)
        if 'error' not in result:
            print(f"添加课程: {name}")
        else:
            print(f"课程 {name} 已存在或添加失败")


if __name__ == '__main__':
    print("=" * 50)
    print("人脸识别考勤系统 - 数据导入工具")
    print("=" * 50)

    # 导入学生
    import_existing_students()

    print()

    # 添加示例课程
    add_sample_course()

    print("\n数据导入完成，可以启动系统了！")
    print("运行命令: python main.py")