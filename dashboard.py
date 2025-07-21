from gevent import monkey
monkey.patch_all()
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask import jsonify
from telegram import Bot
from db import get_total_users, get_all_users, get_messages_for_user, save_message
from config import BOT_TOKEN, DASHBOARD_PASSWORD
import asyncio
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS

app = Flask(__name__)
app.secret_key = 'change_this_secret_key'
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"], supports_credentials=True)
bot = Bot(BOT_TOKEN)
# SocketIO setup
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins=["http://localhost:3000", "http://127.0.0.1:3000"])

# Create a global event loop for the Flask app
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

BOOTSTRAP_HEAD = '''
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body { background: #f8f9fa; }
.card { box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
/* Messenger-style chat window */
.chat-popup {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 350px;
  max-width: 95vw;
  background: #fff;
  border-radius: 12px 12px 0 0;
  box-shadow: 0 4px 24px rgba(0,0,0,0.18);
  z-index: 9999;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-left: 10px;
}
.chat-popup-header {
  background: #007bff;
  color: #fff;
  padding: 10px 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: bold;
  cursor: pointer;
}
.chat-popup-body {
  background: #f4f4f4;
  padding: 10px;
  flex: 1 1 auto;
  overflow-y: auto;
  min-height: 120px;
  max-height: 350px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.chat-popup-footer {
  padding: 8px 10px;
  background: #f8f9fa;
  border-top: 1px solid #eee;
}
.chat-bubble { max-width: 70%; padding: 10px 15px; border-radius: 18px; margin-bottom: 8px; display: inline-block; }
.chat-bubble.user { background: #e9ecef; color: #222; align-self: flex-start; }
.chat-bubble.admin { background: #007bff; color: #fff; align-self: flex-end; margin-left: auto; }
.chat-meta { font-size: 0.8em; color: #888; margin-top: 2px; }
.minimize-btn, .close-btn { background: none; border: none; color: #fff; font-size: 1.2em; margin-left: 8px; cursor: pointer; }
.minimized { height: 40px !important; min-height: 0 !important; max-height: 40px !important; overflow: hidden !important; }
</style>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
'''

