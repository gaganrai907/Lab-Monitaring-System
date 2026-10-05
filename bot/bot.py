import os
from datetime import datetime, timezone
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    ""
).strip()

SERVER_URL = os.getenv(
    "SERVER_URL",
    ""
).strip().rstrip("/")

SERVER_API_KEY = os.getenv(
    "SERVER_API_KEY",
    ""
).strip()


# ============================================================
# CONSTANTS
# ============================================================

REQUEST_TIMEOUT = 10
ALERT_CHECK_INTERVAL = 5

ALLOWED_ROLES = {
    "HOD",
    "FACULTY",
}


# ============================================================
# SERVER API
# ============================================================

def server_headers():
    """
    Headers used for communication with central server.
    """

    headers = {
        "Accept": "application/json",
    }

    if SERVER_API_KEY:
        headers["X-API-Key"] = SERVER_API_KEY

    return headers


def api_request(
    method,
    endpoint,
    **kwargs
):
    """
    Common API request handler.

    Returns:
        requests.Response | None
    """

    if not SERVER_URL:
        print("❌ SERVER_URL is not configured.")
        return None

    url = (
        f"{SERVER_URL}/"
        f"{endpoint.lstrip('/')}"
    )

    headers = kwargs.pop(
        "headers",
        {}
    )

    final_headers = server_headers()
    final_headers.update(headers)

    try:

        response = requests.request(
            method=method,
            url=url,
            headers=final_headers,
            timeout=REQUEST_TIMEOUT,
            **kwargs
        )

        response.raise_for_status()

        return response

    except requests.Timeout:

        print(
            f"❌ Server timeout: {url}"
        )

    except requests.ConnectionError:

        print(
            f"❌ Server connection failed: {url}"
        )

    except requests.HTTPError as error:

        status_code = (
            error.response.status_code
            if error.response
            else "UNKNOWN"
        )

        print(
            f"❌ HTTP error "
            f"{status_code}: {url}"
        )

        if error.response is not None:
            try:
                print(
                    "Server response:",
                    error.response.text
                )
            except Exception:
                pass

    except requests.RequestException as error:

        print(
            f"❌ Request error: {error}"
        )

    except Exception as error:

        print(
            f"❌ Unexpected API error: {error}"
        )

    return None


# ============================================================
# SAFE JSON
# ============================================================

def response_json(response):

    if response is None:
        return None

    try:

        return response.json()

    except ValueError:

        print(
            "❌ Server returned invalid JSON."
        )

        return None


# ============================================================
# USER
# ============================================================

def get_user(telegram_id):

    response = api_request(
        "GET",
        f"/api/users/{telegram_id}"
    )

    if response is None:
        return None

    if response.status_code == 404:
        return None

    data = response_json(response)

    if not data:
        return None

    return data.get("user")


# ============================================================
# USERS
# ============================================================

def get_all_users():

    response = api_request(
        "GET",
        "/api/users"
    )

    if response is None:
        return []

    data = response_json(response)

    if not data:
        return []

    users = data.get(
        "users",
        []
    )

    if not isinstance(users, list):
        return []

    return users


# ============================================================
# ALERTS
# ============================================================

def get_alerts():

    response = api_request(
        "GET",
        "/api/alerts"
    )

    if response is None:
        return []

    data = response_json(response)

    if not data:
        return []

    alerts = data.get(
        "alerts",
        []
    )

    if not isinstance(alerts, list):
        return []

    return alerts


# ============================================================
# IST TIME
# ============================================================

