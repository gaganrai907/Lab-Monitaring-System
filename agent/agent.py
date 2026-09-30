import socket
import time
import uuid

import requests

from config import (
    SERVER_URL,
    SERVER_API_KEY,
    LAB_NAME,
    PC_NUMBER,
    AGENT_VERSION,
    HEARTBEAT_INTERVAL
)

from detection.process_detector import detect_games


def get_device_id():

    try:
        machine_id = uuid.getnode()
        return f"{machine_id:012x}"

    except Exception:

        return socket.gethostname()


DEVICE_ID = get_device_id()
HOSTNAME = socket.gethostname()


def headers():

    return {
        "X-API-Key": SERVER_API_KEY
    }


def register_pc():

    url = f"{SERVER_URL}/api/pcs/register"

    data = {
        "lab_name": LAB_NAME,
        "pc_number": PC_NUMBER,
        "device_id": DEVICE_ID,
        "hostname": HOSTNAME,
        "agent_version": AGENT_VERSION
    }

    try:

        response = requests.post(
            url,
            json=data,
            headers=headers(),
            timeout=10
        )

        response.raise_for_status()

        print("✅ PC registration successful.")

        return True

    except requests.RequestException as error:

        print("❌ Registration failed:")
        print(error)

        return False


def send_heartbeat():

    url = f"{SERVER_URL}/api/pcs/heartbeat"

    data = {
        "device_id": DEVICE_ID
    }

    try:

        response = requests.post(
            url,
            json=data,
            headers=headers(),
            timeout=10
        )

        response.raise_for_status()

        print("💓 Heartbeat sent.")

        return True

    except requests.RequestException as error:

        print("❌ Heartbeat failed:")
        print(error)

        return False


def send_game_alert(game):

    url = f"{SERVER_URL}/api/alerts"

    data = {
        "device_id": DEVICE_ID,
        "alert_type": "GAME_DETECTED",
        "title": "Game Detected",
        "message": (
            f"{game['game']} detected on "
            f"{LAB_NAME} {PC_NUMBER}"
        ),
        "severity": "HIGH"
    }

    try:

        response = requests.post(
            url,
            json=data,
            headers=headers(),
            timeout=10
        )

        response.raise_for_status()

        result = response.json()

        print(
            f"🚨 Game alert sent: "
            f"{game['game']} "
            f"(Alert ID: {result['alert_id']})"
        )

        return True

    except requests.RequestException as error:

        print("❌ Game alert failed:")
        print(error)

        return False

LAST_DETECTED_GAMES = set()

def check_games():

    global LAST_DETECTED_GAMES

    games = detect_games()

    current_games = set()

    for game in games:

        game_key = f"{game['process']}:{game['pid']}"

        current_games.add(game_key)

        # Already reported — don't send another alert
        if game_key in LAST_DETECTED_GAMES:
            continue

        print(
            f"🎮 GAME DETECTED: "
            f"{game['game']} "
            f"PID={game['pid']}"
        )

        send_game_alert(game)

    LAST_DETECTED_GAMES = current_games
    
def main():

    print("=" * 50)
    print("COLLEGE LAB MONITORING AGENT")
    print("=" * 50)

    print(f"Lab       : {LAB_NAME}")
    print(f"PC Number : {PC_NUMBER}")
    print(f"Hostname  : {HOSTNAME}")
    print(f"Device ID : {DEVICE_ID}")

    print("=" * 50)

    register_pc()

    print("🚀 Agent started.")

    while True:

        send_heartbeat()

        check_games()

        time.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    main()