DASHBOARD_TEMPLATE = BOOTSTRAP_HEAD + '''
<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
  <div class="container-fluid">
    <span class="navbar-brand">Admin Dashboard</span>
    <a href="{{ url_for('logout') }}" class="btn btn-outline-light">Logout</a>
  </div>
</nav>
<div class="container">
  <div class="row g-4">
    <div class="col-md-4">
      <div class="card p-3 mb-4">
        <h5>Total Users</h5>
        <div class="display-4">{{ total_users }}</div>
      </div>
      <div class="card p-3 mb-4">
        <h5>Send Message to One User</h5>
        <form method="post" action="{{ url_for('send_one') }}">
          <div class="mb-2">
            <input type="number" class="form-control" name="user_id" placeholder="User ID" required>
          </div>
          <div class="mb-2">
            <input type="text" class="form-control" name="message" placeholder="Message" required>
          </div>
          <button type="submit" class="btn btn-primary w-100">Send</button>
        </form>
      </div>
      <div class="card p-3 mb-4">
        <h5>Send Message to All Users</h5>
        <form method="post" action="{{ url_for('send_all') }}">
          <div class="mb-2">
            <input type="text" class="form-control" name="message" placeholder="Message" required>
          </div>
          <button type="submit" class="btn btn-success w-100">Send to All</button>
        </form>
      </div>
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <div class="alert alert-info" role="alert">
            {% for msg in messages %}{{ msg }}<br>{% endfor %}
          </div>
        {% endif %}
      {% endwith %}
    </div>
    <div class="col-md-8">
      <div class="card p-3 mb-4">
        <h5>User List</h5>
        <div class="table-responsive">
          <table class="table table-striped table-hover">
            <thead><tr><th>#</th><th>User ID</th><th>Full Name</th><th>Username</th><th>Join Date</th><th>Invite Link</th><th>Chat</th></tr></thead>
            <tbody>
              {% for user in users %}
                <tr>
                  <td>{{ loop.index }}</td>
                  <td>{{ user[0] }}</td>
                  <td>{{ user[1] or '' }}</td>
                  <td>{% if user[2] %}@{{ user[2] }}{% endif %}</td>
                  <td>{{ user[3] or '' }}</td>
                  <td>{% if user[4] %}<a href="{{ user[4] }}" target="_blank">Invite Link</a>{% else %}-{% endif %}</td>
                  <td><button class="btn btn-sm btn-primary" onclick="openChatWindow({{ user[0] }}, {{ user[1]|tojson }}, {{ user[2]|tojson }})">Chat</button></td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>
<div id="chat-popups"></div>
<script>
var socket = io();
var openChats = {};
function openChatWindow(user_id, full_name, username) {
  full_name = full_name || 'User';
  username = username || '';
  if (openChats[user_id]) {
    document.getElementById('chat-popup-' + user_id).style.zIndex = 9999;
    return;
  }
  var popup = document.createElement('div');
  popup.className = 'chat-popup';
  popup.id = 'chat-popup-' + user_id;
  popup.innerHTML = `
    <div class="chat-popup-header" onclick="toggleMinimize(${user_id})">
      <span><b>${full_name}${username ? ' (@' + username + ')' : ''}</b></span>
      <span>
        <button class="minimize-btn" onclick="event.stopPropagation();toggleMinimize(${user_id})">_</button>
        <button class="close-btn" onclick="event.stopPropagation();closeChatWindow(${user_id})">&times;</button>
      </span>
    </div>
    <div class="chat-popup-body" id="chat-body-${user_id}"></div>
    <form class="chat-popup-footer" id="chat-form-${user_id}" autocomplete="off" onsubmit="return sendChatMessage(${user_id})">
      <div class="input-group">
        <input type="text" class="form-control" id="chat-input-${user_id}" placeholder="Type your reply as the assistant..." required autocomplete="off">
        <button class="btn btn-primary" type="submit">Send</button>
      </div>
    </form>
  `;
  document.getElementById('chat-popups').appendChild(popup);
  openChats[user_id] = true;
  fetchChatMessages(user_id);
  socket.emit('join', {room: 'chat_' + user_id});
}
function closeChatWindow(user_id) {
  var popup = document.getElementById('chat-popup-' + user_id);
  if (popup) popup.remove();
  delete openChats[user_id];
}
function toggleMinimize(user_id) {
  var popup = document.getElementById('chat-popup-' + user_id);
  if (popup) popup.classList.toggle('minimized');
}
function fetchChatMessages(user_id) {
  fetch(`/chat/${user_id}/messages`).then(r => r.text()).then(html => {
    var body = document.getElementById('chat-body-' + user_id);
    if (body) {
      body.innerHTML = html;
      body.scrollTop = body.scrollHeight;
    }
  }).catch(function(e) { console.error('Fetch chat messages error:', e); });
}
function sendChatMessage(user_id) {
  var input = document.getElementById('chat-input-' + user_id);
  var msg = input.value.trim();
  if (!msg) return false;
  fetch(`/chat/${user_id}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'message=' + encodeURIComponent(msg)
  }).then(() => {
    input.value = '';
    fetchChatMessages(user_id);
  });
  return false;
}
socket.on('connect', function() {
  for (var user_id in openChats) {
    socket.emit('join', {room: 'chat_' + user_id});
  }
});
socket.on('new_message', function(data) {
  var user_id = data.user_id;
  if (openChats[user_id]) {
    fetchChatMessages(user_id);
  }
});
</script>
'''

