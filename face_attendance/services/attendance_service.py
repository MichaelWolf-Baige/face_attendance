"""
考勤服务
核心业务逻辑：人脸识别考勤流程
优化：统一检测+编码流水线，预计算匹配矩阵，时序跟踪+投票
"""
import os
import time
import threading
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Callable
from collections import Counter
import numpy as np

from database.db_manager import DatabaseManager
import config
from utils.logger import get_logger

logger = get_logger(__name__)


class SimpleTracker:
    """
    基于 IoU 的简单人脸跟踪器 + 投票机制

    作用：
    - 通过 IoU 匹配关联连续帧中的同一人脸
    - 用滑动窗口投票平滑识别结果，消除单帧误识别闪烁
    - 跟踪丢失后自动清除
    """

    def __init__(self, max_lost: int = 3, iou_threshold: float = 0.3, vote_window: int = 3):
        self.tracks = {}  # track_id -> track dict
        self.next_id = 0
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold
        self.vote_window = vote_window

    def _iou(self, box1, box2):
        """计算两个 (left, top, width, height) 框的 IoU"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[0] + box1[2], box2[0] + box2[2])
        y2 = min(box1[1] + box1[3], box2[1] + box2[3])

        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = box1[2] * box1[3]
        area2 = box2[2] * box2[3]
        union = area1 + area2 - inter

        return inter / union if union > 0 else 0.0

    def update(self, detections: List[Dict]) -> List[Dict]:
        """
        用当前帧检测结果更新跟踪状态

        Args:
            detections: 每项包含 'bbox'(left,top,w,h), 'name', 'confidence', 'student_id'

        Returns:
            经过投票平滑后的稳定识别结果
        """
        matched_track_ids = set()
        matched_det_ids = set()

        # 贪心匹配：每个检测框与 IoU 最大的已有 track 配对
        for det_idx, det in enumerate(detections):
            best_iou = self.iou_threshold
            best_track_id = None

            for track_id, track in self.tracks.items():
                if track_id in matched_track_ids:
                    continue
                iou = self._iou(det['bbox'], track['bbox'])
                if iou > best_iou:
                    best_iou = iou
                    best_track_id = track_id

            if best_track_id is not None:
                track = self.tracks[best_track_id]
                track['bbox'] = det['bbox']
                track['votes'].append(det.get('name'))
                if len(track['votes']) > self.vote_window:
                    track['votes'] = track['votes'][-self.vote_window:]
                track['lost_count'] = 0
                track['last_detection'] = det
                matched_track_ids.add(best_track_id)
                matched_det_ids.add(det_idx)

        # 未匹配的检测 → 新建 track
        for det_idx, det in enumerate(detections):
            if det_idx not in matched_det_ids:
                self.tracks[self.next_id] = {
                    'bbox': det['bbox'],
                    'votes': [det.get('name')],
                    'lost_count': 0,
                    'last_detection': det,
                }
                self.next_id += 1

        # 未匹配的 track → 增加 lost 计数
        for track_id in list(self.tracks.keys()):
            if track_id not in matched_track_ids:
                self.tracks[track_id]['lost_count'] += 1

        # 清除丢失太久的 track
        for track_id in list(self.tracks.keys()):
            if self.tracks[track_id]['lost_count'] > self.max_lost:
                del self.tracks[track_id]

        # 返回投票平滑后的结果
        confirmed = []
        for track_id, track in self.tracks.items():
            votes = track['votes']
            if not votes:
                continue

            counter = Counter(votes)
            most_common_name, count = counter.most_common(1)[0]

            # 投票过半才覆盖，否则用最新检测结果
            if count >= max(2, len(votes) * 0.5):
                confirmed_name = most_common_name
            else:
                confirmed_name = track['last_detection'].get('name')

            det = track['last_detection'].copy()
            det['name'] = confirmed_name
            det['track_id'] = track_id
            confirmed.append(det)

        return confirmed

    def reset(self):
        self.tracks.clear()
        self.next_id = 0


class AttendanceService:
    """考勤服务 - 优化版（统一流水线 + 跟踪器）"""

    def __init__(self, db_manager, detector, encoder, matcher):
        self.db = db_manager

        self.detector = detector
        self.encoder = encoder
        self.matcher = matcher

        # 人脸数据库缓存（预计算矩阵）
        self._cache_lock = threading.RLock()
        self._face_names = []
        self._face_student_ids = []

        # 打卡冷却
        self._cooldown_lock = threading.Lock()
        self._last_check_time = {}
        self._cooldown = getattr(config, 'ATTENDANCE_COOLDOWN', 10)

        # 时序跟踪器
        self._tracker = SimpleTracker(
            max_lost=3,
            iou_threshold=0.3,
            vote_window=3
        )

    def refresh_face_database(self, class_name: str = None):
        """刷新人脸数据库缓存 — 预计算归一化矩阵，可按班级过滤"""
        with self._cache_lock:
            encodings, names, student_ids = self.db.get_all_face_encodings(class_name=class_name)
            self._face_names = names
            self._face_student_ids = student_ids
            self.matcher.update_database(encodings, names, student_ids)

        logger.info(f"人脸库已刷新: {len(names)} 人 (班级: {class_name or '全部'}), 矩阵预计算完成")

    def process_frame(self, frame: np.ndarray, course_id: int = None,
                      late_threshold_minutes: int = 15) -> List[Dict]:
        """
        处理一帧图像，检测人脸并识别 — 优化版

        使用 detect_and_encode() 一次调用完成检测+编码，避免双重 model.get()
        使用预计算矩阵做匹配，使用跟踪器平滑结果

        Args:
            frame: BGR格式的图像帧
            course_id: 当前课程ID
            late_threshold_minutes: 迟到阈值（分钟）

        Returns:
            识别结果列表
        """
        # 一次调用完成检测+编码（核心优化：省掉一次 SCRFD+ArcFace 前向传播）
        detections = self.encoder.detect_and_encode(
            frame,
            max_num=10,
            resize_scale=self.detector.resize_scale
        )

        if not detections:
            # 无人脸时也要更新跟踪器（让丢失的 track 递增 lost_count）
            self._tracker.update([])
            return []

        # 批量匹配（一次矩阵乘法完成所有人脸的匹配）
        encodings = [d['encoding'] for d in detections]
        match_results = self.matcher.match_multiple_batch(encodings)

        # 构建检测结果
        raw_detections = []
        for det, (name, confidence, match_idx) in zip(detections, match_results):
            top, right, bottom, left = det['location']
            student_id = None

            # 通过 matcher 返回的 index 查找 student_id（修复重名 bug）
            if match_idx is not None and match_idx < len(self._face_student_ids):
                student_id = self._face_student_ids[match_idx]

            raw_detections.append({
                'location': det['location'],
                'name': name,
                '_original_name': name,
                'student_id': student_id,
                'confidence': confidence,
                'bbox': (left, top, right - left, bottom - top),
                'det_score': det.get('det_score', 0),
            })

        # 时序跟踪 + 投票平滑
        tracked_detections = self._tracker.update(raw_detections)

        # 跟踪器可能修正了 name，需要同步修正 student_id
        results = []
        for det in tracked_detections:
            name = det.get('name')
            student_id = det.get('student_id')

            # 如果跟踪器修改了 name（投票修正），需要重新查找 student_id
            if name and name != det.get('_original_name', name):
                # 在人脸库中查找修正后的 name 对应的 student_id
                if name in self._face_names:
                    idx = self._face_names.index(name)
                    student_id = self._face_student_ids[idx]

            results.append({
                'location': det['location'],
                'name': name,
                'student_id': student_id,
                'confidence': det['confidence'],
                'bbox': det['bbox'],
                'track_id': det.get('track_id'),
            })

        return results

    def check_in(self, student_id: str, course_id: int = None,
                 confidence: float = None, late_threshold_minutes: int = 15) -> Tuple[bool, str, str]:
        """
        学生打卡 - 线程安全

        Args:
            student_id: 学号
            course_id: 课程ID
            confidence: 识别置信度
            late_threshold_minutes: 迟到阈值（分钟），默认15分钟

        Returns:
            (success, status, message): 是否成功、状态、消息
        """
        current_time = time.time()
        with self._cooldown_lock:
            if student_id in self._last_check_time:
                if current_time - self._last_check_time[student_id] < self._cooldown:
                    remaining = int(self._cooldown - (current_time - self._last_check_time[student_id]))
                    return False, 'cooldown', f"请等待 {remaining} 秒后再打卡"

        student = self.db.get_student(student_id)
        if not student:
            return False, 'error', "学生不存在"

        if self.db.check_today_attendance(student['id'], course_id):
            return False, 'duplicate', f"{student['name']} 今天已打卡"

        now = datetime.now()
        status = 'normal'

        if course_id:
            course = self.db.get_course(course_id)
            if course and course.get('start_time'):
                try:
                    start_hour, start_min = map(int, course['start_time'].split(':'))
                    class_start = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
                    late_threshold = class_start.timestamp() + late_threshold_minutes * 60
                    if now.timestamp() > late_threshold:
                        status = 'late'
                except ValueError as e:
                    logger.warning(f"课程时间格式错误: {course.get('start_time')}, 错误: {e}")

        try:
            self.db.add_attendance_record(
                student_id=student['id'],
                course_id=course_id,
                status=status,
                confidence=confidence
            )
            with self._cooldown_lock:
                self._last_check_time[student_id] = current_time

            status_text = '正常' if status == 'normal' else '迟到'
            return True, status, f"{student['name']} 打卡成功 ({status_text})"
        except Exception as e:
            return False, 'error', f"打卡失败: {str(e)}"

    def manual_makeup_check_in(self, student_id: str, course_id: int = None,
                               status: str = 'normal', remark: str = None) -> Tuple[bool, str]:
        """
        手动补签 - 绕过人脸识别和冷却时间，教师直接标记学生出勤

        Args:
            student_id: 学号
            course_id: 课程ID
            status: 考勤状态 (normal/late)
            remark: 备注（自动添加"手动补签"前缀）

        Returns:
            (success, message)
        """
        student = self.db.get_student(student_id)
        if not student:
            return False, f"学号 {student_id} 不存在"

        if self.db.check_today_attendance(student['id'], course_id):
            return False, f"{student['name']} 今天已打卡，无需补签"

        full_remark = f"手动补签" if not remark else f"手动补签 - {remark}"

        try:
            self.db.add_attendance_record(
                student_id=student['id'],
                course_id=course_id,
                status=status,
                confidence=None,
                remark=full_remark
            )
            status_text = '正常' if status == 'normal' else '迟到'
            return True, f"{student['name']} 补签成功 ({status_text})"
        except Exception as e:
            return False, f"补签失败: {str(e)}"

    def get_unchecked_students(self, course_id: int = None, class_name: str = None) -> List[Dict]:
        """
        获取今日未打卡的学生列表

        Args:
            course_id: 课程ID
            class_name: 班级名（可选过滤）

        Returns:
            未打卡学生列表
        """
        all_students = self.db.get_all_students()
        if class_name:
            all_students = [s for s in all_students if s.get('class_name') == class_name]

        unchecked = []
        for s in all_students:
            if not self.db.check_today_attendance(s['id'], course_id):
                unchecked.append(s)
        return unchecked

    def auto_check_in(self, frame: np.ndarray, course_id: int = None) -> List[Dict]:
        """
        自动处理一帧并打卡

        Args:
            frame: 图像帧
            course_id: 课程ID

        Returns:
            打卡结果列表
        """
        results = self.process_frame(frame, course_id)
        check_results = []

        for result in results:
            if result['student_id']:
                success, status, message = self.check_in(
                    result['student_id'],
                    course_id,
                    result['confidence']
                )
                result['check_success'] = success
                result['check_status'] = status
                result['check_message'] = message
                check_results.append(result)

        return check_results

    def get_today_records(self, course_id: int = None) -> List[Dict]:
        """获取今日考勤记录"""
        return self.db.get_today_records(course_id)

    def get_attendance_records(self, course_id: int = None, date: date = None,
                                student_id: int = None) -> List[Dict]:
        """查询考勤记录"""
        return self.db.get_attendance_records(course_id, date, student_id)

    def export_records(self, course_id: int = None, start_date: date = None,
                       end_date: date = None) -> List[Dict]:
        """导出考勤记录"""
        return self.db.export_attendance_records(course_id, start_date, end_date)

    def get_statistics(self, course_id: int = None, date: date = None) -> Dict:
        """获取考勤统计"""
        records = self.get_attendance_records(course_id, date)

        total = len(records)
        normal = sum(1 for r in records if r['status'] == 'normal')
        late = sum(1 for r in records if r['status'] == 'late')
        absent = sum(1 for r in records if r['status'] == 'absent')

        return {
            'total': total,
            'normal': normal,
            'late': late,
            'absent': absent,
            'normal_rate': normal / total * 100 if total > 0 else 0
        }

    def set_cooldown(self, seconds: int):
        """设置打卡冷却时间"""
        self._cooldown = seconds

    def set_tolerance(self, tolerance: float):
        """设置人脸匹配阈值"""
        self.matcher.set_tolerance(tolerance)

    def update_attendance_record(self, record_id: int, **kwargs) -> bool:
        """更新考勤记录"""
        return self.db.update_attendance_record(record_id, **kwargs)

    def delete_attendance_record(self, record_id: int) -> bool:
        """删除考勤记录"""
        return self.db.delete_attendance_record(record_id)

    def reset_tracker(self):
        """重置跟踪器（切换场景时调用）"""
        self._tracker.reset()
