import time
import psutil


# Games/applications that should be monitored
GAME_PROCESSES = {
    "valorant.exe": "VALORANT",
    "csgo.exe": "Counter-Strike",
    "cs2.exe": "Counter-Strike 2",
    "minecraft.exe": "Minecraft",
    "robloxplayerbeta.exe": "Roblox",
    "fortnitelauncher.exe": "Fortnite",
    "fortniteclient-win64-shipping.exe": "Fortnite",
    "gta5.exe": "GTA V",
    "steam.exe": "Steam",
    "epicgameslauncher.exe": "Epic Games Launcher",
    "notepad.exe": "TEST GAME",
}


def get_running_processes():
    processes = []

    for process in psutil.process_iter(
        ["pid", "name"]
    ):
        try:
            name = process.info["name"]

            if name:
                processes.append({
                    "pid": process.info["pid"],
                    "name": name.lower()
                })

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess
        ):
            continue

    return processes


def detect_games():

    detected_games = []

    for process in get_running_processes():

        process_name = process["name"]

        if process_name in GAME_PROCESSES:

            detected_games.append({
                "pid": process["pid"],
                "process": process_name,
                "game": GAME_PROCESSES[process_name]
            })

    return detected_games


if __name__ == "__main__":

    print("=" * 50)
    print("GAME DETECTION TEST")
    print("=" * 50)

    while True:

        games = detect_games()

        if games:

            print("\n🎮 GAME DETECTED")

            for game in games:

                print(
                    f"Game    : {game['game']}\n"
                    f"Process : {game['process']}\n"
                    f"PID     : {game['pid']}\n"
                )

        else:

            print("✅ No configured game detected.")

        time.sleep(3)