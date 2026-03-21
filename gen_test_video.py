#!/usr/bin/env python
"""生成用于测试的短视频文件"""
import cv2
import numpy as np
from pathlib import Path

out = Path(__file__).parent / 'tmp_test_video.mp4'
W, H = 640, 360
fps = 10
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
writer = cv2.VideoWriter(str(out), fourcc, fps, (W, H))

for i in range(30):
    frame = np.zeros((H, W, 3), dtype=np.uint8)
    frame[:] = (10, 10, 10)
    cv2.putText(frame, 'GUARANTEED PROFIT', (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
    cv2.putText(frame, 'WECHAT: add me now', (40, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    writer.write(frame)

writer.release()
print('wrote', out, 'size', out.stat().st_size)


