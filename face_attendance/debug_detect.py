"""人脸检测调试工具 - 测试指定目录中人脸检测效果"""
import sys
import cv2
import os
from core.face_detector import FaceDetector


def main(data_dir: str):
    detector = FaceDetector(resize_scale=1.0)
    img_paths = []

    for root, dirs, files in os.walk(data_dir):
        for f in files:
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                img_paths.append(os.path.join(root, f))

    print(f'Testing {len(img_paths)} images from: {data_dir}')
    fail = 0
    for i, p in enumerate(img_paths):
        img = cv2.imdecode(
            open(p, 'rb').read() if os.name == 'nt' else open(p, 'rb').read(),
            cv2.IMREAD_COLOR
        )
        if img is None:
            continue
        locs = detector.detect(img)
        if locs:
            top, right, bottom, left = locs[0]
            quality = detector.detect_quality(img[top:bottom, left:right])
            print(f'  [{i+1}] {os.path.basename(p)}: OK, quality={quality:.3f}')
        else:
            fail += 1
            print(f'  [{i+1}] {os.path.basename(p)}: NO FACE')
    print(f'Result: {len(img_paths)-fail}/{len(img_paths)} detected, {fail} failed')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <image_directory>")
        sys.exit(1)
    main(sys.argv[1])
