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
from detection.active_window import detect_browser
from detection.website_rules import detect_website


# ============================================================
# DEVICE INFORMATION
# ============================================================

def get_device_id():
    try:
        machine_id = uuid.getnode()
        return f"{machine_id:012x}"
    except Exception:
        return socket.gethostname()


DEVICE_ID = get_device_id()
HOSTNAME = socket.gethostname()


# ============================================================
# SERVER HEADERS
# ============================================================

def headers():
    return {
        "X-API-Key": SERVER_API_KEY
    }


# ============================================================
# DETECTION STATE
# ============================================================

LAST_DETECTED_GAMES = set()
LAST_DETECTED_WEBSITE = None


# ============================================================
# REGISTER PC
# ============================================================

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


# ============================================================
# HEARTBEAT
# ============================================================

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


# ============================================================
# GAME ALERT
# ============================================================

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


# ============================================================
# WEBSITE ALERT
# ============================================================

def send_website_alert(website):

    url = f"{SERVER_URL}/api/alerts"

    data = {
        "device_id": DEVICE_ID,
        "alert_type": "RESTRICTED_WEBSITE",
        "title": "Restricted Website Detected",
        "message": (
            f"{website['website']} "
            f"({website['category']}) detected on "
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
            f"🚨 Website alert sent: "
            f"{website['website']} "
            f"(Alert ID: {result['alert_id']})"
        )

        return True

    except requests.RequestException as error:

        print("❌ Website alert failed:")
        print(error)

        return False


# ============================================================
# CHECK GAMES
# ============================================================

def check_games():

    global LAST_DETECTED_GAMES

    games = detect_games()

    current_games = set()

    for game in games:

        game_key = (
            f"{game['process']}:"
            f"{game['pid']}"
        )

        current_games.add(game_key)

        if game_key in LAST_DETECTED_GAMES:
            continue

        print(
            f"🎮 GAME DETECTED: "
            f"{game['game']} "
            f"PID={game['pid']}"
        )

        send_game_alert(game)

    LAST_DETECTED_GAMES = current_games


# ============================================================
# CHECK WEBSITE
# ============================================================

def check_website():

    global LAST_DETECTED_WEBSITE

    browser = detect_browser()

    # No browser active
    if not browser:

        if LAST_DETECTED_WEBSITE is not None:

            print("🌐 Browser no longer active.")

        LAST_DETECTED_WEBSITE = None

        return


    browser_name = browser["browser"]
    title = browser["title"]

    # Show current browser window
    print(
        f"🌐 Browser: {browser_name} | "
        f"Title: {title}"
    )


    # Check website
    website = detect_website(title)


    # Normal website
    if not website:

        if LAST_DETECTED_WEBSITE is not None:

            print(
                "✅ Restricted website no longer active."
            )

        LAST_DETECTED_WEBSITE = None

        return


    # Website key
    website_key = (
        f"{website['category']}:"
        f"{website['website']}"
    )


    # Already detected
    if website_key == LAST_DETECTED_WEBSITE:

        return


    # New restricted website
    print("")
    print("🚨 RESTRICTED WEBSITE DETECTED")
    print(
        f"Category : {website['category']}"
    )
    print(
        f"Website  : {website['website']}"
    )
    print(
        f"Title    : {website['title']}"
    )
    print("")


    # Send server alert
    success = send_website_alert(website)


    # Only remember if alert was successfully sent
    if success:

        LAST_DETECTED_WEBSITE = website_key


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("COLLEGE LAB MONITORING AGENT")
    print("=" * 60)

    print(f"Lab       : {LAB_NAME}")
    print(f"PC Number : {PC_NUMBER}")
    print(f"Hostname  : {HOSTNAME}")
    print(f"Device ID : {DEVICE_ID}")

    print("=" * 60)


    # Register PC
    register_pc()

    print("🚀 Agent started.")
    print("🌐 Website monitoring enabled.")
    print("🎮 Game monitoring enabled.")
    print("")


    while True:

        try:

            # Heartbeat
            send_heartbeat()

            # Game detection
            check_games()

            # Website detection
            check_website()

        except Exception as error:

            print("")
            print("❌ Agent error:")
            print(error)
            print("")


        time.sleep(HEARTBEAT_INTERVAL)


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()