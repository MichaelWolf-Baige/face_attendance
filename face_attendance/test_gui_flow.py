"""
测试人脸识别GUI流程
"""
import sys
import cv2
import numpy as np
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QThread, pyqtSignal
from queue import Queue

from database.db_manager import DatabaseManager
from services.attendance_service import AttendanceService


class TestRecognitionThread(QThread):
    result_ready = pyqtSignal(list)

    def __init__(self, attendance_service):
        super().__init__()
        self.attendance_service = attendance_service
        self.frame_queue = Queue(maxsize=1)
        self._running = True

    def add_frame(self, frame):
        if self.frame_queue.full():
            try:
                self.frame_queue.get_nowait()
            except:
                pass
        self.frame_queue.put(frame)

    def run(self):
        self.attendance_service.refresh_face_database()
        print(f"[识别线程启动] 人脸库: {self.attendance_service._face_names}")

        while self._running:
            try:
                frame = self.frame_queue.get(timeout=0.5)
                results = self.attendance_service.process_frame(frame)
                if results:
                    print(f"[识别线程] 结果: {[r.get('name') for r in results]}")
                self.result_ready.emit(results)
            except:
                continue

    def stop(self):
        self._running = False
        self.wait()


def on_result(results):
    print(f"[主线程收到] 识别结果: {len(results)} 人")
    for r in results:
        print(f"  - {r.get('name')}: {r.get('confidence'):.0%}")


def main():
    # 初始化
    app = QApplication([])

    db = DatabaseManager()
    service = AttendanceService(db)

    # 创建识别线程
    thread = TestRecognitionThread(service)
    thread.result_ready.connect(on_result)
    thread.start()
    print("识别线程已启动")

    # 打开摄像头
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("摄像头已打开，测试10秒...")

    start_time = time.time()
    frame_count = 0

    while time.time() - start_time < 10:
        ret, frame = cap.read()
        if not ret:
            continue

        frame = cv2.flip(frame, 1)
        thread.add_frame(frame)
        frame_count += 1

        # 显示
        cv2.imshow('Test', frame)
        cv2.waitKey(1)

    cap.release()
    cv2.destroyAllWindows()
    thread.stop()

    print(f"\n测试完成，处理了 {frame_count} 帧")


if __name__ == '__main__':
    main()