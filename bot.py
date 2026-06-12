import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

BOT_TOKEN = "8703083706:AAGErnqq5Bod296TLDTPbt72XRG-3yskd-U"
ADMIN_IDS = [513723806]
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"accounts": [], "users": {}, "banned": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    data = load_data()

    if uid in data["banned"]:
        await update.message.reply_text("❌ شما بن شده‌اید.")
        return

    if uid in data["users"]:
        acc = data["users"][uid]
        await update.message.reply_text(
            f"✅ اکانت شما:\n\n👤 یوزرنیم: `{acc['username']}`\n🔑 پسورد: `{acc['password']}`",
            parse_mode="Markdown"
        )
        return

    if not data["accounts"]:
        await update.message.reply_text("⚠️ اکانتی موجود نیست. بعداً تلاش کنید.")
        return

    acc = data["accounts"].pop(0)
    data["users"][uid] = {
        "username": acc["username"],
        "password": acc["password"],
        "name": user.full_name,
        "telegram_username": user.username or "ندارد"
    }
    save_data(data)
    await update.message.reply_text(
        f"🎉 اکانت شما:\n\n👤 یوزرنیم: `{acc['username']}`\n🔑 پسورد: `{acc['password']}`",
        parse_mode="Markdown"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    keyboard = [
        [InlineKeyboardButton("👥 لیست کاربران", callback_data="list_users")],
        [InlineKeyboardButton("➕ افزودن اکانت", callback_data="add_account")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast")],
        [InlineKeyboardButton("📊 آمار", callback_data="stats")],
    ]
    await update.message.reply_text("🔧 پنل مدیریت:", reply_markup=InlineKeyboardMarkup(keyboard))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cb = query.data
    user = query.from_user

    if user.id not in ADMIN_IDS:
        return

    data = load_data()

    if cb == "stats":
        await query.edit_message_text(
            f"📊 آمار:\n\n🗂 اکانت باقی‌مانده: {len(data['accounts'])}\n"
            f"👥 کاربران: {len(data['users'])}\n🚫 بن‌شده: {len(data['banned'])}"
        )

    elif cb == "list_users":
        if not data["users"]:
            await query.edit_message_text("هیچ کاربری اکانت نگرفته.")
            return
        text = "👥 لیست کاربران:\n\n"
        keyboard = []
        for uid, info in data["users"].items():
            banned = uid in data["banned"]
            text += f"{'🚫' if banned else '✅'} {info['name']} | @{info['telegram_username']} | {uid}\n"
            keyboard.append([InlineKeyboardButton(
                f"{'آزاد کردن' if banned else 'بن کردن'} - {info['name']}",
                callback_data=f"{'unban' if banned else 'ban'}_{uid}"
            )])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif cb.startswith("ban_"):
        uid = cb[4:]
        if uid not in data["banned"]:
            data["banned"].append(uid)
            save_data(data)
        await query.edit_message_text(f"✅ کاربر {uid} بن شد.")

    elif cb.startswith("unban_"):
        uid = cb[6:]
        if uid in data["banned"]:
            data["banned"].remove(uid)
            save_data(data)
        await query.edit_message_text(f"✅ کاربر {uid} آزاد شد.")

    elif cb == "broadcast":
        context.user_data["awaiting_broadcast"] = True
        await query.edit_message_text("📢 متن پیام همگانی را بفرست:")

    elif cb == "add_account":
        context.user_data["awaiting_account"] = True
        await query.edit_message_text("➕ اکانت‌ها را بفرست:\n`username:password`\nهر خط یک اکانت", parse_mode="Markdown")

    elif cb == "back":
        keyboard = [
            [InlineKeyboardButton("👥 لیست کاربران", callback_data="list_users")],
            [InlineKeyboardButton("➕ افزودن اکانت", callback_data="add_account")],
            [InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast")],
            [InlineKeyboardButton("📊 آمار", callback_data="stats")],
        ]
        await query.edit_message_text("🔧 پنل مدیریت:", reply_markup=InlineKeyboardMarkup(keyboard))

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        return

    if context.user_data.get("awaiting_account"):
        context.user_data["awaiting_account"] = False
        lines = update.message.text.strip().splitlines()
        data = load_data()
        added = 0
        for line in lines:
            if ":" in line:
                u, p = line.split(":", 1)
                data["accounts"].append({"username": u.strip(), "password": p.strip()})
                added += 1
        save_data(data)
        await update.message.reply_text(f"✅ {added} اکانت اضافه شد.")
        return

    if context.user_data.get("awaiting_broadcast"):
        context.user_data["awaiting_broadcast"] = False
        msg = update.message.text
        data = load_data()
        success, fail = 0, 0
        for uid in data["users"]:
            try:
                await context.bot.send_message(chat_id=int(uid), text=msg)
                success += 1
            except:
                fail += 1
        await update.message.reply_text(f"📢 ارسال شد:\n✅ موفق: {success}\n❌ ناموفق: {fail}")

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("ربات در حال اجراست...")
    app.run_polling()

if __name__ == "__main__":
    main()
