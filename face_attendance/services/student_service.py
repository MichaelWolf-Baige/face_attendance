"""
学生管理服务
优化: 使用5点关键点质量评估 + 质量加权编码 + 离群值剔除
"""
import os
import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple, Callable
from datetime import datetime

from core.face_encoder import FaceEncoder
from core.face_aligner import FaceAligner
from database.db_manager import DatabaseManager
import config


def _write_error_log(log_path: str, line: str):
    """追加写入错误日志（线程安全，每次打开即关闭）"""
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {line}\n")
    except Exception:
        pass


class StudentService:
    """学生管理服务"""

    def __init__(self, db_manager, detector, encoder):
        self.db = db_manager
        self.detector = detector
        self.encoder = encoder

    def add_student_with_encoding(self, student_id: str, name: str,
                                    class_name: str = None,
                                    encoding: np.ndarray = None) -> Tuple[bool, str]:
        """使用已有编码注册学生 (RegisterDialog 等 GUI 已提取编码)"""
        existing = self.db.get_student(student_id)
        if existing:
            return False, f"学号 {student_id} 已存在"
        try:
            self.db.add_student(
                student_id=student_id, name=name,
                class_name=class_name, face_encoding=encoding
            )
            return True, f"学生 {name} 注册成功"
        except Exception as e:
            return False, f"注册失败: {str(e)}"

    def register_student(self, student_id: str, name: str, class_name: str = None,
                         image_path: str = None, image: np.ndarray = None,
                         images: List[np.ndarray] = None) -> Tuple[bool, str]:
        """
        注册学生 — 使用5点关键点质量加权编码

        多张图片时:
        1. 每张图通过 detect_and_encode 获取编码+5点关键点+姿态+质量
        2. 过滤非正面脸、模糊脸
        3. 离群值剔除
        4. 质量加权平均生成更鲁棒的模板
        """
        existing = self.db.get_student(student_id)
        if existing:
            return False, f"学号 {student_id} 已存在"

        frames = self._collect_frames(image_path, image, images)
        if not frames:
            return False, "请提供有效的人脸图片"

        # 使用质量加权编码（集成5点关键点姿态估计+离群值剔除）
        avg_encoding = self.encoder.encode_with_quality(
            frames,
            resize_scale=getattr(config, 'FACE_REGISTRATION_RESIZE_SCALE', 0.75),
            min_quality=getattr(config, 'FACE_REGISTRATION_MIN_QUALITY', 0.25)
        )

        # 回退：如果质量加权编码失败，尝试简单平均编码
        if avg_encoding is None and getattr(config, 'FACE_REGISTRATION_FALLBACK', True):
            from utils.logger import get_logger
            get_logger(__name__).warning(f"质量加权编码失败，回退到简单平均编码 (学号={student_id})")
            avg_encoding = self.encoder.encode_average(frames)

        if avg_encoding is None:
            return False, f"未能从{len(frames)}张图片中提取有效人脸特征（质量不达标或未检测到人脸）"

        try:
            self.db.add_student(
                student_id=student_id,
                name=name,
                class_name=class_name,
                face_encoding=avg_encoding,
                face_image_path=image_path
            )
            return True, f"学生 {name} 注册成功"
        except Exception as e:
            return False, f"注册失败: {str(e)}"

    def _collect_frames(self, image_path=None, image=None, images=None) -> List[np.ndarray]:
        """收集并加载待处理的图像"""
        frames = []
        if images:
            frames = [img.copy() for img in images if img is not None]
        elif image is not None:
            frames = [image.copy()]
        elif image_path and os.path.exists(image_path):
            img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is not None:
                frames = [img]
        return frames

    def register_from_directory(self, dir_path: str,
                                class_name: str = None,
                                progress_callback: Callable[[int, int, str], None] = None,
                                cancel_check: Callable[[], bool] = None,
                                error_log_path: str = None) -> Tuple[int, List[str]]:
        """
        从目录批量注册学生 (支持嵌套子目录如train/test/val)

        支持中断续传: 已注册的学号自动跳过，中断后可重新运行
        """
        success_count = 0
        errors = []
        skipped = 0

        if not os.path.isdir(dir_path):
            return 0, ["目录不存在"]

        student_dirs = {}
        self._scan_student_dirs(dir_path, student_dirs)

        if not student_dirs:
            errors.append("未找到任何学生目录 (格式: 学号_姓名/)")
            return 0, errors

        total = len(student_dirs)
        current = 0

        for student_id, (name, dir_paths) in student_dirs.items():
            if cancel_check and cancel_check():
                errors.append(f"用户取消 (已处理 {current}/{total})")
                break

            current += 1
            if progress_callback:
                progress_callback(current, total, f"正在处理: {name} ({current}/{total})")

            if self.db.get_student(student_id):
                skipped += 1
                continue

            frames = []
            for d in dir_paths:
                try:
                    for f in os.listdir(d):
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                            img_path = os.path.join(d, f)
                            img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                            if img is not None:
                                frames.append(img)
                except OSError:
                    continue

            if not frames:
                msg = f"{name}: 无有效图片"
                errors.append(msg)
                if error_log_path:
                    _write_error_log(error_log_path, f"[跳过] {msg}")
                continue

            first_image_path = os.path.join(dir_paths[0], os.listdir(dir_paths[0])[0])
            success, msg = self.register_student(
                student_id, name,
                class_name=class_name,
                image_path=first_image_path,
                images=frames
            )
            if success:
                success_count += 1
            else:
                errors.append(f"{name}: {msg}")
                if error_log_path:
                    _write_error_log(error_log_path, f"[失败] {name}({student_id}): {msg}")

        if skipped > 0:
            errors.insert(0, f"跳过 {skipped} 名已注册学生")
        if cancel_check and cancel_check():
            errors.insert(0, "导入已被用户中断，已导入的数据安全保留。下次运行将自动跳过已导入的学生。")

        return success_count, errors

    def _scan_student_dirs(self, root: str, result: dict):
        """递归扫描学生目录"""
        try:
            for item in os.listdir(root):
                item_path = os.path.join(root, item)
                if not os.path.isdir(item_path):
                    continue

                if item.lower() in ('__pycache__', '.git', '__macosx'):
                    continue

                parts = item.split('_', 1)
                if len(parts) >= 2 and parts[0].strip().isdigit():
                    student_id = parts[0].strip()
                    name = parts[1].strip()
                    if student_id not in result:
                        result[student_id] = (name, [])
                    result[student_id][1].append(item_path)
                else:
                    self._scan_student_dirs(item_path, result)
        except OSError:
            pass

    def register_from_class_dir(self, class_dir: str, class_name: str,
                                progress_callback: Callable[[int, int, str], None] = None,
                                cancel_check: Callable[[], bool] = None,
                                error_log_path: str = None) -> Tuple[int, List[str]]:
        """
        从班级目录导入 (处理 train/test/val 结构)

        自动从班级名提取前缀（如 23人工智能1班 → 1-），
        加到学号前，保证跨班级学号唯一。

        支持中断续传: 已注册的学号自动跳过
        """
        import re
        # 从班级名提取数字前缀: "23人工智能1班" → "1"
        class_num = ''
        m = re.search(r'(\d+)班', class_name)
        if m:
            class_num = m.group(1) + '-'

        success_count = 0
        errors = []
        skipped = 0

        if not os.path.isdir(class_dir):
            return 0, ["班级目录不存在"]

        student_images = {}
        for subset in ['train', 'test', 'val']:
            subset_path = os.path.join(class_dir, subset)
            if not os.path.isdir(subset_path):
                continue

            try:
                for student_dir in os.listdir(subset_path):
                    student_path = os.path.join(subset_path, student_dir)
                    if not os.path.isdir(student_path):
                        continue

                    parts = student_dir.split('_', 1)
                    if len(parts) != 2 or not parts[0].strip().isdigit():
                        continue

                    student_id = class_num + parts[0].strip()
                    name = parts[1].strip()

                    if student_id not in student_images:
                        student_images[student_id] = (name, [])

                    for f in os.listdir(student_path):
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                            student_images[student_id][1].append(os.path.join(student_path, f))
            except OSError:
                continue

        total = len(student_images)
        current = 0

        for student_id, (name, img_paths) in student_images.items():
            if cancel_check and cancel_check():
                errors.append(f"用户取消 (已处理 {current}/{total})")
                break

            current += 1
            if progress_callback:
                progress_callback(current, total, f"正在处理: {name} ({current}/{total})")

            if self.db.get_student(student_id):
                skipped += 1
                continue

            if not img_paths:
                msg = f"{name}: 无图片"
                errors.append(msg)
                if error_log_path:
                    _write_error_log(error_log_path, f"[跳过] {msg}")
                continue

            frames = []
            for img_path in img_paths:
                img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                if img is not None:
                    frames.append(img)

            if not frames:
                msg = f"{name}: 无法读取图片"
                errors.append(msg)
                if error_log_path:
                    _write_error_log(error_log_path, f"[失败] {name}({student_id}): {msg}")
                continue

            success, msg = self.register_student(
                student_id, name,
                class_name=class_name,
                image_path=img_paths[0],
                images=frames
            )
            if success:
                success_count += 1
            else:
                errors.append(f"{name}: {msg}")
                if error_log_path:
                    _write_error_log(error_log_path, f"[失败] {name}({student_id}): {msg}")

        if skipped > 0:
            errors.insert(0, f"跳过 {skipped} 名已注册学生")
        if cancel_check and cancel_check():
            errors.insert(0, "导入已被用户中断，已导入的数据安全保留。下次运行将自动跳过已导入的学生。")

        return success_count, errors

    def get_student(self, student_id: str) -> Optional[Dict]:
        """获取学生信息"""
        return self.db.get_student(student_id)

    def get_all_students(self) -> List[Dict]:
        """获取所有学生"""
        return self.db.get_all_students()

    def update_student(self, student_id: str, **kwargs) -> bool:
        """更新学生信息"""
        return self.db.update_student(student_id, **kwargs)

    def delete_student(self, student_id: str) -> Tuple[bool, str]:
        """删除学生"""
        success = self.db.delete_student(student_id)
        if success:
            return True, f"学生 {student_id} 已删除"
        return False, f"学生 {student_id} 不存在"

    def get_face_database(self) -> Tuple[List[np.ndarray], List[str], List[str]]:
        """获取人脸数据库（用于识别）"""
        return self.db.get_all_face_encodings()

    def update_face_encoding(self, student_id: str, image: np.ndarray) -> Tuple[bool, str]:
        """更新学生的人脸特征 — 使用5点关键点质量检查"""
        dets = self.encoder.detect_and_encode(image, max_num=5, resize_scale=1.0)
        if not dets:
            return False, "未检测到人脸"
        if len(dets) > 1:
            return False, "检测到多张人脸"

        det = dets[0]
        quality = det['quality']
        min_q = getattr(config, 'FACE_REGISTRATION_MIN_QUALITY', 0.25)
        if quality['total_score'] < min_q:
            reason = quality.get('reject_reason', '质量不达标')
            return False, f"人脸质量不达标: {reason}"

        encoding = det['encoding']
        if encoding is None:
            return False, "特征提取失败"

        success = self.db.update_student(student_id, face_encoding=encoding)
        if success:
            return True, "人脸特征更新成功"
        return False, "更新失败"
