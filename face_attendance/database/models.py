"""
数据库模型定义
使用 SQLAlchemy ORM
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, LargeBinary, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Student(Base):
    """学生表"""
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String(20), unique=True, nullable=False, comment='学号')
    name = Column(String(50), nullable=False, comment='姓名')
    class_name = Column(String(50), comment='班级')
    face_encoding = Column(LargeBinary, comment='人脸特征向量(512维float32序列化)')
    face_image_path = Column(String(255), comment='人脸图片路径')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')

    # 关联考勤记录
    attendance_records = relationship("AttendanceRecord", back_populates="student")

    def __repr__(self):
        return f"<Student(student_id='{self.student_id}', name='{self.name}')>"


class Course(Base):
    """课程表"""
    __tablename__ = 'courses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_code = Column(String(20), unique=True, comment='课程代码')
    course_name = Column(String(100), comment='课程名')
    teacher_name = Column(String(50), comment='教师名')
    start_time = Column(String(10), comment='上课时间 如: 08:00')
    end_time = Column(String(10), comment='下课时间 如: 09:40')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    # 关联考勤记录
    attendance_records = relationship("AttendanceRecord", back_populates="course")

    def __repr__(self):
        return f"<Course(course_code='{self.course_code}', course_name='{self.course_name}')>"


class AttendanceRecord(Base):
    """考勤记录表"""
    __tablename__ = 'attendance_records'

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey('students.id'), nullable=False, comment='学生ID')
    course_id = Column(Integer, ForeignKey('courses.id'), comment='课程ID')
    check_time = Column(DateTime, default=datetime.now, nullable=False, comment='打卡时间')
    status = Column(String(20), default='normal', comment='状态: normal/late/absent')
    confidence = Column(Float, comment='识别置信度')
    remark = Column(Text, comment='备注')

    __table_args__ = (
        Index('idx_attendance_student_time', 'student_id', 'check_time'),
        Index('idx_attendance_course', 'course_id'),
        Index('idx_attendance_check_time', 'check_time'),
        Index('idx_attendance_status', 'status'),
    )

    # 关联
    student = relationship("Student", back_populates="attendance_records")
    course = relationship("Course", back_populates="attendance_records")

    def __repr__(self):
        return f"<AttendanceRecord(student_id={self.student_id}, check_time='{self.check_time}', status='{self.status}')>"


class User(Base):
    """用户表（用于登录认证）"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    password_hash = Column(String(255), comment='密码哈希')
    role = Column(String(20), default='teacher', comment='角色: admin/teacher')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"