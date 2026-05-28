"""
人脸特征提取模块
使用 InsightFace ArcFace 512维特征向量 + 5点关键点对齐
集成 FaceAligner 进行姿态估计和质量评估
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional
import config
from utils.logger import get_logger
from .face_aligner import FaceAligner

logger = get_logger(__name__)

# 模块级单例，detector 和 encoder 共享
_face_model = None
_model_config = {}


def set_model_config(model_name: str = None, det_size: tuple = None):
    """由 AppContext 调用，在模型加载前注入配置"""
    global _model_config
    if model_name is not None:
        _model_config['model_name'] = model_name
    if det_size is not None:
        _model_config['det_size'] = det_size


def _get_face_model():
    """获取 InsightFace 模型单例"""
    global _face_model
    if _face_model is None:
        import insightface
        providers = ['CPUExecutionProvider']
        try:
            import onnxruntime as ort
            if 'CUDAExecutionProvider' in ort.get_available_providers():
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        except ImportError:
            pass
        model_name = _model_config.get('model_name') or getattr(config, 'FACE_MODEL_NAME', 'buffalo_l')
        det_sz = _model_config.get('det_size') or getattr(config, 'FACE_DET_SIZE', (640, 640))
        _face_model = insightface.app.FaceAnalysis(
            name=model_name,
            providers=providers
        )
        _face_model.prepare(ctx_id=0, det_size=det_sz)
        logger.info(f"InsightFace 模型加载完成 (模型: {model_name}, 检测: SCRFD, 编码: ArcFace 512维, det_size: {det_sz}, providers: {providers})")

        # 模型预热：运行一次虚拟推理预加载GPU内核
        try:
            import numpy as np
            dummy = np.zeros((112, 112, 3), dtype=np.uint8)
            _face_model.get(dummy, max_num=1)
            logger.info("模型预热完成")
        except Exception as e:
            logger.warning(f"模型预热失败(非阻塞): {e}")
    return _face_model


class FaceEncoder:
    """人脸特征提取类 (InsightFace ArcFace)"""

    def __init__(self, num_jitters: int = None):
        self.num_jitters = num_jitters  # InsightFace无此参数，保留接口兼容

    def detect_and_encode(self, image: np.ndarray,
                          max_num: int = 10,
                          resize_scale: float = None) -> List[dict]:
        """
        一次调用同时完成人脸检测+特征提取+5点关键点质量评估

        避免了 detect() + encode_faces() 两次 model.get() 的性能浪费
        集成 FaceAligner 返回姿态信息和综合质量评分

        Args:
            image: BGR格式的numpy数组
            max_num: 最大检测人脸数
            resize_scale: 缩放比例（None=使用实例默认值）

        Returns:
            列表，每项包含:
              - location: (top, right, bottom, left) dlib格式
              - encoding: 512维归一化特征向量
              - det_score: 检测置信度
              - landmark: 5点关键点 (5,2) 或 None
              - bbox_raw: (x1, y1, x2, y2) 原始坐标
              - pose: 姿态信息 dict (roll, yaw, is_frontal, frontal_score)
              - quality: 综合质量评估 dict (total_score, is_good, reject_reason)
              - aligned_face: 112x112 对齐后的人脸图像
        """
        if image is None or image.size == 0:
            return []

        scale = resize_scale if resize_scale is not None else config.FACE_ATTENDANCE_RESIZE_SCALE
        h, w = image.shape[:2]

        # 先缩放再处理
        if scale != 1.0:
            small = cv2.resize(image, (int(w * scale), int(h * scale)))
        else:
            small = image

        try:
            model = _get_face_model()
            faces = model.get(small, max_num=max_num)

            results = []
            for face in faces:
                emb = face.embedding
                emb = emb / (np.linalg.norm(emb) + 1e-10)
                emb = emb.astype(np.float32)

                # 坐标还原到原图尺度
                x1, y1, x2, y2 = face.bbox.astype(int)
                if scale != 1.0:
                    x1 = int(x1 / scale)
                    y1 = int(y1 / scale)
                    x2 = int(x2 / scale)
                    y2 = int(y2 / scale)

                det_score = float(face.det_score)

                # 5点关键点（还原到原图尺度）
                landmark = None
                if hasattr(face, 'kps') and face.kps is not None:
                    landmark = face.kps.astype(np.float32).copy()
                    if scale != 1.0:
                        landmark = landmark / scale

                # 姿态估计
                pose = FaceAligner.estimate_pose(landmark)

                # 综合质量评估
                top, right, bottom, left = y1, x2, y2, x1
                face_region = image[max(0, top):min(h, bottom), max(0, left):min(w, right)]
                quality = FaceAligner.assess_quality(face_region, landmark, det_score)

                # 5点仿射对齐（显式对齐到 ArcFace 模板）
                aligned_face = FaceAligner.align_face(image, landmark)

                results.append({
                    'location': (y1, x2, y2, x1),
                    'encoding': emb,
                    'det_score': det_score,
                    'landmark': landmark,
                    'bbox_raw': (x1, y1, x2, y2),
                    'pose': pose,
                    'quality': quality,
                    'aligned_face': aligned_face,
                })

            return results
        except Exception as e:
            logger.error(f"检测+编码错误: {e}")
            return []

    def encode(self, image: np.ndarray,
               face_location: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        提取单个人脸的特征向量 (已对齐，L2归一化)

        Args:
            image: BGR格式的numpy数组
            face_location: 人脸位置 (top, right, bottom, left) — dlib格式

        Returns:
            512维归一化特征向量，失败返回None
        """
        if image is None or image.size == 0:
            return None

        try:
            top, right, bottom, left = face_location
            h, w = image.shape[:2]

            pad_t = max(0, top - 20)
            pad_b = min(h, bottom + 20)
            pad_l = max(0, left - 20)
            pad_r = min(w, right + 20)
            face_img = image[pad_t:pad_b, pad_l:pad_r]

            model = _get_face_model()
            faces = model.get(face_img, max_num=1)
            if faces:
                emb = faces[0].embedding
                emb = emb / np.linalg.norm(emb)
                return emb.astype(np.float32)
            return None
        except Exception as e:
            logger.error(f"特征提取错误: {e}")
            return None

    def encode_average(self, images: List[np.ndarray],
                       face_locations: List[Tuple[int, int, int, int]] = None) -> Optional[np.ndarray]:
        """
        从多张图片提取特征并返回平均编码（注册用 — 简单平均，旧接口）

        建议使用 encode_with_quality() 替代，支持质量加权和离群值剔除
        """
        if not images:
            return None

        model = _get_face_model()
        encodings = []
        for img in images:
            if img is None or img.size == 0:
                continue
            try:
                faces = model.get(img, max_num=1)
                if faces:
                    emb = faces[0].embedding
                    emb = emb / (np.linalg.norm(emb) + 1e-10)
                    encodings.append(emb.astype(np.float32))
            except Exception as e:
                logger.warning(f"编码失败: {e}")
                continue

        if not encodings:
            return None

        avg = np.mean(encodings, axis=0)
        avg = avg / (np.linalg.norm(avg) + 1e-10)
        logger.info(f"从{len(encodings)}/{len(images)}张图片生成平均编码")
        return avg.astype(np.float32)

    def encode_with_quality(self, images: List[np.ndarray],
                             resize_scale: float = None,
                             min_quality: float = None) -> Optional[np.ndarray]:
        """
        从多张图片提取特征，使用5点关键点进行质量加权+离群值剔除

        注册流水线的核心方法，比 encode_average() 更精确:
        1. 对每张图用 detect_and_encode 获取编码+5点关键点+姿态+质量
        2. 过滤非正面脸、模糊脸、质量不合格的图片
        3. 按质量排序，只取最好的前N张 (FACE_REGISTRATION_TOP_N)
        4. 离群值剔除: 去掉与聚类中心距离过大的编码
        5. 质量加权平均: 好照片权重高，差照片权重低
        6. L2 归一化输出

        Args:
            images: 多张BGR人脸图像
            resize_scale: 缩放比例 (None=使用配置值)
            min_quality: 最低质量阈值 (None=使用配置值)

        Returns:
            512维归一化质量加权特征向量，失败返回None
        """
        if not images:
            return None

        scale = resize_scale if resize_scale is not None else getattr(config, 'FACE_REGISTRATION_RESIZE_SCALE', 0.75)
        min_q = min_quality if min_quality is not None else getattr(config, 'FACE_REGISTRATION_MIN_QUALITY', 0.25)
        outlier_sim = getattr(config, 'FACE_REGISTRATION_OUTLIER_SIM', 0.30)

        # 第1步：对每张图提取编码+质量
        items = []  # (encoding, quality_score, reject_reason)
        for img in images:
            if img is None or img.size == 0:
                continue
            try:
                dets = self.detect_and_encode(img, max_num=1, resize_scale=scale)
                if not dets:
                    items.append((None, 0.0, "未检测到人脸"))
                    continue

                det = dets[0]
                quality = det['quality']
                # 用注册专用(放宽的)质量阈值重新评估
                quality['is_acceptable'] = quality['total_score'] >= min_q
                if not quality['is_acceptable'] and quality.get('reject_reason') is None:
                    quality['reject_reason'] = f'质量不达标(score={quality["total_score"]:.2f}<{min_q})'
                if not quality['is_acceptable']:
                    items.append((None, 0.0, quality.get('reject_reason', '质量不达标')))
                    continue

                items.append((det['encoding'], quality['total_score'], None))
            except Exception as e:
                items.append((None, 0.0, f"编码异常: {e}"))
                continue

        valid = [(enc, score) for enc, score, _ in items if enc is not None]
        rejected = [(score, reason) for _, score, reason in items if reason is not None]

        if rejected:
            reasons = [f"质量={s:.2f}({r})" for s, r in rejected]
            logger.info(f"注册时拒绝了 {len(rejected)} 张图片: {reasons}")

        if not valid:
            logger.warning(f"所有 {len(images)} 张图片均质量不合格")
            return None

        # 第2步：按质量排序，只取最好的前N张
        top_n = getattr(config, 'FACE_REGISTRATION_TOP_N', 5)
        if top_n > 0 and len(valid) > top_n:
            valid.sort(key=lambda x: x[1], reverse=True)
            dropped = len(valid) - top_n
            valid = valid[:top_n]
            logger.info(f"注册: 取质量最高的 {top_n}/{len(valid) + dropped} 张照片 "
                        f"(质量范围: {valid[-1][1]:.2f}~{valid[0][1]:.2f})")

        # 第3步：离群值剔除
        encodings = np.array([e for e, _ in valid])
        if len(encodings) > 2:
            mean_enc = np.mean(encodings, axis=0)
            mean_enc = mean_enc / (np.linalg.norm(mean_enc) + 1e-10)

            # 计算每个编码与均值的余弦相似度
            sims = encodings @ mean_enc

            # 保留相似度高于阈值的编码
            mask = sims > outlier_sim
            if mask.sum() == 0:
                # 全是离群值？至少保留最好的一个
                best_idx = np.argmax(sims)
                mask = np.zeros(len(sims), dtype=bool)
                mask[best_idx] = True

            outlier_count = len(encodings) - mask.sum()
            if outlier_count > 0:
                logger.info(f"离群值剔除: 移除 {outlier_count} 个异常编码 "
                            f"(sim范围: {sims.min():.3f}~{sims.max():.3f})")

            filtered = [(encodings[i], valid[i][1]) for i in range(len(valid)) if mask[i]]
        else:
            filtered = valid

        # 第5步：质量加权平均
        enc_list = [e for e, _ in filtered]
        weights = np.array([s for _, s in filtered])

        # 归一化权重
        weights = weights / (weights.sum() + 1e-10)

        weighted_avg = np.zeros_like(enc_list[0])
        for enc, w in zip(enc_list, weights):
            weighted_avg += w * enc

        weighted_avg = weighted_avg / (np.linalg.norm(weighted_avg) + 1e-10)
        logger.info(f"从 {len(filtered)}/{len(images)} 张图片生成质量加权编码 "
                    f"(权重: {weights.round(2).tolist()})")
        return weighted_avg.astype(np.float32)

    def encode_faces(self, image: np.ndarray,
                     face_locations: List[Tuple[int, int, int, int]]) -> List[np.ndarray]:
        """
        批量提取多个人脸的特征向量

        注意：此方法会重新运行检测，建议使用 detect_and_encode() 替代
        """
        if image is None or image.size == 0:
            return []

        try:
            model = _get_face_model()
            faces = model.get(image, max_num=len(face_locations) if face_locations else 0)
            encodings = []
            for face in faces:
                emb = face.embedding
                emb = emb / (np.linalg.norm(emb) + 1e-10)
                encodings.append(emb.astype(np.float32))
            return encodings
        except Exception as e:
            logger.error(f"批量特征提取错误: {e}")
            return []

    def encode_face_image(self, face_image: np.ndarray) -> Optional[np.ndarray]:
        """
        从单张人脸图像提取特征 (自动检测人脸)
        """
        if face_image is None or face_image.size == 0:
            return None

        try:
            model = _get_face_model()
            faces = model.get(face_image, max_num=1)
            if faces:
                emb = faces[0].embedding
                emb = emb / (np.linalg.norm(emb) + 1e-10)
                return emb.astype(np.float32)
            return None
        except Exception as e:
            logger.error(f"特征提取错误: {e}")
            return None
