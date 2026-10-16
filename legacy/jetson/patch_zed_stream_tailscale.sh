#!/bin/bash
# patch_zed_stream_tailscale.sh
# Tune stream_server for Tailscale: lower bitrate, smaller chunk_size, adaptive BR.
# Run ON Jetson. Does NOT restart cameras — relaunch percept after.
#
#   bash ~/Documents/SimChair_Teleop/patch_zed_stream_tailscale.sh
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
    echo "[err] no stream_server in ${f} — run patch_zed_stream_ports.sh first"
    exit 1
  fi

  local bak="${f}.bak.tailscale_$(date +%Y%m%d_%H%M%S)"
  cp -a "${f}" "${bak}"
  echo "[bak] ${bak}"

  python3 - "${f}" "${port}" "${bitrate}" <<'PY'
import sys, re
path, port, bitrate = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding="utf-8").read()
block = f"""    # SimChair H.265 stream — Tailscale-friendly (smaller chunks)
    stream_server:
      port: {port}
      bitrate: {bitrate}
      chunk_size: 4096
      adaptative_bitrate: true
"""
# Replace existing stream_server section (comment + block) if present
pat = re.compile(
    r"(?:[ \t]*# SimChair H\.265 stream[^\n]*\n)?"
    r"[ \t]*stream_server:\n"
    r"(?:[ \t]+[^\n]+\n)+",
    re.M,
)
new, n = pat.subn(block, text, count=1)
if n != 1:
    print(f"[err] expected 1 stream_server block in {path}, found {n}")
    sys.exit(1)
open(path, "w", encoding="utf-8").write(new)
print(f"[ok] {path} → port={port} bitrate={bitrate} chunk_size=4096 adaptive=true")
PY
}

patch_file "${CFG}/zed_front.yaml" 30000 5000
patch_file "${CFG}/zed_left.yaml"  30004 3500
patch_file "${CFG}/zed_right.yaml" 30008 3500

echo ""
grep -A6 stream_server "${CFG}/zed_front.yaml" "${CFG}/zed_left.yaml" "${CFG}/zed_right.yaml"

echo ""
echo "Next:"
echo "  # symlink-install: src already used if you built with --symlink-install"
echo "  sudo systemctl restart percept-stack"
echo "  # wait until active, then:"
echo "  bash ~/Documents/SimChair_Teleop/simchair_enable_zed_streams.sh --all"
echo "  ss -ulnp | grep -E '30000|30004|30008'"
