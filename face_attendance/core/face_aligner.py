"""
人脸对齐模块
基于5点关键点的人脸对齐、姿态估计和质量评估

5点关键点: 左眼、右眼、鼻尖、左嘴角、右嘴角

核心作用:
1. 仿射对齐 — 将人脸对齐到标准模板，消除头部旋转/偏转影响
2. 姿态估计 — 从关键点推算 roll/yaw，过滤非正面脸
3. 质量评估 — 综合姿态、清晰度、亮度、检测置信度给出 0~1 评分
"""
import cv2
import numpy as np
from typing import Dict, Optional, Tuple

# ArcFace 标准模板坐标 (112×112 输入)
ARCFACE_TEMPLATE = np.array([
    [38.2946, 51.6963],   # 左眼中心
    [73.5318, 51.5014],   # 右眼中心
    [56.0252, 71.7366],   # 鼻尖
    [41.5493, 92.3655],   # 左嘴角
    [70.7299, 92.2041],   # 右嘴角
], dtype=np.float32)


class FaceAligner:
    """
    基于5点关键点的人脸对齐器

    InsightFace 内部已用 5 点做对齐，此模块将关键点信息暴露出来用于:
    - 姿态估计: 识别侧脸/仰头/低头并过滤
    - 质量评分: 综合姿态+清晰度+亮度，只保留高质量人脸用于注册
    - 仿射对齐: 显式对齐到标准模板（用于调试/可视化）
    """

    # 姿态阈值
    MAX_ROLL_DEG = 20          # 最大头部偏转角(度)
    MAX_YAW_DEVIATION = 0.4    # 最大偏航比偏差 |ratio - 1.0|
    MIN_EYE_DISTANCE = 30      # 最小两眼间距(像素，原图尺度)

    @staticmethod
    def align_face(image: np.ndarray, landmarks: np.ndarray,
                   output_size: Tuple[int, int] = (112, 112)) -> Optional[np.ndarray]:
        """
        使用5点关键点进行仿射对齐

        将检测到的关键点映射到 ArcFace 标准模板坐标，
        通过仿射变换矫正头部偏转和尺度差异

        Args:
            image: BGR 格式原始图像
            landmarks: (5, 2) 关键点坐标 [[x,y], ...]
            output_size: 输出图像尺寸，默认 112x112 (ArcFace 标准)

        Returns:
            对齐后的 112x112 人脸图像，失败返回 None
        """
        if landmarks is None or len(landmarks) < 5:
            return None

        src_pts = np.array(landmarks[:5], dtype=np.float32)
        M, _ = cv2.estimateAffinePartial2D(src_pts, ARCFACE_TEMPLATE)
        if M is None:
            return None

        aligned = cv2.warpAffine(image, M, output_size, borderValue=0.0)
        return aligned

    @staticmethod
    def estimate_pose(landmarks: np.ndarray) -> Dict:
        """
        从5点关键点估计人脸姿态

        利用关键点几何关系推算:
        - roll: 两眼连线与水平线的夹角 → 头部侧倾
        - yaw: 两眼到鼻子的水平距离比 → 头部左右偏转
        - frontal_score: 正面程度综合评分 0~1

        Args:
            landmarks: (5, 2) 关键点坐标

        Returns:
            姿态字典:
              - roll: 头部偏转角(度)
              - yaw: 偏航角度估计(度)
              - yaw_ratio: 左右距离比 (1.0=完美正面)
              - eye_distance: 两眼间距(像素)
              - is_frontal: 是否正面
              - frontal_score: 正面评分 0~1
        """
        if landmarks is None or len(landmarks) < 5:
            return {'roll': 0, 'yaw': 0, 'yaw_ratio': 1.0,
                    'eye_distance': 0, 'is_frontal': False, 'frontal_score': 0.0}

        pts = np.array(landmarks[:5], dtype=np.float64)
        left_eye, right_eye = pts[0], pts[1]
        nose = pts[2]

        # Roll: 两眼连线与水平线夹角
        dx = right_eye[0] - left_eye[0]
        dy = right_eye[1] - left_eye[1]
        roll = np.degrees(np.arctan2(dy, dx))

        # Yaw: 两眼到鼻子的水平距离比
        left_eye_to_nose = nose[0] - left_eye[0]
        right_eye_to_nose = right_eye[0] - nose[0]
        yaw_ratio = left_eye_to_nose / (right_eye_to_nose + 1e-6)
        yaw = np.degrees(np.arctan2(abs(yaw_ratio - 1.0), 1.0)) * 2

        # 两眼间距
        eye_distance = float(np.linalg.norm(right_eye - left_eye))

        # 是否正面
        is_frontal = (abs(roll) < FaceAligner.MAX_ROLL_DEG and
                      abs(yaw_ratio - 1.0) < FaceAligner.MAX_YAW_DEVIATION and
                      eye_distance >= FaceAligner.MIN_EYE_DISTANCE)

        # 正面评分 (0~1, 各因子加权)
        roll_score = max(0.0, 1.0 - abs(roll) / 45.0)
        yaw_score = max(0.0, 1.0 - abs(yaw_ratio - 1.0) / 0.8)
        size_score = min(1.0, eye_distance / 60.0)
        frontal_score = roll_score * 0.4 + yaw_score * 0.4 + size_score * 0.2

        return {
            'roll': float(roll),
            'yaw': float(yaw),
            'yaw_ratio': float(yaw_ratio),
            'eye_distance': eye_distance,
            'is_frontal': is_frontal,
            'frontal_score': float(frontal_score),
        }

    @staticmethod
    def assess_quality(image: np.ndarray, landmarks: np.ndarray,
                       det_score: float = 0.0,
                       min_quality: float = 0.25) -> Dict:
        """
        综合评估人脸质量 (0~1)

        评分维度:
        - 姿态 (40%): 正面程度，侧脸大幅扣分
        - 清晰度 (30%): 拉普拉斯方差，模糊脸扣分
        - 检测置信度 (15%): SCRFD 检测分数
        - 亮度 (15%): 灰度均值，过暗/过亮扣分

        Args:
            image: 人脸区域图像 (BGR)
            landmarks: (5, 2) 关键点坐标
            det_score: SCRFD 检测置信度

        Returns:
            质量字典:
              - total_score: 综合质量 0~1
              - pose: 姿态信息
              - sharpness: 清晰度 0~1
              - brightness: 亮度 0~1
              - is_acceptable: >= 0.4 可接受
              - is_good: >= 0.6 良好
              - reject_reason: 拒绝原因 (None 表示不拒绝)
        """
        pose = FaceAligner.estimate_pose(landmarks)

        sharpness = 0.5
        brightness = 0.5
        if image is not None and image.size > 0 and image.shape[0] >= 30:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness = min(laplacian_var / 500.0, 1.0)
            brightness = min(gray.mean() / 200.0, 1.0)

        total_score = (pose['frontal_score'] * 0.4 +
                       sharpness * 0.3 +
                       det_score * 0.15 +
                       brightness * 0.15)

        # 拒绝原因
        reject_reason = None
        if not pose['is_frontal']:
            if abs(pose['roll']) >= FaceAligner.MAX_ROLL_DEG:
                reject_reason = f"头部偏转过大({pose['roll']:.1f}°)"
            elif abs(pose['yaw_ratio'] - 1.0) >= FaceAligner.MAX_YAW_DEVIATION:
                reject_reason = f"非正面脸(yaw_ratio={pose['yaw_ratio']:.2f})"
            else:
                reject_reason = "人脸过小"
        elif sharpness < 0.2:
            reject_reason = f"图像模糊(清晰度={sharpness:.2f})"
        elif brightness < 0.15 or brightness > 0.95:
            reject_reason = f"光线不佳(亮度={brightness:.2f})"

        return {
            'total_score': float(total_score),
            'pose': pose,
            'sharpness': float(sharpness),
            'brightness': float(brightness),
            'det_score': float(det_score),
            'is_acceptable': total_score >= min_quality,
            'is_good': total_score >= 0.6,
            'reject_reason': reject_reason,
        }
