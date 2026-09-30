import time

from active_window import detect_browser
from website_rules import detect_website


print("=" * 60)
print("WEBSITE DETECTION TEST")
print("=" * 60)
print("Open/switch browser websites.")
print("Press CTRL+C to stop.\n")


last_title = None

while True:

    browser = detect_browser()

    if browser:

        title = browser["title"]

        if title != last_title:

            result = detect_website(title)

            print("\n🌐 Browser:", browser["browser"])
            print("📄 Title  :", title)

            if result:
                print("🚨 RESTRICTED WEBSITE")
                print("Category :", result["category"])
                print("Website  :", result["website"])
            else:
                print("✅ Website allowed / not configured")

            last_title = title

    time.sleep(2)