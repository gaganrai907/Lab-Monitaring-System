import os

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SERVER_URL = os.getenv("SERVER_URL")
SERVER_API_KEY = os.getenv("SERVER_API_KEY")


def server_headers():
    return {
        "X-API-Key": SERVER_API_KEY
    }


def get_user(telegram_id):
    try:
        response = requests.get(
            f"{SERVER_URL}/api/users/{telegram_id}",
            headers=server_headers(),
            timeout=10
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        return response.json()["user"]

    except requests.RequestException as error:
        print("User authentication error:", error)
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    db_user = get_user(str(user.id))

    if not db_user:
        await update.message.reply_text(
            "❌ Access Denied\n\n"
            "Aapka Telegram account College Lab Monitoring System "
            "me authorized nahi hai.\n\n"
            "Apna Telegram ID HOD ko bhejiye."
        )
        return

    role = db_user["role"]

    if role == "HOD":

        menu = (
            "👑 HOD Control Panel\n\n"
            "🖥️ /pcs - All Lab PC Status\n"
            "🚨 /alerts - Latest Alerts\n"
            "🏫 /labs - Lab Information\n"
            "⚙️ /help - All Commands"
        )

    elif role == "FACULTY":

        menu = (
            "👨‍🏫 Faculty Panel\n\n"
            "🖥️ /pcs - Assigned Lab PC Status\n"
            "🚨 /alerts - Latest Alerts\n"
            "🏫 /labs - Assigned Lab\n"
            "⚙️ /help - All Commands"
        )

    else:

        menu = (
            "👤 User Panel\n\n"
            "⚙️ /help - Available Commands"
        )

    await update.message.reply_text(
        f"👋 Welcome, {db_user['name']}!\n\n"
        f"Role: {role}\n\n"
        f"{menu}"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    db_user = get_user(str(user.id))

    if not db_user:

        await update.message.reply_text(
            "❌ Unauthorized user."
        )

        return

    if db_user["role"] == "HOD":

        await update.message.reply_text(
            "👑 HOD Commands\n\n"
            "/start - Open HOD Panel\n"
            "/pcs - Show All Lab PCs\n"
            "/alerts - Show Latest Alerts\n"
            "/labs - Show Labs\n"
            "/id - Show Telegram ID"
        )

    elif db_user["role"] == "FACULTY":

        await update.message.reply_text(
            "👨‍🏫 Faculty Commands\n\n"
            "/start - Open Faculty Panel\n"
            "/pcs - Show Assigned Lab PCs\n"
            "/alerts - Show Latest Alerts\n"
            "/labs - Show Assigned Lab\n"
            "/id - Show Telegram ID"
        )


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    await update.message.reply_text(
        f"👤 Your Telegram Information\n\n"
        f"Name: {user.full_name}\n"
        f"Username: @{user.username if user.username else 'Not set'}\n"
        f"Telegram ID: `{user.id}`",
        parse_mode="Markdown"
    )


async def pcs(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    db_user = get_user(str(user.id))

    if not db_user:

        await update.message.reply_text(
            "❌ Access Denied."
        )

        return

    try:

        response = requests.get(
            f"{SERVER_URL}/api/pcs",
            headers=server_headers(),
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        if data["count"] == 0:

            await update.message.reply_text(
                "❌ No PCs registered."
            )

            return

        role = db_user["role"]
        assigned_lab = db_user["assigned_lab"]

        message = "🖥️ *Lab PC Status*\n\n"

        visible_pcs = 0

        for pc in data["pcs"]:

            if role == "FACULTY":

                if pc["lab_name"] != assigned_lab:
                    continue

            if pc["status"] == "ONLINE":
                status_icon = "🟢"
            else:
                status_icon = "🔴"

            message += (
                f"{status_icon} *{pc['lab_name']}*\n"
                f"PC: `{pc['pc_number']}`\n"
                f"Host: `{pc['hostname']}`\n"
                f"Status: `{pc['status']}`\n\n"
            )

            visible_pcs += 1

        if visible_pcs == 0:

            await update.message.reply_text(
                "❌ No PCs found for your assigned lab."
            )

            return

        await update.message.reply_text(
            message,
            parse_mode="Markdown"
        )

    except requests.RequestException as error:

        print("Server error:", error)

        await update.message.reply_text(
            "❌ Central server se connection nahi ho paya."
        )


async def alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    db_user = get_user(str(user.id))

    if not db_user:

        await update.message.reply_text(
            "❌ Access Denied."
        )

        return

    try:

        response = requests.get(
            f"{SERVER_URL}/api/alerts",
            headers=server_headers(),
            timeout=10
        )

        response.raise_for_status()

        data = response.json()

        if data["count"] == 0:

            await update.message.reply_text(
                "✅ No alerts found."
            )

            return

        message = "🚨 *Latest Alerts*\n\n"

        for alert in data["alerts"][:10]:

            severity = alert["severity"]

            if severity == "HIGH":
                icon = "🔴"
            elif severity == "WARNING":
                icon = "🟠"
            else:
                icon = "🔵"

            lab_name = alert["lab_name"] or "Unknown Lab"
            pc_number = alert["pc_number"] or "Unknown PC"

            message += (
                f"{icon} *{alert['title']}*\n"
                f"🏫 Lab: `{lab_name}`\n"
                f"🖥️ PC: `{pc_number}`\n"
                f"🎯 Type: `{alert['alert_type']}`\n"
                f"📝 {alert['message']}\n"
                f"⚠️ Severity: `{severity}`\n"
                f"🕐 `{alert['created_at']}`\n\n"
            )

        await update.message.reply_text(
            message,
            parse_mode="Markdown"
        )

    except requests.RequestException as error:

        print("Alert server error:", error)

        await update.message.reply_text(
            "❌ Server se alerts nahi mil pa rahe hain."
        )


async def labs(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    db_user = get_user(str(user.id))

    if not db_user:

        await update.message.reply_text(
            "❌ Access Denied."
        )

        return

    if db_user["role"] == "HOD":

        await update.message.reply_text(
            "🏫 Lab Management\n\n"
            "👑 HOD Access: All Laboratories"
        )

    elif db_user["role"] == "FACULTY":

        await update.message.reply_text(
            f"🏫 Assigned Laboratory\n\n"
            f"Lab: {db_user['assigned_lab'] or 'Not assigned'}"
        )


def main():

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing in .env"
        )

    if not SERVER_URL:
        raise RuntimeError(
            "SERVER_URL is missing in .env"
        )

    print("🤖 Starting College Lab Monitor Bot...")

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("help", help_command)
    )

    application.add_handler(
        CommandHandler("id", id_command)
    )

    application.add_handler(
        CommandHandler("pcs", pcs)
    )

    application.add_handler(
        CommandHandler("alerts", alerts)
    )

    application.add_handler(
        CommandHandler("labs", labs)
    )

    print("✅ Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()