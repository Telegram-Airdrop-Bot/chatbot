# Telegram Bot Features

## Features
- Private channel creation and management
- Bot acts as admin in the private channel
- Bot generates and provides private channel invite links
- Welcome message for new users (with invite link)
- Welcome back message for returning users
- Admin dashboard (React) for real-time chat with users
- Admin can send broadcast and individual messages
- Real-time updates via Flask-SocketIO
- User and message storage in SQLite database
- Channel invite link fetchable from dashboard
- Messenger-style chat UI for admin
- Only new users get the channel invite link
- CORS and credentials set up for cross-origin requests

## Bot Workflow
1. **User starts the bot**: User sends /start to the bot.
2. **New user**: Bot saves user info, sends welcome message with channel invite link.
3. **Returning user**: Bot sends a simple welcome back message.
4. **User joins channel**: User uses the invite link to join the private channel.
5. **User messages bot**: Messages are saved and shown in the admin dashboard in real time.
6. **Admin replies**: Admin sends messages from dashboard; user receives them as bot messages.
7. **Broadcast**: Admin can send a message to all users from the dashboard.
8. **Invite link**: Admin can fetch the current channel invite link from the dashboard.

## Technologies Used
- Python (Flask, Flask-SocketIO, python-telegram-bot)
- React (admin dashboard)
- SQLite (database)

---
For deployment and configuration, see `instruction.md`. 