import win32gui
import win32process
import psutil


BROWSERS = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
}


def get_active_window():
    """
    Get currently active Windows application/window.
    """

    hwnd = win32gui.GetForegroundWindow()

    if not hwnd:
        return None

    title = win32gui.GetWindowText(hwnd)

    if not title:
        return None

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)

        process = psutil.Process(pid)

        process_name = process.name().lower()

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
        psutil.ZombieProcess,
    ):
        return None

    return {
        "title": title,
        "process": process_name,
        "pid": pid,
    }


def detect_browser():
    """
    Detect the currently active browser window.
    """

    window = get_active_window()

    if not window:
        return None

    browser_name = BROWSERS.get(window["process"])

    if not browser_name:
        return None

    return {
        "browser": browser_name,
        "process": window["process"],
        "pid": window["pid"],
        "title": window["title"],
    }


if __name__ == "__main__":

    print("=" * 60)
    print("ACTIVE BROWSER DETECTION TEST")
    print("=" * 60)

    print("\nOpen Chrome / Edge / Firefox and switch between windows.")
    print("Press CTRL+C to stop.\n")

    last_window = None

    while True:

        browser = detect_browser()

        if browser:

            current = (
                browser["browser"],
                browser["process"],
                browser["pid"],
                browser["title"],
            )

            if current != last_window:

                print("\n🌐 BROWSER DETECTED")

                print(f"Browser : {browser['browser']}")
                print(f"Process : {browser['process']}")
                print(f"PID     : {browser['pid']}")
                print(f"Title   : {browser['title']}")

                last_window = current

        else:

            last_window = None