CHAT_TEMPLATE = BOOTSTRAP_HEAD + '''
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
  <div class="container-fluid">
    <a href="{{ url_for('dashboard') }}" class="navbar-brand">← Back to Dashboard</a>
    <a href="{{ url_for('logout') }}" class="btn btn-outline-light">Logout</a>
  </div>
</nav>
<div class="container">
  <div class="row justify-content-center">
    <div class="col-md-8">
      <div class="card p-3 mb-4">
        <h5>Chat with User {{ user_id }}</h5>
        <div id="chat-area" class="chat-area" style="max-height: 400px; overflow-y: auto; background: #f4f4f4; padding: 10px; border-radius: 5px;">
          {% for sender, message, timestamp in messages %}
            <div class="chat-bubble {{ sender }}">
              <b>{% if sender == 'admin' %}Assistant{% else %}User{% endif %}:</b> {{ message }}
              <div class="chat-meta">{{ timestamp }}</div>
            </div>
          {% endfor %}
        </div>
        <form method="post" action="{{ url_for('chat', user_id=user_id) }}" class="mt-3" id="reply-form" autocomplete="off">
          <div class="input-group">
            <input type="text" name="message" class="form-control" placeholder="Type your reply as the assistant..." required autocomplete="off">
            <button class="btn btn-primary" type="submit">Send</button>
          </div>
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="alert alert-info mt-2" role="alert">
              {% for msg in messages %}{{ msg }}<br>{% endfor %}
            </div>
          {% endif %}
        {% endwith %}
      </div>
    </div>
  </div>
</div>
<script>
var socket = io();
var user_id = {{ user_id }};
function scrollChatToBottom() {
  var chatArea = document.getElementById('chat-area');
  chatArea.scrollTop = chatArea.scrollHeight;
}
function fetchMessages() {
  fetch("{{ url_for('chat_messages', user_id=user_id) }}")
    .then(response => response.text())
    .then(html => {
      document.getElementById('chat-area').innerHTML = html;
      scrollChatToBottom();
    });
}
socket.on('connect', function() {
  socket.emit('join', {room: 'chat_' + user_id});
});
socket.on('new_message', function(data) {
  if (data.user_id == user_id) {
    fetchMessages();
  }
});
document.addEventListener('DOMContentLoaded', function() {
  scrollChatToBottom();
});
</script>
'''

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if request.form['password'] == DASHBOARD_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect password')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/dashboard')
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    total_users = get_total_users()
    users = get_all_users()
    return render_template_string(DASHBOARD_TEMPLATE, total_users=total_users, users=users)

@app.route('/dashboard-users')
def dashboard_users():
    if 'logged_in' not in session:
        return jsonify([])
    users = get_all_users()
    return jsonify([
        {
            'user_id': u[0],
            'full_name': u[1],
            'username': u[2],
            'join_date': u[3],
            'invite_link': u[4]
        } for u in users
    ])

@app.route('/dashboard-stats')
def dashboard_stats():
    if 'logged_in' not in session:
        return jsonify({})
    total_users = get_total_users()
    return jsonify({
        'total_users': total_users
    })

@app.route('/send_one', methods=['POST'])
def send_one():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    user_id = request.form['user_id']
    message = request.form['message']
    try:
        loop.run_until_complete(bot.send_message(chat_id=int(user_id), text=message))
        flash('Message sent to user.')
    except Exception as e:
        flash(f'Error: {e}')
    return redirect(url_for('dashboard'))

@app.route('/send_all', methods=['POST'])
def send_all():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    message = request.form['message']
    users = get_all_users()
    count = 0
    for user in users:
        try:
            loop.run_until_complete(bot.send_message(chat_id=int(user[0]), text=message))
            count += 1
        except Exception:
            pass
    flash(f'Message sent to {count} users.')
    return redirect(url_for('dashboard'))

@app.route('/notify-admin', methods=['POST'])
def notify_admin():
    data = request.json
    user_id = data.get('user_id')
    full_name = data.get('full_name')
    username = data.get('username')
    socketio.emit('new_message', {
        'user_id': user_id,
        'full_name': full_name,
        'username': username
    })
    return jsonify({'status': 'ok'})

@app.route('/chat/<int:user_id>', methods=['GET', 'POST'])
def chat(user_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        message = request.form['message']
        # Save admin message
        save_message(user_id, 'admin', message)
        # Send message to user via bot
        try:
            loop.run_until_complete(bot.send_message(chat_id=int(user_id), text=message))
            flash('Message sent to user.')
        except Exception as e:
            flash(f'Error: {e}')
        # Emit real-time update
        socketio.emit('new_message', {'user_id': user_id}, room='chat_' + str(user_id))
        return ('', 204) if request.headers.get('X-Requested-With') else redirect(url_for('chat', user_id=user_id))
    messages = get_messages_for_user(user_id)
    return render_template_string(CHAT_TEMPLATE, user_id=user_id, messages=messages)

@app.route('/chat/<int:user_id>/messages')
def chat_messages(user_id):
    if 'logged_in' not in session:
        return ''
    messages = get_messages_for_user(user_id)
    if not messages:
        return '<div class="text-center text-muted">No messages yet.</div>'
    html = ''
    for sender, message, timestamp in messages:
        sender_class = 'admin' if sender == 'admin' else 'user'
        sender_label = 'Assistant' if sender == 'admin' else 'User'
        html += f'<div class="chat-bubble {sender_class}"><b>{sender_label}:</b> {message}<div class="chat-meta">{timestamp}</div></div>'
    return html

# SocketIO event: join room
@socketio.on('join')
def on_join(data):
    room = data.get('room')
    join_room(room)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    socketio.run(app, debug=True) 