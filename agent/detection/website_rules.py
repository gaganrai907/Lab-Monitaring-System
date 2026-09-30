RESTRICTED_WEBSITES = {

    "AI": [
        "chatgpt.com",
        "openai.com",
        "gemini.google.com",
        "claude.ai",
        "copilot.microsoft.com",
        "perplexity.ai",
    ],

    "GAME": [
        "roblox.com",
        "steampowered.com",
        "epicgames.com",
        "miniclip.com",
        "poki.com",
        "crazygames.com",
    ],
}


def detect_website(title):
    """
    Detect restricted website from browser window title.
    """

    title_lower = title.lower()

    for category, websites in RESTRICTED_WEBSITES.items():

        for website in websites:

            domain_name = website.split(".")[0]

            if website.lower() in title_lower:
                return {
                    "category": category,
                    "website": website,
                    "title": title,
                }

            if domain_name.lower() in title_lower:
                return {
                    "category": category,
                    "website": website,
                    "title": title,
                }

    return None