def format_ist_time(iso_time):

    if not iso_time:
        return "Unknown time"

    try:

        dt = datetime.fromisoformat(
            str(iso_time).replace(
                "Z",
                "+00:00"
            )
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        dt = dt.astimezone(
            ZoneInfo("Asia/Kolkata")
        )

        return (
            dt.strftime(
                "%d %b %Y, %I:%M %p"
            )
            + " IST"
        )

    except Exception:

        return str(iso_time)


# ============================================================
# ALERT FILTERING
# ============================================================

def filter_alerts_for_user(
    alerts,
    db_user
):

    if not db_user:
        return []

    role = db_user.get(
        "role",
        ""
    )

    if role == "HOD":
        return alerts

    if role == "FACULTY":

        assigned_lab = db_user.get(
            "assigned_lab"
        )

        if not assigned_lab:
            return []

        return [
            alert
            for alert in alerts
            if alert.get("lab_name")
            == assigned_lab
        ]

    return []


# ============================================================
# ALERT FORMAT
# ============================================================

def format_alert(alert):

    severity = str(
        alert.get(
            "severity",
            "INFO"
        )
    ).upper()

    if severity == "HIGH":

        icon = "🔴"

    elif severity == "WARNING":

        icon = "🟠"

    else:

        icon = "🔵"

    lab_name = (
        alert.get("lab_name")
        or "Unknown Lab"
    )

    pc_number = (
        alert.get("pc_number")
        or "Unknown PC"
    )

    title = (
        alert.get("title")
        or "Lab Alert"
    )

    alert_type = (
        alert.get("alert_type")
        or "Unknown"
    )

    message = (
        alert.get("message")
        or "No additional information."
    )

    alert_time = format_ist_time(
        alert.get("created_at")
    )

    return (
        "🚨 *NEW LAB ALERT*\n\n"
        f"{icon} *{title}*\n\n"
        f"🏫 Lab: `{lab_name}`\n"
        f"🖥️ PC: `{pc_number}`\n"
        f"🎯 Type: `{alert_type}`\n"
        f"📝 {message}\n"
        f"⚠️ Severity: `{severity}`\n"
        f"🕐 `{alert_time}`"
    )


# ============================================================
# MAIN MENU
# ============================================================

def main_menu(role):

    buttons = [
        [
            InlineKeyboardButton(
                "🖥️ PCs",
                callback_data="menu_pcs"
            ),
            InlineKeyboardButton(
                "🚨 Alerts",
                callback_data="menu_alerts"
            )
        ],
        [
            InlineKeyboardButton(
                "🏫 Labs",
                callback_data="menu_labs"
            ),
            InlineKeyboardButton(
                "⚙️ Restrictions",
                callback_data="menu_restrictions"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑️ Delete Alerts",
                callback_data="menu_delete_alerts"
            )
        ]
    ]

    return InlineKeyboardMarkup(
        buttons
    )


# ============================================================
# RESTRICTION KEYBOARD
# ============================================================

def restriction_keyboard(
    enabled
):

    status = (
        "🟢 ENABLED"
        if enabled
        else "🔴 DISABLED"
    )

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"🤖 AI Websites: {status}",
                callback_data="toggle_ai"
            )
        ],
        [
            InlineKeyboardButton(
                "🎮 Game Websites: 🔒 ALWAYS ON",
                callback_data="game_locked"
            )
        ],
        [
            InlineKeyboardButton(
                "🎮 Game Applications: 🔒 ALWAYS ON",
                callback_data="game_locked"
            )
        ]
    ])


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    user = update.effective_user

    db_user = get_user(
        str(user.id)
    )

    if not db_user:

        if update.message:

            await update.message.reply_text(
                "❌ *Access Denied*\n\n"
                "Aapka Telegram account "
                "College Lab Monitoring System "
                "me authorized nahi hai.\n\n"
                "Apna Telegram ID HOD ko bhejiye.",
                parse_mode="Markdown"
            )

        return

    role = db_user.get(
        "role",
        "UNKNOWN"
    )

    name = db_user.get(
        "name",
        user.full_name
    )

    await update.message.reply_text(
        f"👋 Welcome, {name}!\n\n"
        f"Role: *{role}*\n\n"
        "🎛️ *Control Panel*",
        parse_mode="Markdown",
        reply_markup=main_menu(role)
    )


