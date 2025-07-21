import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from config import BOT_TOKEN, GROUP_INVITE_LINK, ADMIN_USER_ID, WELCOME_MESSAGE, GROUP_CHAT_ID
from db import init_db, add_user, get_total_users, get_all_users, save_message
import datetime
import requests

logging.basicConfig(level=logging.INFO)

# Initialize DB
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler('dashboard', dashboard))
    app.add_handler(MessageHandler(filters.TEXT & filters.REPLY, handle_admin_reply))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.REPLY, user_message_handler))

    app.run_polling()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton('Join Group', callback_data='join_group')],
        [InlineKeyboardButton('Cancel', callback_data='cancel')]
    ]
    await update.message.reply_text('Welcome! Choose an option:', reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
        if query.data == 'join_group':
            keyboard = [
                [InlineKeyboardButton('Request to Join', callback_data='request_join')],
                [InlineKeyboardButton('Cancel', callback_data='cancel')]
            ]
            await query.edit_message_text('Do you want to join the group?', reply_markup=InlineKeyboardMarkup(keyboard))
        elif query.data == 'request_join':
            user = query.from_user
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            username = user.username or ''
            join_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            add_user(user.id, full_name, username, join_date)
            # Generate unique invite link for this user
            invite_link = None
            try:
                chat = await context.bot.create_chat_invite_link(chat_id=GROUP_CHAT_ID, member_limit=1, name=f"{full_name} ({user.id})")
                invite_link = chat.invite_link
            except Exception as e:
                logging.error(f"Failed to create invite link: {e}")
                invite_link = GROUP_INVITE_LINK  # fallback
            await query.edit_message_text(f'You have been approved! Click below to join the group.',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('Join Group', url=invite_link)]]))
            await context.bot.send_message(chat_id=user.id, text=WELCOME_MESSAGE)
        elif query.data == 'cancel':
            await query.edit_message_text('Action cancelled.')
    except Exception as e:
        logging.error(f"Error in button_handler: {e}")

async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text('Unauthorized.')
        return
    total = get_total_users()
    keyboard = [
        [InlineKeyboardButton('Send Message to One', callback_data='send_one')],
        [InlineKeyboardButton('Send Message to All', callback_data='send_all')]
    ]
    await update.message.reply_text(f'Total users: {total}', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if update.message.reply_to_message:
        if 'Send message to user:' in update.message.reply_to_message.text:
            user_id = int(update.message.reply_to_message.text.split(':')[-1].strip())
            await context.bot.send_message(chat_id=user_id, text=update.message.text)
            await update.message.reply_text('Message sent.')
        elif 'Send message to all users' in update.message.reply_to_message.text:
            for user_id in get_all_users():
                try:
                    await context.bot.send_message(chat_id=user_id, text=update.message.text)
                except Exception:
                    pass
            await update.message.reply_text('Message sent to all users.')

async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = user.username or ''
    join_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Ensure user is in DB
    add_user(user.id, full_name, username, join_date)
    # Save message
    save_message(user.id, 'user', update.message.text)
    # Notify admin dashboard for real-time pop-up
    try:
        requests.post(
            "http://localhost:5000/notify-admin",
            json={
                "user_id": user.id,
                "full_name": full_name,
                "username": username
            },
            timeout=1
        )
    except Exception as e:
        logging.error(f"Failed to notify admin dashboard: {e}")
    # Optionally, you can send an auto-reply or just do nothing
    # await update.message.reply_text("Thank you for your message! Our team will get back to you soon.")

if __name__ == '__main__':
    main() 