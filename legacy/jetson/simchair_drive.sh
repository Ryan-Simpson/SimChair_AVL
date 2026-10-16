#!/bin/bash
# simchair_drive.sh — temporary Teensy borrow for sim-chair teleop
#
# While running: WebUI stopped, vehicle controller owns /dev/ttyACM0 + UDP 5006
# On exit (Ctrl+C): full avros-webui.service restarted (not just actuator_node)
#
# Usage:
#   bash ~/Documents/SimChair_Teleop/simchair_drive.sh
# Stop:
#   Ctrl+C   OR   pkill -f orin_vehicle_controller
#
# Drive mode: open-loop duty (UL/UR). Override:
#   VEHICLE_ARGS="--velocity" bash .../simchair_drive.sh

TELEOP_DIR="${TELEOP_DIR:-$HOME/Documents/SimChair_Teleop}"
SERIAL_PORT="${SERIAL_PORT:-/dev/ttyACM0}"
UDP_PORT="${UDP_PORT:-5006}"
VEHICLE_ARGS="${VEHICLE_ARGS:---duty}"

GUARD_PID=""
RESTORED=0

restore_webui() {
    # Ctrl+C fires INT then EXIT — only restore once
    if [[ "${RESTORED}" -eq 1 ]]; then
        return 0
    fi
    RESTORED=1

    # Disable trap so nested kills don't re-enter
    trap - EXIT INT TERM

    echo ""
    echo "[simchair_drive] Restoring full Chrome WebUI (avros-webui.service)..."

    if [[ -n "${GUARD_PID}" ]] && kill -0 "${GUARD_PID}" 2>/dev/null; then
        kill "${GUARD_PID}" 2>/dev/null || true
        wait "${GUARD_PID}" 2>/dev/null || true
    fi
    GUARD_PID=""

    pkill -f orin_vehicle_controller.py 2>/dev/null || true
    # Clear any orphan actuator we (or a bad restore) started outside systemd
    pkill -f actuator_node 2>/dev/null || true
    sleep 1

    if ! sudo systemctl restart avros-webui; then
        echo "[simchair_drive] ERROR: systemctl restart avros-webui failed."
        echo "  Run manually:  sudo systemctl restart avros-webui"
        echo "  Then:          systemctl status avros-webui --no-pager"
        return 1
    fi

    # Wait for HTTPS :8000 + Teensy owner
    local i
    for i in $(seq 1 20); do
        if ss -ltnp 2>/dev/null | grep -q ':8000 ' \
            && pgrep -f actuator_node >/dev/null 2>&1; then
            echo "[simchair_drive] WebUI restored — open https://100.93.121.3:8000"
            echo "  Teensy: sudo lsof ${SERIAL_PORT}   (expect actuator_node only)"
            systemctl is-active avros-webui --quiet && echo "  service: active"
            return 0
        fi
        sleep 0.5
    done

    echo "[simchair_drive] WARNING: service restarted but :8000 / actuator not ready yet."
    echo "  systemctl status avros-webui --no-pager | head -20"
    echo "  ss -ltnp | grep 8000"
    echo "  sudo lsof ${SERIAL_PORT}"
    return 1
}

trap restore_webui EXIT INT TERM

echo "============================================"
echo " SimChair drive (borrows Teensy + UDP ${UDP_PORT})"
echo " Vehicle: orin_vehicle_controller.py ${VEHICLE_ARGS}"
echo " Stop with Ctrl+C → full WebUI restored"
echo "============================================"

# Full stop — Chrome needs webui_node on :8000, not actuator alone
sudo systemctl stop avros-webui 2>/dev/null || true
pkill -f orin_vehicle_controller.py 2>/dev/null || true
pkill -f actuator_node 2>/dev/null || true
sleep 1

if [[ ! -e "${SERIAL_PORT}" ]]; then
    echo "ERROR: ${SERIAL_PORT} missing. Plug in Teensy USB first."
    ls -l /dev/ttyACM* 2>/dev/null || true
    exit 1
fi

# UDP 5006 must be free for vehicle controller
if ss -ulnp 2>/dev/null | grep -q ":${UDP_PORT} "; then
    echo "[simchair_drive] UDP ${UDP_PORT} still in use after stopping WebUI:"
    ss -ulnp 2>/dev/null | grep ":${UDP_PORT} " || true
    if pgrep -af orin_vehicle_controller >/dev/null 2>&1; then
        pkill -f orin_vehicle_controller.py 2>/dev/null || true
        sleep 0.5
    fi
    if ss -ulnp 2>/dev/null | grep -q ":${UDP_PORT} "; then
        echo "ERROR: UDP ${UDP_PORT} still held. Free it, then retry."
        exit 1
    fi
fi

(
    while true; do
        pkill -f actuator_node 2>/dev/null || true
        sleep 2
    done
) &
GUARD_PID=$!
echo "[simchair_drive] Guard PID ${GUARD_PID} (holds actuator off while driving)"

echo "[simchair_drive] Starting vehicle controller (${VEHICLE_ARGS})..."
set +u
# shellcheck disable=SC2086
/usr/bin/python3 "${TELEOP_DIR}/orin_vehicle_controller.py" ${VEHICLE_ARGS}
status=$?
set -u
exit "${status}"
