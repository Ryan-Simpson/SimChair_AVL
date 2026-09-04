#!/bin/bash
# patch_zed_stream_3cam_stable.sh
# Aggressive Tailscale-safe tuning for THREE simultaneous ZED streams.
# chunk_size must stay under Tailscale MTU (~1280) or you get freezes/tears.
#
#   bash ~/Documents/SimChair_Teleop/patch_zed_stream_3cam_stable.sh
#   then: sudo systemctl restart percept-stack → wait for 3 zed_node → --all
#
set -euo pipefail

CFG="/home/dinosaur/IGVC/src/avros_bringup/config"

patch_file() {
  local f="$1"
  local port="$2"
  local bitrate="$3"

  if [[ ! -f "${f}" ]]; then
    echo "[err] missing ${f}"
    exit 1
  fi
  if ! grep -qE '^[[:space:]]*stream_server:' "${f}"; then
    echo "[err] no stream_server in ${f}"
    exit 1
  fi

  local bak="${f}.bak.3cam_$(date +%Y%m%d_%H%M%S)"
  cp -a "${f}" "${bak}"
  echo "[bak] ${bak}"

  python3 - "${f}" "${port}" "${bitrate}" <<'PY'
import sys, re
path, port, bitrate = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding="utf-8").read()
block = f"""    # SimChair H.265 — 3-cam Tailscale stable (chunk < MTU ~1280)
    stream_server:
      port: {port}
      bitrate: {bitrate}
      chunk_size: 1024
      gop_size: 30
      target_framerate: 15
      adaptative_bitrate: true
"""
pat = re.compile(
    r"(?:[ \t]*# SimChair H\.265[^\n]*\n)?"
    r"[ \t]*stream_server:\n"
    r"(?:[ \t]+[^\n]+\n)+",
    re.M,
)
new, n = pat.subn(block, text, count=1)
if n != 1:
    print(f"[err] expected 1 stream_server block in {path}, found {n}")
    sys.exit(1)
open(path, "w", encoding="utf-8").write(new)
print(f"[ok] {path} → port={port} bitrate={bitrate} chunk=1024 fps=15")
PY
}

# Slightly more bitrate on front (drive cam); sides leaner
patch_file "${CFG}/zed_front.yaml" 30000 4000
patch_file "${CFG}/zed_left.yaml"  30004 2500
patch_file "${CFG}/zed_right.yaml" 30008 2500

echo ""
grep -A8 stream_server "${CFG}/zed_front.yaml" "${CFG}/zed_left.yaml" "${CFG}/zed_right.yaml"

echo ""
echo "Next:"
echo "  sudo systemctl restart percept-stack"
echo "  # wait until all 3 zed_node up, chunk_size==1024"
echo "  bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --all"
echo "  # Windows: py -3.8 windows_zed_stream_receiver.py --native-size"
echo "  # Also: tailscale ping Jetson — want direct, not DERP relay"
