"""
摄像头线程模块
使用OpenCV捕获视频流
"""
import cv2
import threading
import time
import numpy as np
import logging
from typing import Callable, Optional
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

logger = logging.getLogger(__name__)

# 最大连续错误次数
MAX_CONSECUTIVE_ERRORS = 10


class CameraThread(QObject):
    """摄像头线程类"""

    # 信号定义
    frame_ready = pyqtSignal(np.ndarray)  # 帧就绪信号
    error_occurred = pyqtSignal(str)  # 错误信号

    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480):
        """
        初始化摄像头线程

        Args:
            camera_index: 摄像头索引
            width: 画面宽度
            height: 画面高度
        """
        super().__init__()

        self.camera_index = camera_index
        self.width = width
        self.height = height

        self._running = False
        self._stop_event = threading.Event()  # 使用事件而非简单布尔值
        self._thread = None
        self._cap = None
        self._lock = threading.Lock()
        self._cap_lock = threading.Lock()  # 专门保护VideoCapture

    def start(self):
        """启动摄像头"""
        if self._running:
            return

        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """停止摄像头 - 安全版本"""
        self._running = False
        self._stop_event.set()  # 设置停止信号

        # 先释放摄像头资源，这会中断阻塞的read()
        with self._cap_lock:
            if self._cap:
                self._cap.release()
                self._cap = None

        # 等待线程退出
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
            if self._thread.is_alive():
                logger.warning("Camera thread did not stop in time")

        self._thread = None

    def _run(self):
        """线程运行函数"""
        with self._cap_lock:
            self._cap = cv2.VideoCapture(self.camera_index)

            if not self._cap.isOpened():
                self.error_occurred.emit(f"无法打开摄像头 {self.camera_index}")
                self._running = False
                return

            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

            actual_w = self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            actual_h = self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            logger.info(f"摄像头实际分辨率: {int(actual_w)}x{int(actual_h)} (请求: {self.width}x{self.height})")

        # 计算帧率
        fps_counter = 0
        fps_start_time = time.time()
        fps = 0

        # 错误计数和退避
        consecutive_errors = 0
        error_backoff = 0.1

        while self._running and not self._stop_event.is_set():
            with self._cap_lock:
                if self._cap is None or not self._cap.isOpened():
                    break
                ret, frame = self._cap.read()

            if not ret:
                consecutive_errors += 1

                # 超过最大错误次数，停止摄像头
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    self.error_occurred.emit("摄像头连续读取失败，已停止")
                    break

                # 只在首次错误时发送信号
                if consecutive_errors == 1:
                    self.error_occurred.emit(f"读取摄像头帧失败 (尝试 {consecutive_errors}/{MAX_CONSECUTIVE_ERRORS})")

                # 指数退避
                time.sleep(error_backoff)
                error_backoff = min(error_backoff * 2, 2.0)  # 最多等待2秒
                continue

            # 成功读取，重置错误计数
            consecutive_errors = 0
            error_backoff = 0.1

            # 水平翻转（镜像效果）
            frame = cv2.flip(frame, 1)

            # 计算帧率
            fps_counter += 1
            if time.time() - fps_start_time >= 1.0:
                fps = fps_counter
                fps_counter = 0
                fps_start_time = time.time()

            # 在帧上显示帧率
            cv2.putText(frame, f"FPS: {fps}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 发射信号
            self.frame_ready.emit(frame)

            # 控制帧率
            time.sleep(0.01)

        # 清理
        with self._cap_lock:
            if self._cap:
                self._cap.release()
                self._cap = None

    def get_frame(self) -> Optional[np.ndarray]:
        """获取当前帧（同步方式）"""
        with self._lock:
            if self._cap and self._cap.isOpened():
                ret, frame = self._cap.read()
                if ret:
                    return cv2.flip(frame, 1)
        return None

    def is_running(self) -> bool:
        """检查摄像头是否正在运行"""
        return self._running

    def capture_image(self, save_path: str = None) -> Optional[np.ndarray]:
        """
        捕获一张图片

        Args:
            save_path: 保存路径（可选）

        Returns:
            捕获的图像
        """
        frame = self.get_frame()
        if frame is not None and save_path:
            cv2.imwrite(save_path, frame)
        return frame


class CameraManager:
    """摄像头管理器（单例模式）"""

    _instance = None
    _camera = None

    @classmethod
    def get_camera(cls, camera_index: int = 0) -> CameraThread:
        """获取摄像头实例"""
        if cls._camera is None:
            cls._camera = CameraThread(camera_index)
        return cls._camera

    @classmethod
    def release_camera(cls):
        """释放摄像头"""
        if cls._camera:
            cls._camera.stop()
            cls._camera = None