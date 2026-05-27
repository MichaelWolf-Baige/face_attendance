"""
人脸匹配模块
使用余弦相似度进行人脸比对（配合 InsightFace 归一化特征向量）
优化：预计算归一化矩阵，批量矩阵乘法，三区阈值策略
"""
import numpy as np
from typing import List, Tuple, Optional, Dict
import config


class FaceMatcher:
    """人脸比对类 (余弦相似度) — 三区阈值优化版"""

    def __init__(self, tolerance: float = None):
        # 三区阈值: confident(直接确认) / uncertain(需额外验证) / reject
        self.confident = getattr(config, 'FACE_RECOGNITION_CONFIDENT', 0.55)
        self.tolerance = tolerance if tolerance is not None else config.FACE_RECOGNITION_TOLERANCE
        self.uncertain_min_margin = 0.08  # 不确定区内最低 margin 要求

        # 预计算的归一化矩阵（refresh_face_database 时更新）
        self._known_matrix = None   # (N, 512) float32, L2归一化
        self._known_names = None    # list[str]
        self._known_ids = None      # list[str]  student_id

    def _classify_match(self, best_sim: float, margin: float) -> Tuple[bool, float]:
        """
        三区阈值分类

        Returns:
            (is_match, adjusted_confidence)
        """
        if best_sim >= self.confident:
            # 高置信区: 直接确认
            return True, float(best_sim)
        elif best_sim >= self.tolerance:
            # 不确定区: 需要 margin 足够大才确认
            if margin >= self.uncertain_min_margin:
                # margin 充足，确认但降低置信度
                return True, float(best_sim * 0.9)
            else:
                # margin 不够，拒绝（可能是库内相似人脸混淆）
                return False, float(best_sim)
        else:
            # 拒绝区
            return False, float(best_sim)

    def update_database(self, encodings: List[np.ndarray],
                        names: List[str],
                        student_ids: List[str] = None):
        """
        更新人脸库并预计算归一化矩阵

        调用此方法后，match() 将使用缓存的矩阵，无需每次重新归一化

        Args:
            encodings: 特征向量列表 (应为 float32)
            names: 对应姓名列表
            student_ids: 对应学号列表
        """
        if not encodings:
            self._known_matrix = None
            self._known_names = None
            self._known_ids = None
            return

        self._known_matrix = np.array(encodings, dtype=np.float32)
        # 归一化（只做一次，后续 match 直接使用）
        norms = np.linalg.norm(self._known_matrix, axis=1, keepdims=True)
        self._known_matrix = self._known_matrix / (norms + 1e-10)
        self._known_names = list(names)
        self._known_ids = list(student_ids) if student_ids else [None] * len(names)

    def match(self, face_encoding: np.ndarray,
              known_encodings: List[np.ndarray] = None,
              known_names: List[str] = None) -> Tuple[Optional[str], float, Optional[int]]:
        """
        比对单个人脸与已知人脸库

        优先使用 update_database() 缓存的矩阵；
        如未缓存，则使用传入的参数（兼容旧接口）

        Args:
            face_encoding: 待识别特征向量 (应为L2归一化)
            known_encodings: 已知人脸特征列表 (兼容旧接口，优先用缓存)
            known_names: 对应的姓名列表 (兼容旧接口)

        Returns:
            (name, confidence, index): 识别结果、置信度、人脸库索引
        """
        if face_encoding is None:
            return None, 0.0, None

        query = face_encoding / (np.linalg.norm(face_encoding) + 1e-10)

        # 优先使用缓存矩阵
        if self._known_matrix is not None:
            similarities = self._known_matrix @ query
            names = self._known_names
        elif known_encodings and known_names:
            known = np.array(known_encodings, dtype=np.float32)
            known = known / (np.linalg.norm(known, axis=1, keepdims=True) + 1e-10)
            similarities = known @ query
            names = known_names
        else:
            return None, 0.0, None

        best_idx = int(np.argmax(similarities))
        best_sim = float(similarities[best_idx])

        # 计算 margin
        margin = 0.0
        if len(similarities) > 1:
            sorted_sims = np.sort(similarities)[::-1]
            margin = best_sim - sorted_sims[1]

        # 三区阈值分类
        is_match, confidence = self._classify_match(best_sim, margin)

        if not is_match:
            return None, confidence, None

        return names[best_idx], float(confidence), best_idx

    def match_with_details(self, face_encoding: np.ndarray) -> Dict:
        """
        比对并返回完整匹配详情

        Returns:
            dict: matched, name, confidence, distance, margin, index, student_id
        """
        if face_encoding is None or self._known_matrix is None:
            return {
                'matched': False, 'name': None, 'confidence': 0.0,
                'distance': 1.0, 'margin': 0.0, 'index': None, 'student_id': None
            }

        query = face_encoding / (np.linalg.norm(face_encoding) + 1e-10)
        similarities = self._known_matrix @ query

        sorted_indices = np.argsort(similarities)[::-1]
        best_idx = int(sorted_indices[0])
        best_sim = float(similarities[best_idx])

        margin = 0.0
        if len(similarities) > 1:
            second_best = float(similarities[sorted_indices[1]])
            margin = best_sim - second_best

        # 三区阈值分类
        matched, confidence = self._classify_match(best_sim, margin)

        student_id = self._known_ids[best_idx] if self._known_ids else None

        return {
            'matched': matched,
            'name': self._known_names[best_idx] if matched else None,
            'confidence': float(confidence),
            'distance': float(1.0 - best_sim),
            'margin': float(margin),
            'index': best_idx,
            'student_id': student_id if matched else None,
        }

    def match_multiple_batch(self, face_encodings: List[np.ndarray],
                             known_encodings: List[np.ndarray] = None,
                             known_names: List[str] = None
                             ) -> List[Tuple[Optional[str], float, Optional[int]]]:
        """
        批量匹配多个人脸 — 单次矩阵乘法

        优先使用缓存矩阵；否则回退到逐个匹配

        Returns:
            [(name, confidence, index), ...]
        """
        if not face_encodings:
            return []

        # 尝试使用缓存的矩阵做批量匹配
        if self._known_matrix is not None:
            queries = np.array(face_encodings, dtype=np.float32)
            norms = np.linalg.norm(queries, axis=1, keepdims=True)
            queries = queries / (norms + 1e-10)

            # (n_queries, 512) @ (512, n_known) → (n_queries, n_known)
            sim_matrix = queries @ self._known_matrix.T

            results = []
            for i in range(len(face_encodings)):
                sims = sim_matrix[i]
                best_idx = int(np.argmax(sims))
                best_sim = float(sims[best_idx])

                # 计算 margin
                margin = 0.0
                if len(sims) > 1:
                    sorted_sims = np.sort(sims)[::-1]
                    margin = best_sim - sorted_sims[1]

                # 三区阈值分类
                is_match, confidence = self._classify_match(best_sim, margin)

                if not is_match:
                    results.append((None, confidence, None))
                    continue

                results.append((self._known_names[best_idx], float(confidence), best_idx))

            return results

        # 回退：逐个匹配（兼容旧接口）
        results = []
        for encoding in face_encodings:
            name, conf, idx = self.match(encoding, known_encodings, known_names)
            results.append((name, conf, idx))
        return results

    def compare_faces(self, encoding1: np.ndarray,
                      encoding2: np.ndarray) -> Tuple[bool, float]:
        """比较两个人脸是否相同"""
        e1 = encoding1 / (np.linalg.norm(encoding1) + 1e-10)
        e2 = encoding2 / (np.linalg.norm(encoding2) + 1e-10)
        similarity = float(np.dot(e1, e2))
        is_match = similarity >= self.tolerance
        return is_match, float(1.0 - similarity)

    def set_tolerance(self, tolerance: float):
        """设置余弦相似度匹配阈值"""
        self.tolerance = tolerance

    def get_database_size(self) -> int:
        """返回当前人脸库大小"""
        return len(self._known_matrix) if self._known_matrix is not None else 0
