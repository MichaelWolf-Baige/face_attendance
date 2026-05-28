"""
批量导入人工智能一班和二班的学生人脸数据
使用 StudentService 统一导入流程，支持多图编码平均
支持 Ctrl+C 中断 + 断点续传
"""
import os
import sys

# CUDA/cuDNN DLL PATH 注册（与 main.py 保持一致）
_site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')
for _lib in ['nvidia/cudnn/bin', 'nvidia/cublas/bin']:
    _path = os.path.join(_site_packages, _lib)
    if os.path.isdir(_path) and _path not in os.environ.get('PATH', ''):
        os.environ['PATH'] = _path + ';' + os.environ.get('PATH', '')

from datetime import datetime
from database.db_manager import DatabaseManager
from services.student_service import StudentService
from services.course_service import CourseService

# 全局取消标志
_cancelled = False


def progress_callback(current, total, status_text):
    """进度回调"""
    pct = current / total * 100 if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current / total) if total > 0 else 0
    bar = '#' * filled + '-' * (bar_len - filled)
    print(f"\r  [{bar}] {pct:.0f}%  {status_text}", end='', flush=True)


def main():
    global _cancelled
    print("=" * 60)
    print("批量导入学生人脸数据")
    print("=" * 60)

    # 错误日志路径
    log_dir = os.path.dirname(os.path.abspath(__file__))
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(log_dir, f'import_errors_{timestamp}.log')

    # 使用 AppContext 统一管理依赖
    from app_context import AppContext
    ctx = AppContext()
    db = ctx.db
    student_service = ctx.student_service

    existing = len(db.get_all_students())
    if existing > 0:
        print(f"\n现有学生数量: {existing} (已导入的学生将自动跳过)")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    total_imported = 0
    all_errors = []

    classes = [
        (os.path.join(base_dir, "23人工智能1班"), "23人工智能1班"),
        (os.path.join(base_dir, "23人工智能2班"), "23人工智能2班"),
    ]

    for class_dir, class_name in classes:
        if _cancelled:
            break
        if not os.path.exists(class_dir):
            print(f"\n班级目录不存在: {class_dir}")
            continue

        print(f"\n导入 {class_name} (使用train/test/val中全部图片)...")
        print("  按 Ctrl+C 可安全中断，已导入的数据不会丢失\n")

        try:
            imported, errors = student_service.register_from_class_dir(
                class_dir, class_name,
                progress_callback=progress_callback,
                error_log_path=log_path
            )
        except KeyboardInterrupt:
            print("\n\n[中断] 用户按下 Ctrl+C")
            _cancelled = True
            break

        print()  # 换行
        total_imported += imported
        all_errors.extend(errors)
        print(f"  {class_name}导入: {imported} 人")

    # 添加课程
    if not _cancelled:
        print("\n添加课程...")
        course_service = CourseService(db)
        course_service.add_course('AI001', '人工智能导论', '张老师', '08:00', '09:40')
        course_service.add_course('AI002', '机器学习', '李老师', '10:00', '11:40')
        course_service.add_course('AI003', '深度学习', '王老师', '14:00', '15:40')

    # 统计
    final_count = len(db.get_all_students())
    print("\n" + "=" * 60)
    if _cancelled:
        print("导入已中断!")
    else:
        print("导入完成!")
    print(f"  本次新增: {total_imported} 人")
    print(f"  数据库总数: {final_count} 人")

    if all_errors:
        print(f"\n详情 ({len(all_errors)} 条):")
        for e in all_errors[:10]:
            print(f"  - {e}")
        if len(all_errors) > 10:
            print(f"  ... 还有 {len(all_errors) - 10} 条")

    # 写入导入摘要
    summary_path = os.path.join(log_dir, f'import_summary_{timestamp}.txt')
    try:
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"导入时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"状态: {'中断' if _cancelled else '完成'}\n")
            f.write(f"新增学生: {total_imported} 人\n")
            f.write(f"数据库总数: {final_count} 人\n")
            if all_errors:
                f.write(f"\n失败/跳过记录 ({len(all_errors)} 条):\n")
                for e in all_errors:
                    f.write(f"  {e}\n")
            f.write(f"\n错误日志: {log_path if all_errors else '无'}\n")
            f.write("\n提示: 直接重新运行本脚本即可续传，已导入的学生会自动跳过。\n")
        print(f"\n导入摘要已保存: {summary_path}")
    except Exception:
        pass

    print("\n可以启动系统了: python main.py")


if __name__ == '__main__':
    main()
