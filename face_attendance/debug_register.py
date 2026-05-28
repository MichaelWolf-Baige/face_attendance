"""人脸注册调试工具 - 测试指定目录中编码提取效果"""
import sys
import os
import cv2
import numpy as np
from core.face_detector import FaceDetector
from core.face_encoder import FaceEncoder


def main(data_dir: str):
    detector = FaceDetector(resize_scale=1.0)
    encoder = FaceEncoder()

    for student_dir in sorted(os.listdir(data_dir)):
        student_path = os.path.join(data_dir, student_dir)
        if not os.path.isdir(student_path):
            continue

        print(f'\n=== {student_dir} ===')
        img_paths = []
        for root, dirs, files in os.walk(student_path):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                    img_paths.append(os.path.join(root, f))

        print(f'Total images: {len(img_paths)}')
        face_encodings = []

        for i, p in enumerate(img_paths):
            img = cv2.imdecode(
                open(p, 'rb').read() if os.name == 'nt' else open(p, 'rb').read(),
                cv2.IMREAD_COLOR
            )
            if img is None:
                continue

            face_locations = detector.detect(img)
            if len(face_locations) == 0:
                print(f'  [{i+1}] {os.path.basename(p)}: no face')
                continue

            if len(face_locations) > 1:
                print(f'  [{i+1}] {os.path.basename(p)}: {len(face_locations)} faces, using largest')
                face_locations = [max(
                    face_locations,
                    key=lambda loc: (loc[2]-loc[0]) * (loc[1]-loc[3])
                )]

            top, right, bottom, left = face_locations[0]
            quality = detector.detect_quality(img[top:bottom, left:right])
            if quality < 0.3:
                print(f'  [{i+1}] {os.path.basename(p)}: low quality={quality:.3f}')
                continue

            encoding = encoder.encode(img, face_locations[0])
            if encoding is not None:
                face_encodings.append(encoding)
                print(f'  [{i+1}] {os.path.basename(p)}: OK (q={quality:.3f}, norm={np.linalg.norm(encoding):.4f})')
            else:
                print(f'  [{i+1}] {os.path.basename(p)}: encode FAILED')

        print(f'Result: {len(face_encodings)}/{len(img_paths)} encodings')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <student_data_directory>")
        print(f"  Directory should contain subdirectories named like '1_张三/'")
        sys.exit(1)
    main(sys.argv[1])
