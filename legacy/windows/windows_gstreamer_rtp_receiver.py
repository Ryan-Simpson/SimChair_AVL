"""
windows_gstreamer_rtp_receiver.py  —  run on Windows (Plan B fallback)
Receives direct RTP/UDP H.264 from orin_gstreamer_rtp_sender.py.

Requires GStreamer for Windows with d3d11h264dec, or use WSL/ffmpeg variant.
Install: https://gstreamer.freedesktop.org/download/

Usage:
    python windows_gstreamer_rtp_receiver.py
"""

import argparse
import subprocess
import sys
import threading
import queue

import cv2
import numpy as np

CAMERAS = [
    ('Left',  5602,     0),
    ('Front', 5600,  1920),
    ('Right', 5604,  3840),
]

# GStreamer pipeline per camera (stdin → raw BGR for OpenCV)
GST_PIPELINE = (
    'udpsrc port={port} caps="application/x-rtp,media=video,encoding-name=H264" ! '
    'rtpjitterbuffer latency=50 ! rtph264depay ! h264parse ! '
    'd3d11h264dec ! videoconvert ! video/x-raw,format=BGR ! '
    'fdsink fd=1 sync=false'
)


def stream(name: str, port: int, frame_queue: queue.Queue):
    cmd = ['gst-launch-1.0', '-q'] + GST_PIPELINE.format(port=port).split(' ! ')
    # gst-launch needs proper pipeline string
    pipeline = GST_PIPELINE.format(port=port)
    proc = subprocess.Popen(
        ['gst-launch-1.0', '-q'] + _split_gst(pipeline),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    width, height = 1280, 720
    frame_size = width * height * 3

    print(f'[{name}] Listening UDP port {port}')
    while True:
        raw = proc.stdout.read(frame_size)
        if len(raw) < frame_size:
            print(f'[{name}] Stream ended.')
            break
        frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
        try:
            frame_queue.get_nowait()
        except queue.Empty:
            pass
        frame_queue.put(frame.copy())

    proc.kill()


def _split_gst(pipeline: str) -> list:
    """Split GStreamer pipeline on ' ! ' for gst-launch argv."""
    return [p.strip() for p in pipeline.split('!')]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-gst', action='store_true', help='Verify gst-launch exists')
    args = parser.parse_args()

    if args.check_gst:
        try:
            subprocess.run(['gst-launch-1.0', '--version'], check=True, capture_output=True)
            print('GStreamer OK')
        except (FileNotFoundError, subprocess.CalledProcessError):
            print('ERROR: gst-launch-1.0 not found. Install GStreamer for Windows.')
            sys.exit(1)
        return

    queues = {name: queue.Queue(maxsize=2) for name, _, _ in CAMERAS}
    for name, port, _ in CAMERAS:
        t = threading.Thread(target=stream, args=(name, port, queues[name]), daemon=True)
        t.start()

    windows_created = {name: False for name, _, _ in CAMERAS}
    print('Running. Press Q to quit.')

    while True:
        for name, _, x_offset in CAMERAS:
            try:
                frame = queues[name].get_nowait()
            except queue.Empty:
                continue

            win = f'ZED {name}'
            if not windows_created[name]:
                cv2.namedWindow(win, cv2.WINDOW_NORMAL)
                cv2.moveWindow(win, x_offset, 0)
                cv2.resizeWindow(win, 1920, 1080)
                windows_created[name] = True
            cv2.imshow(win, frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
