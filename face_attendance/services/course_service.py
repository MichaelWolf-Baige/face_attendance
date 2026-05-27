"""
课程管理服务
"""
import os
from datetime import date
from typing import List, Dict, Optional

class CourseService:
    """课程管理服务"""

    def __init__(self, db_manager):
        self.db = db_manager

    def add_course(self, course_code: str, course_name: str,
                   teacher_name: str = None,
                   start_time: str = None,
                   end_time: str = None) -> Dict:
        """
        添加课程

        Args:
            course_code: 课程代码
            course_name: 课程名称
            teacher_name: 教师姓名
            start_time: 上课时间 (如: 08:00)
            end_time: 下课时间 (如: 09:40)

        Returns:
            创建的课程信息
        """
        # 检查课程代码是否已存在
        courses = self.db.get_all_courses()
        for c in courses:
            if c['course_code'] == course_code:
                return {'error': f"课程代码 {course_code} 已存在"}

        return self.db.add_course(course_code, course_name, teacher_name, start_time, end_time)

    def get_course(self, course_id: int) -> Optional[Dict]:
        """获取课程信息"""
        return self.db.get_course(course_id)

    def get_all_courses(self) -> List[Dict]:
        """获取所有课程"""
        return self.db.get_all_courses()

    def delete_course(self, course_id: int) -> bool:
        """删除课程"""
        return self.db.delete_course(course_id)

    def update_course(self, course_id: int, **kwargs) -> bool:
        """更新课程信息"""
        return self.db.update_course(course_id, **kwargs)

    def get_course_attendance_summary(self, course_id: int,
                                       start_date: date = None,
                                       end_date: date = None) -> Dict:
        """
        获取课程考勤汇总

        Args:
            course_id: 课程ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            汇总数据
        """
        records = self.db.export_attendance_records(course_id, start_date, end_date)

        if not records:
            return {
                'course_id': course_id,
                'total_records': 0,
                'students': [],
                'summary': {}
            }

        # 按学生统计
        student_stats = {}
        for record in records:
            student_id = record['学号']
            if student_id not in student_stats:
                student_stats[student_id] = {
                    'name': record['姓名'],
                    'class': record['班级'],
                    'total': 0,
                    'normal': 0,
                    'late': 0,
                    'absent': 0
                }

            student_stats[student_id]['total'] += 1
            if record['状态'] == '正常':
                student_stats[student_id]['normal'] += 1
            elif record['状态'] == '迟到':
                student_stats[student_id]['late'] += 1
            else:
                student_stats[student_id]['absent'] += 1

        # 计算出勤率
        for stats in student_stats.values():
            stats['attendance_rate'] = (stats['normal'] + stats['late']) / stats['total'] * 100 if stats['total'] > 0 else 0

        return {
            'course_id': course_id,
            'total_records': len(records),
            'students': list(student_stats.values()),
            'summary': {
                'total_students': len(student_stats),
                'avg_attendance_rate': sum(s['attendance_rate'] for s in student_stats.values()) / len(student_stats) if student_stats else 0
            }
        }