"""
人脸检测模块
使用 InsightFace SCRFD 模型进行人脸检测
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
import config

from .face_encoder import _get_face_model


class FaceDetector:
    """人脸检测类 (InsightFace SCRFD)"""

    def __init__(self, model: str = None, resize_scale: float = None):
        self.resize_scale = resize_scale if resize_scale is not None else config.FACE_ATTENDANCE_RESIZE_SCALE

    def detect(self, image: np.ndarray, resize_scale: float = None) -> List[Tuple[int, int, int, int]]:
        """
        检测图像中的人脸位置

        Args:
            image: BGR格式的numpy数组
            resize_scale: 临时覆盖缩放比例

        Returns:
            人脸位置列表，每个元素为 (top, right, bottom, left) — dlib兼容格式
        """
        if image is None or image.size == 0:
            return []

        scale = resize_scale if resize_scale is not None else self.resize_scale
        h, w = image.shape[:2]

        if scale != 1.0:
            small = cv2.resize(image, (int(w * scale), int(h * scale)))
        else:
            small = image

        model = _get_face_model()
        faces = model.get(small)

        locations = []
        for face in faces:
            x1, y1, x2, y2 = face.bbox.astype(int)
            if scale != 1.0:
                x1 = int(x1 / scale)
                y1 = int(y1 / scale)
                x2 = int(x2 / scale)
                y2 = int(y2 / scale)
            locations.append((y1, x2, y2, x1))  # → (top, right, bottom, left)

        return locations

    def detect_fast(self, image: np.ndarray, min_size: int = 80) -> List[Tuple[int, int, int, int]]:
        """
        快速检测（缩放图像加速）

        Returns:
            人脸位置列表 (top, right, bottom, left)
        """
        if image is None or image.size == 0:
            return []
        h, w = image.shape[:2]
        scale = min(1.0, 480.0 / max(h, w))
        return self.detect(image, resize_scale=scale)

    def detect_quality(self, image: np.ndarray) -> float:
        """
        评估人脸图像质量 (0.0~1.0)

        检测图像清晰度、对比度等指标
        """
        if image is None or image.size == 0 or image.shape[0] < 30 or image.shape[1] < 30:
            return 0.0

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharpness = min(laplacian_var / 500.0, 1.0)
        contrast = gray.std() / 128.0
        h, w = gray.shape
        size_score = min(min(h, w) / config.FACE_MIN_FACE_SIZE, 1.0)

        return float(sharpness * 0.4 + contrast * 0.2 + size_score * 0.4)

    def detect_with_details(self, image: np.ndarray) -> List[dict]:
        """检测人脸并返回详细信息（包含质量评分）— 修复缩放坐标"""
        scale = self.resize_scale
        h, w = image.shape[:2]

        if scale != 1.0:
            small = cv2.resize(image, (int(w * scale), int(h * scale)))
        else:
            small = image

        model = _get_face_model()
        faces = model.get(small)

        results = []
        for face in faces:
            x1, y1, x2, y2 = face.bbox.astype(int)
            # 坐标还原到原图尺度
            if scale != 1.0:
                x1 = int(x1 / scale)
                y1 = int(y1 / scale)
                x2 = int(x2 / scale)
                y2 = int(y2 / scale)

            top, right, bottom, left = y1, x2, y2, x1
            face_region = image[top:bottom, left:right]
            quality = self.detect_quality(face_region)
            results.append({
                'location': (top, right, bottom, left),
                'top': top,
                'right': right,
                'bottom': bottom,
                'left': left,
                'width': x2 - x1,
                'height': y2 - y1,
                'quality': quality,
                'det_score': float(face.det_score)
            })

        return results

    def draw_faces(self, image: np.ndarray,
                   face_locations: List[Tuple[int, int, int, int]],
                   color: Tuple[int, int, int] = (0, 255, 0),
                   thickness: int = 2) -> np.ndarray:
        """在图像上绘制人脸框"""
        result = image.copy()
        for top, right, bottom, left in face_locations:
            cv2.rectangle(result, (left, top), (right, bottom), color, thickness)
        return result