# ============================================================
# HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not update.effective_user:
        return

    user = update.effective_user

    db_user = get_user(
        str(user.id)
    )

    if not db_user:

        await update.message.reply_text(
            "❌ Unauthorized user."
        )

        return

    role = db_user.get(
        "role",
        ""
    )

    message = (
        "📚 *College Lab Monitoring*\n\n"
        "/start - Control Panel\n"
        "/pcs - PC Status\n"
        "/alerts - Latest Alerts\n"
        "/labs - Lab Information\n"
        "/id - Telegram ID\n"
        "/restrictions - Restriction Settings\n"
        "/deletealerts - Delete Alert History\n"
    )

    if role == "HOD":

        message += (
            "\n👑 Role: HOD"
        )

    elif role == "FACULTY":

        message += (
            "\n👨‍🏫 Assigned Lab: "
            f"{db_user.get('assigned_lab') or 'Not assigned'}"
        )

    await update.message.reply_text(
        message,
        parse_mode="Markdown"
    )


# ============================================================
# TELEGRAM ID
# ============================================================

async def id_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    username = (
        f"@{user.username}"
        if user.username
        else "Not set"
    )

    await update.message.reply_text(
        "👤 *Your Telegram Information*\n\n"
        f"Name: {user.full_name}\n"
        f"Username: {username}\n"
        f"Telegram ID: `{user.id}`",
        parse_mode="Markdown"
    )


# ============================================================
# SHOW PCS
# ============================================================

async def show_pcs(
    chat_id,
    telegram_id,
    bot
):

    db_user = get_user(
        str(telegram_id)
    )

    if not db_user:

        await bot.send_message(
            chat_id=chat_id,
            text="❌ Access Denied."
        )

        return

    response = api_request(
        "GET",
        "/api/pcs"
    )

    if response is None:

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ Central server se "
                "connection nahi ho paya."
            )
        )

        return

    data = response_json(response)

    if not data:

        await bot.send_message(
            chat_id=chat_id,
            text="❌ Invalid server response."
        )

        return

    pcs_list = data.get(
        "pcs",
        []
    )

    if not pcs_list:

        await bot.send_message(
            chat_id=chat_id,
            text="❌ No PCs registered."
        )

        return

    role = db_user.get(
        "role"
    )

    assigned_lab = db_user.get(
        "assigned_lab"
    )

    message = "🖥️ *Lab PC Status*\n\n"

    visible_pcs = 0

    for pc in pcs_list:

        lab_name = (
            pc.get("lab_name")
            or "Unknown Lab"
        )

        if role == "FACULTY":

            if lab_name != assigned_lab:
                continue

        status = str(
            pc.get(
                "status",
                "OFFLINE"
            )
        ).upper()

        if status == "ONLINE":
            status_icon = "🟢"
        else:
            status_icon = "🔴"

        pc_number = (
            pc.get("pc_number")
            or "Unknown"
        )

        hostname = (
            pc.get("hostname")
            or "Unknown"
        )

        message += (
            f"{status_icon} *{lab_name}*\n"
            f"PC: `{pc_number}`\n"
            f"Host: `{hostname}`\n"
            f"Status: `{status}`\n\n"
        )

        visible_pcs += 1

    if visible_pcs == 0:

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "❌ No PCs found for "
                "your assigned lab."
            )
        )

        return

    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="Markdown"
    )


# ============================================================
# PCS COMMAND
# ============================================================

async def pcs(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    await show_pcs(
        update.effective_chat.id,
        user.id,
        context.bot
    )


# ============================================================
# SHOW ALERTS
# ============================================================

async def show_alerts(
    chat_id,
    telegram_id,
    bot
):

    db_user = get_user(
        str(telegram_id)
    )

    if not db_user:

        await bot.send_message(
            chat_id=chat_id,
            text="❌ Access Denied."
        )

        return

    alert_list = get_alerts()

    alert_list = filter_alerts_for_user(
        alert_list,
        db_user
    )

    if not alert_list:

        await bot.send_message(
            chat_id=chat_id,
            text="✅ No alerts found."
        )

        return

    message = "🚨 *Latest Alerts*\n\n"

    for alert in alert_list[:10]:

        severity = str(
            alert.get(
                "severity",
                "INFO"
            )
        ).upper()

        if severity == "HIGH":
            icon = "🔴"

        elif severity == "WARNING":
            icon = "🟠"

        else:
            icon = "🔵"

        lab_name = (
            alert.get("lab_name")
            or "Unknown Lab"
        )

        pc_number = (
            alert.get("pc_number")
            or "Unknown PC"
        )

        title = (
            alert.get("title")
            or "Lab Alert"
        )

        alert_type = (
            alert.get("alert_type")
            or "Unknown"
        )

        alert_message = (
            alert.get("message")
            or "No message"
        )

        alert_time = format_ist_time(
            alert.get("created_at")
        )

        message += (
            f"{icon} *{title}*\n"
            f"🏫 Lab: `{lab_name}`\n"
            f"🖥️ PC: `{pc_number}`\n"
            f"🎯 Type: `{alert_type}`\n"
            f"📝 {alert_message}\n"
            f"⚠️ Severity: `{severity}`\n"
            f"🕐 `{alert_time}`\n\n"
        )

    await bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="Markdown"
    )


