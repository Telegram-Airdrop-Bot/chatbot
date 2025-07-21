import sqlite3
import asyncio
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from threading import Thread
from config import BOT_TOKEN
import datetime

app = Flask(__name__)
app.secret_key = 'change_this_secret_key'
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"], supports_credentials=True)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000"])

DB_NAME = 'users.db'

# --- Database helpers ---
def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT user_id, full_name, username, join_date FROM users')
    users = c.fetchall()
    conn.close()
    return users

def get_total_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total = c.fetchone()[0]
    conn.close()
    return total

def get_messages_for_user(user_id, limit=100):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT sender, message, timestamp FROM messages WHERE user_id = ? ORDER BY id ASC LIMIT ?', (user_id, limit))
    messages = c.fetchall()
    conn.close()
    return messages

def save_message(user_id, sender, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, sender, message, timestamp) VALUES (?, ?, ?, ?)',
              (user_id, sender, message, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def add_user(user_id, full_name, username, join_date):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, full_name, username, join_date) VALUES (?, ?, ?, ?)', (user_id, full_name, username, join_date))
    conn.commit()
    conn.close()

# --- Flask API Endpoints ---
@app.route('/dashboard-users')
def dashboard_users():
    users = get_all_users()
    return jsonify([
        {
            'user_id': u[0],
            'full_name': u[1],
            'username': u[2],
            'join_date': u[3]
        } for u in users
    ])

@app.route('/dashboard-stats')
def dashboard_stats():
    total_users = get_total_users()
    return jsonify({
        'total_users': total_users
    })

@app.route('/chat/<int:user_id>/messages')
def chat_messages(user_id):
    messages = get_messages_for_user(user_id)
    if not messages:
        return '<div class="text-center text-muted">No messages yet.</div>'
    html = ''
    for sender, message, timestamp in messages:
        sender_class = 'admin' if sender == 'admin' else 'user'
        sender_label = 'Assistant' if sender == 'admin' else 'User'
        html += f'<div class="chat-bubble {sender_class}"><b>{sender_label}:</b> {message}<div class="chat-meta">{timestamp}</div></div>'
    return html

@app.route('/chat/<int:user_id>', methods=['POST'])
def chat_send(user_id):
    message = request.form.get('message')
    if not message:
        return '', 400
    save_message(user_id, 'admin', message)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.send_message(chat_id=int(user_id), text=message))
        loop.close()
    except Exception as e:
        print(f"Telegram send error: {e}")
    socketio.emit('new_message', {'user_id': user_id}, room='chat_' + str(user_id))
    return '', 204

@app.route('/send_one', methods=['POST'])
def send_one():
    user_id = request.form.get('user_id')
    message = request.form.get('message')
    if not user_id or not message:
        return {'status': 'error', 'msg': 'Missing user_id or message'}, 400
    save_message(int(user_id), 'admin', message)
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot.send_message(chat_id=int(user_id), text=message))
        loop.close()
    except Exception as e:
        print(f"Telegram send error: {e}")
    socketio.emit('new_message', {'user_id': int(user_id)}, room='chat_' + str(user_id))
    return {'status': 'ok'}

@app.route('/send_all', methods=['POST'])
def send_all():
    message = request.form.get('message')
    if not message:
        return {'status': 'error', 'msg': 'Missing message'}, 400
    users = get_all_users()
    for u in users:
        save_message(u[0], 'admin', message)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(bot.send_message(chat_id=int(u[0]), text=message))
            loop.close()
        except Exception as e:
            print(f"Telegram send error: {e}")
        socketio.emit('new_message', {'user_id': u[0]}, room='chat_' + str(u[0]))
    return {'status': 'ok', 'count': len(users)}

@socketio.on('join')
def on_join(data):
    room = data.get('room')
    join_room(room)

# --- Telegram Bot Handlers ---
bot = Bot(BOT_TOKEN)

async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = user.username or ''
    join_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    add_user(user.id, full_name, username, join_date)
    save_message(user.id, 'user', update.message.text)
    # Real-time notify admin dashboard
    socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome! You can chat with the admin here.')

# --- Start Telegram Bot in a Thread ---
def run_telegram_bot():
    app_builder = ApplicationBuilder().token(BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler('start', start))
    app_builder.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message_handler))
    app_builder.run_polling()

if __name__ == '__main__':
    # Start Flask-SocketIO in a thread
    flask_thread = Thread(target=lambda: socketio.run(app, port=5001, debug=True), daemon=True)
    flask_thread.start()

    # Start Telegram bot polling in main thread
    app_builder = ApplicationBuilder().token(BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler('start', start))
    app_builder.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message_handler))
    app_builder.run_polling() 