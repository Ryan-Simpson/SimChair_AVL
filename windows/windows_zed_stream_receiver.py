"""
windows_zed_stream_receiver.py  —  run on Windows sim-chair PC
Receives ZED SDK native H.265 streams from Jetson over Tailscale (RTP/UDP).

Requires: ZED SDK for Windows + pyzed (install from Stereolabs, not pip).
Fallback: windows_camera_receiver.py (JPEG/TCP) if this fails.

Usage:
    python windows_zed_stream_receiver.py
    python windows_zed_stream_receiver.py --profile lan   # use LAN IPs
"""

import argparse
import sys
import threading
import queue

import cv2
import numpy as np

try:
    import pyzed.sl as sl
except ImportError:
    print('ERROR: pyzed not installed. Install ZED SDK for Windows from Stereolabs.')
    print('Fallback: python windows_camera_receiver.py')
    sys.exit(1)

# Tailscale IPs (default profile)
PROFILES = {
    'tailscale': {
        'jetson_ip': '100.93.121.3',
    },
    'lan': {
        'jetson_ip': '192.168.1.100',  # override with --jetson-ip
    },
}

# name, stream_port, x_offset (NVIDIA Surround: 0 / 1920 / 3840)
ALL_CAMERAS = [
    ('Left',  30004,     0),
    ('Front', 30000,  1920),
    ('Right', 30008,  3840),
]


class ZedStreamReader:
    """One ZED network stream; grab thread pushes BGR frames to a queue."""

    def __init__(self, name: str, jetson_ip: str, port: int, frame_queue: queue.Queue):
        self.name = name
        self.frame_queue = frame_queue
        self._running = True

        init = sl.InitParameters()
        init.set_from_stream(jetson_ip, port)
        init.depth_mode = sl.DEPTH_MODE.NONE  # video only — lower latency
        # Do not force resolution/fps: match whatever Jetson is streaming.

        self.cam = sl.Camera()
        status = self.cam.open(init)
        # SDK 5.x may return POTENTIAL_CALIBRATION_ISSUE as a soft warning from open().
        # Fine for RGB teleop (depth disabled). Only hard-fail real errors.
        soft_ok = {sl.ERROR_CODE.SUCCESS}
        if hasattr(sl.ERROR_CODE, 'POTENTIAL_CALIBRATION_ISSUE'):
            soft_ok.add(sl.ERROR_CODE.POTENTIAL_CALIBRATION_ISSUE)
        if hasattr(sl.ERROR_CODE, 'CONFIGURATION_FALLBACK'):
            soft_ok.add(sl.ERROR_CODE.CONFIGURATION_FALLBACK)
        if status not in soft_ok:
            raise RuntimeError(f'[{name}] Failed to open stream {jetson_ip}:{port}: {status}')
        if status != sl.ERROR_CODE.SUCCESS:
            print(f'[{name}] open() warning {status} — continuing (RGB-only stream)')

        self.mat = sl.Mat()
        self.thread = threading.Thread(target=self._grab_loop, daemon=True)
        self.thread.start()
        print(f'[{name}] Stream open on {jetson_ip}:{port}')

    def _grab_loop(self):
        while self._running:
            err = self.cam.grab()
            if err != sl.ERROR_CODE.SUCCESS:
                # Packet loss / corrupt chunk — keep last good frame; don't thrash CPU
                continue
            self.cam.retrieve_image(self.mat, sl.VIEW.LEFT)
            bgra = self.mat.get_data()
            if bgra is None:
                continue
            # Copy: Mat buffer is reused by SDK on next grab
            frame = cv2.cvtColor(bgra, cv2.COLOR_BGRA2BGR).copy()
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass

    def close(self):
        self._running = False
        try:
            self.thread.join(timeout=1.0)
        except Exception:
            pass
        self.cam.close()


def main():
    parser = argparse.ArgumentParser(description='ZED SDK H.265 stream receiver (3 monitors)')
    parser.add_argument('--profile', choices=['tailscale', 'lan'], default='tailscale')
    parser.add_argument('--jetson-ip', help='Override Jetson IP')
    parser.add_argument(
        '--front-only',
        action='store_true',
        help='Phase-2 bring-up: connect only front (port 30000)',
    )
    parser.add_argument(
        '--native-size',
        action='store_true',
        help='Do not upscale to 1920x1080 (less tear/softness on SVGA streams)',
    )
    args = parser.parse_args()

    jetson_ip = args.jetson_ip or PROFILES[args.profile]['jetson_ip']
    cameras = [c for c in ALL_CAMERAS if c[0] == 'Front'] if args.front_only else ALL_CAMERAS

    print(f'Connecting to Jetson at {jetson_ip} (profile={args.profile})')
    print(f'Cameras: {[n for n, _, _ in cameras]}')
    print('Press Q to quit. JPEG fallback: python windows_camera_receiver_udp.py')
    if not args.front_only:
        print('Tip: freezes on Tailscale → try --front-only (3 streams fight UDP loss)')

    # Open Front first so a dead side stream doesn't block the known-good cam.
    open_order = sorted(cameras, key=lambda c: 0 if c[0] == 'Front' else 1)

    queues = {name: queue.Queue(maxsize=1) for name, _, _ in cameras}
    readers = []
    active = []  # (name, port, x_offset) that actually opened

    for name, port, x_offset in open_order:
        try:
            readers.append(ZedStreamReader(name, jetson_ip, port, queues[name]))
            active.append((name, port, x_offset))
        except RuntimeError as e:
            print(e)
            print(f'[{name}] Skipping — other cameras may still work.')

    if not readers:
        print('No streams opened.')
        print('Hint: on Jetson run:')
        print('  bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --discover')
        print('  bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --all')
        print('Also need ZED SDK + pyzed on this PC (docs/H265_BRINGUP.md Phase 0).')
        sys.exit(1)

    print(f'Open: {[n for n, _, _ in active]}')
    windows_created = {name: False for name, _, _ in active}
    last_frame = {name: None for name, _, _ in active}

    try:
        while True:
            for name, _, x_offset in active:
                try:
                    last_frame[name] = queues[name].get_nowait()
                except queue.Empty:
                    pass

                frame = last_frame[name]
                if frame is None:
                    continue

                win = f'ZED {name}'
                if not windows_created[name]:
                    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
                    cv2.moveWindow(win, x_offset, 0)
                    if not args.native_size:
                        cv2.resizeWindow(win, 1920, 1080)
                    windows_created[name] = True

                cv2.imshow(win, frame)

            if cv2.waitKey(8) & 0xFF == ord('q'):
                break
    finally:
        for r in readers:
            r.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