# ============================================================
# ALERTS COMMAND
# ============================================================

async def alerts(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    await show_alerts(
        update.effective_chat.id,
        user.id,
        context.bot
    )


# ============================================================
# SHOW LABS
# ============================================================

async def show_labs(
    chat_id,
    telegram_id,
    bot
):

    db_user = get_user(
        str(telegram_id)
    )

    if not db_user:

        await bot.send_message(
            chat_id=chat_id,
            text="❌ Access Denied."
        )

        return

    role = db_user.get(
        "role"
    )

    if role == "HOD":

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🏫 *Lab Management*\n\n"
                "👑 HOD Access: "
                "All Laboratories"
            ),
            parse_mode="Markdown"
        )

    elif role == "FACULTY":

        assigned_lab = (
            db_user.get(
                "assigned_lab"
            )
            or "Not assigned"
        )

        await bot.send_message(
            chat_id=chat_id,
            text=(
                "🏫 *Assigned Laboratory*\n\n"
                f"Lab: `{assigned_lab}`"
            ),
            parse_mode="Markdown"
        )

    else:

        await bot.send_message(
            chat_id=chat_id,
            text="❌ You do not have permission."
        )


# ============================================================
# LABS COMMAND
# ============================================================

async def labs(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    await show_labs(
        update.effective_chat.id,
        user.id,
        context.bot
    )


# ============================================================
# GET AI RESTRICTION
# ============================================================

def get_ai_restriction():

    response = api_request(
        "GET",
        "/api/settings/ai-restriction"
    )

    if response is None:
        return None

    data = response_json(response)

    if not data:
        return None

    return data.get("enabled")


# ============================================================
# UPDATE AI RESTRICTION
# ============================================================

def update_ai_restriction(
    enabled
):

    response = api_request(
        "POST",
        "/api/settings/ai-restriction",
        json={
            "enabled": bool(enabled)
        }
    )

    if response is None:
        return None

    data = response_json(response)

    if not data:
        return None

    return data.get("enabled")


# ============================================================
# SHOW RESTRICTIONS
# ============================================================

async def show_restrictions(
    chat_id,
    telegram_id,
    bot,
    edit_message=None
):

    db_user = get_user(
        str(telegram_id)
    )

    if not db_user:

        text = "❌ Access Denied."

        if edit_message:

            await edit_message.edit_text(
                text
            )

        else:

            await bot.send_message(
                chat_id=chat_id,
                text=text
            )

        return

    role = db_user.get(
        "role"
    )

    if role not in ALLOWED_ROLES:

        text = (
            "❌ You do not have permission."
        )

        if edit_message:

            await edit_message.edit_text(
                text
            )

        else:

            await bot.send_message(
                chat_id=chat_id,
                text=text
            )

        return

    enabled = get_ai_restriction()

    if enabled is None:

        text = (
            "❌ Server se restriction "
            "status nahi mil raha."
        )

        if edit_message:

            await edit_message.edit_text(
                text
            )

        else:

            await bot.send_message(
                chat_id=chat_id,
                text=text
            )

        return

    ai_status = (
        "🟢 ENABLED"
        if enabled
        else "🔴 DISABLED"
    )

    text = (
        "⚙️ *Restriction Control*\n\n"
        f"🤖 AI Websites: *{ai_status}*\n"
        "🎮 Game Websites: *ALWAYS ON*\n"
        "🎮 Game Applications: *ALWAYS ON*\n\n"
        "AI restriction ko enable/disable "
        "karne ke liye button press karein."
    )

    keyboard = restriction_keyboard(
        enabled
    )

    if edit_message:

        await edit_message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    else:

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


# ============================================================
# RESTRICTIONS COMMAND
# ============================================================

async def restrictions(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    await show_restrictions(
        update.effective_chat.id,
        user.id,
        context.bot
    )


# ============================================================
# DELETE ALL ALERTS
# ============================================================

def delete_all_alerts():

    response = api_request(
        "DELETE",
        "/api/alerts"
    )

    if response is None:
        return None

    return response_json(
        response
    )


# ============================================================
# DELETE LAB ALERTS
# ============================================================

def delete_lab_alerts(
    lab_name
):

    encoded_lab = quote(
        str(lab_name),
        safe=""
    )

    response = api_request(
        "DELETE",
        f"/api/alerts/lab/{encoded_lab}"
    )

    if response is None:
        return None

    return response_json(
        response
    )


# ============================================================
# DELETE ALERT CONFIRMATION
# ============================================================

async def delete_alerts_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    if not user:
        return

    db_user = get_user(
        str(user.id)
    )

    is_callback = (
        update.callback_query is not None
    )

    if not db_user:

        text = "❌ Access Denied."

        if is_callback:

            await update.callback_query.edit_message_text(
                text
            )

        else:

            await update.message.reply_text(
                text
            )

        return

    role = db_user.get(
        "role"
    )

    if role == "HOD":

        text = (
            "⚠️ *Delete Alert History*\n\n"
            "Aap HOD hain.\n"
            "Isse *ALL LABS* ke alerts "
            "delete ho jayenge.\n\n"
            "Kya aap continue karna chahte hain?"
        )

        callback = "confirm_delete_all"

    elif role == "FACULTY":

        lab = db_user.get(
            "assigned_lab"
        )

        if not lab:

            text = (
                "❌ Aapke account me "
                "koi lab assigned nahi hai."
            )

            if is_callback:

                await update.callback_query.edit_message_text(
                    text
                )

            else:

                await update.message.reply_text(
                    text
                )

            return

        text = (
            "⚠️ *Delete Alert History*\n\n"
            "Sirf aapke assigned lab ke "
            "alerts delete honge:\n"
            f"🏫 `{lab}`\n\n"
            "Kya aap continue karna chahte hain?"
        )

        callback = "confirm_delete_lab"

    else:

        text = (
            "❌ You do not have permission."
        )

        if is_callback:

            await update.callback_query.edit_message_text(
                text
            )

        else:

            await update.message.reply_text(
                text
            )

        return

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🗑️ Yes, Delete",
                callback_data=callback
            ),
            InlineKeyboardButton(
                "❌ Cancel",
                callback_data="cancel_delete"
            )
        ]
    ])

    if is_callback:

        await update.callback_query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    else:

        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    if not query:
        return

    print(
        "🔘 BUTTON CALLBACK RECEIVED"
    )

    print(
        "Callback:",
        query.data
    )

    # Acknowledge callback immediately
    await query.answer()

    user = query.from_user

    db_user = get_user(
        str(user.id)
    )

    if not db_user:

        await query.edit_message_text(
            "❌ Access Denied."
        )

        return

    action = query.data

    # ========================================================
    # PCS
    # ========================================================

    if action == "menu_pcs":

        await show_pcs(
            query.message.chat_id,
            user.id,
            context.bot
        )

        return

    # ========================================================
    # ALERTS
    # ========================================================

    if action == "menu_alerts":

        await show_alerts(
            query.message.chat_id,
            user.id,
            context.bot
        )

        return

    # ========================================================
    # LABS
    # ========================================================

    if action == "menu_labs":

        await show_labs(
            query.message.chat_id,
            user.id,
            context.bot
        )

        return

    # ========================================================
    # RESTRICTIONS
    # ========================================================

    if action == "menu_restrictions":

        await show_restrictions(
            query.message.chat_id,
            user.id,
            context.bot
        )

        return

    # ========================================================
    # DELETE ALERTS
    # ========================================================

    if action == "menu_delete_alerts":

        await delete_alerts_command(
            update,
            context
        )

        return

    # ========================================================
    # TOGGLE AI
    # ========================================================

    if action == "toggle_ai":

        if db_user.get("role") not in ALLOWED_ROLES:

            await query.edit_message_text(
                "❌ You do not have permission."
            )

            return

        current = get_ai_restriction()

        if current is None:

            await query.edit_message_text(
                "❌ Server connection failed."
            )

            return

        new_status = not bool(
            current
        )

        result = update_ai_restriction(
            new_status
        )

        if result is None:

            await query.edit_message_text(
                "❌ AI restriction update failed."
            )

            return

        status_text = (
            "🟢 ENABLED"
            if result
            else "🔴 DISABLED"
        )

        keyboard = restriction_keyboard(
            result
        )

        await query.edit_message_text(
            "⚙️ *Restriction Control*\n\n"
            f"🤖 AI Websites: *{status_text}*\n"
            "🎮 Game Websites: *ALWAYS ON*\n"
            "🎮 Game Applications: *ALWAYS ON*\n\n"
            "✅ AI restriction updated successfully.",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

        return

    # ========================================================
    # GAME LOCKED
    # ========================================================

    if action == "game_locked":

        await query.answer(
            "🎮 Game restrictions are always enabled.",
            show_alert=True
        )

        return

    # ========================================================
    # CONFIRM DELETE ALL
    # ========================================================

    if action == "confirm_delete_all":

        if db_user.get("role") != "HOD":

            await query.edit_message_text(
                "❌ Only HOD can delete all alert history."
            )

            return

        result = delete_all_alerts()

        if result is None:

            await query.edit_message_text(
                "❌ Alert deletion failed."
            )

            return

        deleted = result.get(
            "deleted_count",
            0
        )

        await query.edit_message_text(
            "✅ *Alert History Deleted*\n\n"
            f"🗑️ Deleted alerts: `{deleted}`",
            parse_mode="Markdown"
        )

        return

    # ========================================================
    # CONFIRM DELETE LAB
    # ========================================================

    if action == "confirm_delete_lab":

        if db_user.get("role") != "FACULTY":

            await query.edit_message_text(
                "❌ Invalid permission."
            )

            return

        lab = db_user.get(
            "assigned_lab"
        )

        if not lab:

            await query.edit_message_text(
                "❌ No lab assigned to your account."
            )

            return

        result = delete_lab_alerts(
            lab
        )

        if result is None:

            await query.edit_message_text(
                "❌ Alert deletion failed."
            )

            return

        deleted = result.get(
            "deleted_count",
            0
        )

        await query.edit_message_text(
            "✅ *Lab Alert History Deleted*\n\n"
            f"🏫 Lab: `{lab}`\n"
            f"🗑️ Deleted alerts: `{deleted}`",
            parse_mode="Markdown"
        )

        return

    # ========================================================
    # CANCEL DELETE
    # ========================================================

    if action == "cancel_delete":

        await query.edit_message_text(
            "❌ Delete operation cancelled."
        )

        return

    # ========================================================
    # UNKNOWN CALLBACK
    # ========================================================

    await query.answer(
        "Unknown button action.",
        show_alert=True
    )


# ============================================================
# AUTOMATIC ALERT MONITOR
# ============================================================

async def monitor_alerts(
    context: ContextTypes.DEFAULT_TYPE
):

    try:

        alerts_list = get_alerts()

        if not alerts_list:
            return

        # Sort alerts by numeric ID if possible
        try:

            alerts_list = sorted(
                alerts_list,
                key=lambda alert: int(
                    alert.get("id", 0)
                )
            )

        except Exception:

            pass

        last_alert_id = (
            context.application.bot_data.get(
                "last_alert_id"
            )
        )

        # First execution:
        # mark latest alert and don't send old alerts
        if last_alert_id is None:

            if alerts_list:

                latest_id = alerts_list[-1].get(
                    "id"
                )

                context.application.bot_data[
                    "last_alert_id"
                ] = latest_id

                print(
                    "ℹ️ Existing alerts ignored. "
                    f"Starting from Alert ID={latest_id}"
                )

            return

        for alert in alerts_list:

            alert_id = alert.get(
                "id"
            )

            if alert_id is None:
                continue

            try:

                if int(alert_id) <= int(
                    last_alert_id
                ):
                    continue

            except Exception:

                if str(alert_id) == str(
                    last_alert_id
                ):
                    continue

            users = get_all_users()

            if not users:

                print(
                    "⚠️ No active users found."
                )

                continue

            message = format_alert(
                alert
            )

            for db_user in users:

                role = db_user.get(
                    "role"
                )

                if role not in ALLOWED_ROLES:
                    continue

                if not db_user.get(
                    "active",
                    False
                ):
                    continue

                # Faculty gets only assigned lab alerts
                if role == "FACULTY":

                    assigned_lab = db_user.get(
                        "assigned_lab"
                    )

                    alert_lab = alert.get(
                        "lab_name"
                    )

                    if (
                        not assigned_lab
                        or assigned_lab != alert_lab
                    ):
                        continue

                telegram_id = db_user.get(
                    "telegram_id"
                )

                if not telegram_id:
                    continue

                try:

                    await context.bot.send_message(
                        chat_id=telegram_id,
                        text=message,
                        parse_mode="Markdown"
                    )

                    print(
                        "📨 Automatic alert sent: "
                        f"Alert ID={alert_id} "
                        f"To={telegram_id}"
                    )

                except Exception as error:

                    print(
                        "❌ Telegram alert failed "
                        f"for {telegram_id}: {error}"
                    )

            context.application.bot_data[
                "last_alert_id"
            ] = alert_id

    except Exception as error:

        print(
            f"❌ Alert monitor error: {error}"
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    print(
        "❌ Telegram bot error:",
        context.error
    )


# ============================================================
# MAIN
# ============================================================

def main():

    # ========================================================
    # VALIDATE ENVIRONMENT
    # ========================================================

    if not TELEGRAM_BOT_TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing in .env"
        )

    if not SERVER_URL:

        raise RuntimeError(
            "SERVER_URL is missing in .env"
        )

    if not SERVER_API_KEY:

        raise RuntimeError(
            "SERVER_API_KEY is missing in .env"
        )

    print(
        "============================================"
    )

    print(
        "🤖 Starting College Lab Monitor Bot..."
    )

    print(
        f"🌐 Server: {SERVER_URL}"
    )

    print(
        "============================================"
    )

    # ========================================================
    # APPLICATION
    # ========================================================

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .build()
    )

    # ========================================================
    # COMMANDS
    # ========================================================

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command
        )
    )

    application.add_handler(
        CommandHandler(
            "id",
            id_command
        )
    )

    application.add_handler(
        CommandHandler(
            "pcs",
            pcs
        )
    )

    application.add_handler(
        CommandHandler(
            "alerts",
            alerts
        )
    )

    application.add_handler(
        CommandHandler(
            "labs",
            labs
        )
    )

    application.add_handler(
        CommandHandler(
            "restrictions",
            restrictions
        )
    )

    application.add_handler(
        CommandHandler(
            "deletealerts",
            delete_alerts_command
        )
    )

    # ========================================================
    # BUTTONS
    # ========================================================

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    # ========================================================
    # ERROR HANDLER
    # ========================================================

    application.add_error_handler(
        error_handler
    )

    # ========================================================
    # AUTOMATIC ALERT MONITOR
    # ========================================================

    if application.job_queue is None:

        raise RuntimeError(
            "JobQueue is not available.\n"
            "Install it using:\n"
            "python -m pip install "
            "\"python-telegram-bot[job-queue]\""
        )

    application.job_queue.run_repeating(
        monitor_alerts,
        interval=ALERT_CHECK_INTERVAL,
        first=ALERT_CHECK_INTERVAL
    )

    # ========================================================
    # START
    # ========================================================

    print(
        "✅ Bot is running..."
    )

    print(
        "🚨 Automatic alert monitoring enabled."
    )

    print(
        "🇮🇳 IST time display enabled."
    )

    print(
        "⚙️ AI restriction control enabled."
    )

    print(
        "🗑️ Alert history deletion enabled."
    )

    print(
        "🔘 Button callbacks enabled."
    )

    print(
        "============================================"
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()