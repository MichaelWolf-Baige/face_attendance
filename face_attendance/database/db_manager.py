"""
数据库管理器
提供数据库操作的统一接口
"""
import os
import re
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from .models import Base, Student, Course, AttendanceRecord, User


def _natural_key(s: str):
    """自然排序键：'1-10' > '1-2', '10' > '2'"""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]


def encoding_to_blob(encoding: np.ndarray) -> Optional[bytes]:
    """将numpy数组转换为BLOB存储"""
    if encoding is None:
        return None
    return encoding.tobytes()


def blob_to_encoding(blob: bytes) -> Optional[np.ndarray]:
    """将BLOB转换为numpy数组（自动识别float32/float64）"""
    if blob is None:
        return None
    blob_len = len(blob)
    # 512 * 4 = 2048 (InsightFace ArcFace float32)
    if blob_len == 2048:
        return np.frombuffer(blob, dtype=np.float32).copy()
    # 128 * 8 = 1024 (dlib float64，向后兼容)
    if blob_len == 1024:
        return np.frombuffer(blob, dtype=np.float64).copy()
    # 未知大小，尝试按 float32 解码
    if blob_len % 4 == 0 and blob_len >= 512:
        return np.frombuffer(blob, dtype=np.float32).copy()
    return None


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径，默认为当前目录下的 face_attendance.db
        """
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'face_attendance.db')

        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        self.Session = sessionmaker(bind=self.engine)
        self.init_db()

    def init_db(self):
        """初始化数据库，创建所有表"""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def get_session(self):
        """获取数据库会话的上下文管理器"""
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # ==================== 学生相关操作 ====================

    def add_student(self, student_id: str, name: str, class_name: str = None,
                    face_encoding: np.ndarray = None, face_image_path: str = None) -> Student:
        """
        添加学生

        Args:
            student_id: 学号
            name: 姓名
            class_name: 班级
            face_encoding: 人脸特征向量
            face_image_path: 人脸图片路径

        Returns:
            创建的Student对象
        """
        with self.get_session() as session:
            student = Student(
                student_id=student_id,
                name=name,
                class_name=class_name,
                face_encoding=encoding_to_blob(face_encoding),
                face_image_path=face_image_path
            )
            session.add(student)
            session.flush()
            # 获取ID
            student_id_db = student.id
            student_data = {
                'id': student_id_db,
                'student_id': student.student_id,
                'name': student.name,
                'class_name': student.class_name,
                'face_image_path': student.face_image_path
            }
            return student_data

    def get_student(self, student_id: str) -> Optional[Dict]:
        """根据学号获取学生"""
        with self.get_session() as session:
            student = session.query(Student).filter(Student.student_id == student_id).first()
            if student is None:
                return None
            return {
                'id': student.id,
                'student_id': student.student_id,
                'name': student.name,
                'class_name': student.class_name,
                'face_image_path': student.face_image_path,
                'created_at': student.created_at
            }

    def get_student_by_pk(self, pk: int) -> Optional[Dict]:
        """根据主键ID获取学生"""
        with self.get_session() as session:
            student = session.query(Student).filter(Student.id == pk).first()
            if student is None:
                return None
            return {
                'id': student.id,
                'student_id': student.student_id,
                'name': student.name,
                'class_name': student.class_name,
                'face_image_path': student.face_image_path
            }

    def get_all_students(self) -> List[Dict]:
        """获取所有学生（按学号自然排序）"""
        with self.get_session() as session:
            students = session.query(Student).all()
            result = [{
                'id': s.id,
                'student_id': s.student_id,
                'name': s.name,
                'class_name': s.class_name,
                'face_image_path': s.face_image_path,
                'created_at': s.created_at
            } for s in students]
            result.sort(key=lambda s: _natural_key(s['student_id']))
            return result

    def update_student(self, student_id: str, **kwargs) -> bool:
        """更新学生信息"""
        with self.get_session() as session:
            student = session.query(Student).filter(Student.student_id == student_id).first()
            if student is None:
                return False

            if 'name' in kwargs:
                student.name = kwargs['name']
            if 'class_name' in kwargs:
                student.class_name = kwargs['class_name']
            if 'face_encoding' in kwargs:
                student.face_encoding = encoding_to_blob(kwargs['face_encoding'])
            if 'face_image_path' in kwargs:
                student.face_image_path = kwargs['face_image_path']

            return True

    def delete_student(self, student_id: str) -> bool:
        """删除学生（同时删除相关考勤记录）"""
        with self.get_session() as session:
            student = session.query(Student).filter(Student.student_id == student_id).first()
            if student is None:
                return False

            # 先删除该学生的所有考勤记录
            student_db_id = student.id
            session.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_db_id).delete()

            # 再删除学生
            session.delete(student)
            return True

    def get_all_face_encodings(self, class_name: str = None) -> Tuple[List[np.ndarray], List[str], List[str]]:
        """
        获取所有学生的人脸特征和姓名（用于人脸匹配），可按班级过滤

        Returns:
            (encodings, names, student_ids): 特征列表、姓名列表、学号列表
        """
        with self.get_session() as session:
            q = session.query(Student).filter(Student.face_encoding.isnot(None))
            if class_name:
                q = q.filter(Student.class_name == class_name)
            students = q.all()

            encodings = []
            names = []
            student_ids = []

            for s in students:
                encoding = blob_to_encoding(s.face_encoding)
                if encoding is not None:
                    encodings.append(encoding)
                    names.append(s.name)
                    student_ids.append(s.student_id)

            return encodings, names, student_ids

    # ==================== 课程相关操作 ====================

    def add_course(self, course_code: str, course_name: str,
                   teacher_name: str = None,
                   start_time: str = None,
                   end_time: str = None) -> Dict:
        """添加课程"""
        with self.get_session() as session:
            course = Course(
                course_code=course_code,
                course_name=course_name,
                teacher_name=teacher_name,
                start_time=start_time,
                end_time=end_time
            )
            session.add(course)
            session.flush()
            return {
                'id': course.id,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'teacher_name': course.teacher_name
            }

    def get_all_courses(self) -> List[Dict]:
        """获取所有课程"""
        with self.get_session() as session:
            courses = session.query(Course).all()
            return [{
                'id': c.id,
                'course_code': c.course_code,
                'course_name': c.course_name,
                'teacher_name': c.teacher_name,
                'start_time': c.start_time,
                'end_time': c.end_time
            } for c in courses]

    def get_course(self, course_id: int) -> Optional[Dict]:
        """获取单个课程"""
        with self.get_session() as session:
            course = session.query(Course).filter(Course.id == course_id).first()
            if course is None:
                return None
            return {
                'id': course.id,
                'course_code': course.course_code,
                'course_name': course.course_name,
                'teacher_name': course.teacher_name,
                'start_time': course.start_time,
                'end_time': course.end_time
            }

    def delete_course(self, course_id: int) -> bool:
        """删除课程"""
        with self.get_session() as session:
            course = session.query(Course).filter(Course.id == course_id).first()
            if course is None:
                return False
            session.delete(course)
            return True

    def update_course(self, course_id: int, **kwargs) -> bool:
        """更新课程信息"""
        with self.get_session() as session:
            course = session.query(Course).filter(Course.id == course_id).first()
            if course is None:
                return False
            if 'course_code' in kwargs:
                course.course_code = kwargs['course_code']
            if 'course_name' in kwargs:
                course.course_name = kwargs['course_name']
            if 'teacher_name' in kwargs:
                course.teacher_name = kwargs['teacher_name']
            if 'start_time' in kwargs:
                course.start_time = kwargs['start_time']
            if 'end_time' in kwargs:
                course.end_time = kwargs['end_time']
            return True

    # ==================== 考勤记录相关操作 ====================

    def add_attendance_record(self, student_id: int, course_id: int = None,
                               status: str = 'normal', confidence: float = None,
                               remark: str = None) -> Dict:
        """添加考勤记录"""
        with self.get_session() as session:
            record = AttendanceRecord(
                student_id=student_id,
                course_id=course_id,
                status=status,
                confidence=confidence,
                remark=remark
            )
            session.add(record)
            session.flush()
            return {
                'id': record.id,
                'student_id': record.student_id,
                'course_id': record.course_id,
                'check_time': record.check_time,
                'status': record.status,
                'confidence': record.confidence
            }

    def get_attendance_records(self, course_id: int = None, date: date = None,
                                student_id: int = None, limit: int = None) -> List[Dict]:
        """
        查询考勤记录

        Args:
            course_id: 课程ID过滤
            date: 日期过滤
            student_id: 学生ID过滤
            limit: 返回记录数量限制，None表示不限制
        """
        with self.get_session() as session:
            query = session.query(AttendanceRecord, Student, Course).join(
                Student, AttendanceRecord.student_id == Student.id
            ).outerjoin(
                Course, AttendanceRecord.course_id == Course.id
            )

            if course_id is not None:
                query = query.filter(AttendanceRecord.course_id == course_id)
            if date is not None:
                # 使用与导出一致的日期范围筛选方式
                start_datetime = datetime.combine(date, datetime.min.time())
                end_datetime = datetime.combine(date, datetime.max.time())
                query = query.filter(AttendanceRecord.check_time >= start_datetime)
                query = query.filter(AttendanceRecord.check_time <= end_datetime)
            if student_id is not None:
                query = query.filter(AttendanceRecord.student_id == student_id)

            query = query.order_by(AttendanceRecord.check_time.desc())
            if limit is not None and limit > 0:
                query = query.limit(limit)

            results = query.all()

            records = []
            for record, student, course in results:
                records.append({
                    'id': record.id,
                    'student_id': record.student_id,
                    'student_name': student.name if student else None,
                    'student_no': student.student_id if student else None,
                    'student_class': student.class_name if student else None,
                    'course_id': record.course_id,
                    'course_name': course.course_name if course else None,
                    'check_time': record.check_time,
                    'status': record.status,
                    'confidence': record.confidence,
                    'remark': record.remark
                })

            return records

    def get_today_records(self, course_id: int = None) -> List[Dict]:
        """获取今日考勤记录"""
        return self.get_attendance_records(course_id=course_id, date=date.today())

    def check_today_attendance(self, student_id: int, course_id: int = None) -> bool:
        """检查学生今天是否已打卡"""
        with self.get_session() as session:
            # 使用与其他方法一致的日期范围筛选
            today = date.today()
            start_datetime = datetime.combine(today, datetime.min.time())
            end_datetime = datetime.combine(today, datetime.max.time())
            query = session.query(AttendanceRecord).filter(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.check_time >= start_datetime,
                AttendanceRecord.check_time <= end_datetime
            )
            if course_id is not None:
                query = query.filter(AttendanceRecord.course_id == course_id)

            return query.first() is not None

    def export_attendance_records(self, course_id: int = None,
                                   start_date: date = None,
                                   end_date: date = None) -> List[Dict]:
        """
        导出考勤记录

        Args:
            course_id: 课程ID过滤
            start_date: 开始日期
            end_date: 结束日期
        """
        with self.get_session() as session:
            query = session.query(AttendanceRecord, Student, Course).join(
                Student, AttendanceRecord.student_id == Student.id
            ).outerjoin(
                Course, AttendanceRecord.course_id == Course.id
            )

            if course_id is not None:
                query = query.filter(AttendanceRecord.course_id == course_id)
            if start_date is not None:
                # 将开始日期转换为当天的 00:00:00
                start_datetime = datetime.combine(start_date, datetime.min.time())
                query = query.filter(AttendanceRecord.check_time >= start_datetime)
            if end_date is not None:
                # 将结束日期转换为当天的 23:59:59，确保包含当天所有记录
                end_datetime = datetime.combine(end_date, datetime.max.time())
                query = query.filter(AttendanceRecord.check_time <= end_datetime)

            query = query.order_by(AttendanceRecord.check_time.desc())
            results = query.all()

            records = []
            for record, student, course in results:
                records.append({
                    '学号': student.student_id if student else '',
                    '姓名': student.name if student else '',
                    '班级': student.class_name if student else '',
                    '课程': course.course_name if course else '',
                    '打卡时间': record.check_time.strftime('%Y-%m-%d %H:%M:%S') if record.check_time else '',
                    '状态': '正常' if record.status == 'normal' else ('迟到' if record.status == 'late' else '缺勤'),
                    '置信度': f'{record.confidence:.2%}' if record.confidence else '',
                    '备注': record.remark or ''
                })

            return records

    def clear_attendance_records(self, course_id: int = None, before_date: date = None) -> int:
        """清理考勤记录"""
        with self.get_session() as session:
            query = session.query(AttendanceRecord)
            if course_id is not None:
                query = query.filter(AttendanceRecord.course_id == course_id)
            if before_date is not None:
                query = query.filter(AttendanceRecord.check_time < before_date)

            count = query.count()
            query.delete()
            return count

    def update_attendance_record(self, record_id: int, **kwargs) -> bool:
        """更新考勤记录"""
        with self.get_session() as session:
            record = session.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
            if record is None:
                return False
            if 'status' in kwargs:
                record.status = kwargs['status']
            if 'remark' in kwargs:
                record.remark = kwargs['remark']
            return True

    def delete_attendance_record(self, record_id: int) -> bool:
        """删除单条考勤记录"""
        with self.get_session() as session:
            record = session.query(AttendanceRecord).filter(AttendanceRecord.id == record_id).first()
            if record is None:
                return False
            session.delete(record)
            return True

    # ==================== 用户相关操作 ====================

    def add_user(self, username: str, password: str, role: str = 'teacher') -> Dict:
        """
        添加用户（自动对密码进行哈希处理）

        Args:
            username: 用户名
            password: 明文密码
            role: 角色（teacher/admin）

        Returns:
            用户信息字典
        """
        from utils.security import hash_password

        # 对密码进行哈希处理
        hashed_password = hash_password(password)

        with self.get_session() as session:
            user = User(username=username, password_hash=hashed_password, role=role)
            session.add(user)
            session.flush()
            return {'id': user.id, 'username': user.username, 'role': user.role}

    def get_user(self, username: str) -> Optional[Dict]:
        """获取用户"""
        with self.get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if user is None:
                return None
            return {
                'id': user.id,
                'username': user.username,
                'password_hash': user.password_hash,
                'role': user.role
            }

    def verify_user(self, username: str, password: str) -> Optional[Dict]:
        """
        验证用户登录

        Args:
            username: 用户名
            password: 明文密码

        Returns:
            验证成功返回用户信息，失败返回 None
        """
        from utils.security import verify_password

        user = self.get_user(username)
        if user is None:
            return None

        # 使用 bcrypt 验证密码
        if verify_password(password, user['password_hash']):
            return user
        return None