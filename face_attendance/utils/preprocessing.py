"""
图像预处理模块
CLAHE 自适应直方图均衡化 + 降噪，提升不同光照条件下的识别鲁棒性

教室场景核心优化: 消除逆光、侧光、暗光对人脸特征的影响
"""
import cv2
import numpy as np
from typing import Tuple


def create_clahe(clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)):
    """创建 CLAHE 对象（可复用，避免重复创建）"""
    return cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)


# 模块级单例 CLAHE 对象
_clahe = None
_clahe_config = None


def _get_clahe(clip_limit=2.0, tile_size=(8, 8)):
    global _clahe, _clahe_config
    cfg = (clip_limit, tile_size)
    if _clahe is None or _clahe_config != cfg:
        _clahe = create_clahe(clip_limit, tile_size)
        _clahe_config = cfg
    return _clahe


def preprocess_face(image: np.ndarray,
                    clip_limit: float = 2.0,
                    tile_size: Tuple[int, int] = (8, 8),
                    denoise: bool = True) -> np.ndarray:
    """
    对整张图像做光照归一化预处理

    处理步骤:
    1. 转 LAB 色彩空间，在 L 通道上做 CLAHE
    2. 转回 BGR
    3. 可选: 轻度高斯降噪

    Args:
        image: BGR 格式图像
        clip_limit: CLAHE 对比度限制 (1.5~3.0, 教室推荐 2.0)
        tile_size: CLAHE 网格大小 (教室推荐 8x8)
        denoise: 是否降噪

    Returns:
        预处理后的 BGR 图像
    """
    if image is None or image.size == 0:
        return image

    clahe = _get_clahe(clip_limit, tile_size)

    # LAB 色彩空间: L 通道承载亮度信息
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_eq = clahe.apply(l)
    lab_eq = cv2.merge([l_eq, a, b])
    result = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)

    if denoise:
        result = cv2.bilateralFilter(result, 5, 20, 20)

    return result


def preprocess_face_region(face_image: np.ndarray,
                           clip_limit: float = 2.0,
                           tile_size: Tuple[int, int] = (6, 6)) -> np.ndarray:
    """
    对人脸区域做增强预处理（比全图预处理更激进）

    适用于注册阶段的单张人脸裁剪图。
    使用更小的 tile_size 更精细地均衡局部光照。

    Args:
        face_image: BGR 格式的人脸区域
        clip_limit: CLAHE 对比度限制
        tile_size: CLAHE 网格 (6x6 适合人脸区域)

    Returns:
        预处理后的人脸区域
    """
    if face_image is None or face_image.size == 0:
        return face_image

    clahe = _get_clahe(clip_limit, tile_size)

    lab = cv2.cvtColor(face_image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l_eq = clahe.apply(l)
    lab_eq = cv2.merge([l_eq, a, b])
    result = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)

    return result
