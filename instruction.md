# Deployment & Configuration Instructions

## 1. Prerequisites
- Python 3.8+
- Node.js & npm (for React dashboard)
- Telegram bot token
- Channel ID and invite link

## 2. Setup & Installation

### Backend (Flask + Bot)
1. Clone the repository and navigate to the project folder.
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Edit `config.py` and set:
   - `BOT_TOKEN` (your Telegram bot token)
   - `CHANNEL_ID` (your private channel ID)
   - `GROUP_INVITE_LINK` (your channel invite link)
   - `DASHBOARD_PASSWORD` (set a strong password)
4. Run the backend:
   ```bash
   python api.py
   ```
   The backend will start on port 5001.

### Frontend (React Dashboard)
1. Navigate to the `admin-dashboard-react` folder:
   ```bash
   cd admin-dashboard-react
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the dashboard:
   ```bash
   npm start
   ```
   The dashboard will run on port 3000.

## 3. Changing Configuration
- To change bot token, channel ID, invite link, or admin password, edit `config.py` and restart the backend.
- To change dashboard UI or logic, edit files in `admin-dashboard-react/src/` and restart the React app.

## 4. Common Issues & Troubleshooting
- **Bot not sending messages:** Ensure the bot token is correct and the user has started the bot.
- **Event loop errors:** Use `asyncio.run_coroutine_threadsafe` for async Telegram calls (already implemented).
- **CORS errors:** Make sure backend allows requests from `localhost:3000`.
- **Socket.IO not connecting:** Ensure the React app connects to `http://localhost:5001`.
- **404 errors on API calls:** Use full backend URLs (e.g., `http://localhost:5001/send_one`).
- **Bot can't detect channel joins:** Telegram bots can't detect channel joins directly; users must start the bot for private chat.

## 5. Useful Tips
- Always restart the backend after changing `config.py`.
- For production, use a process manager (e.g., `pm2`, `supervisor`) and serve the React app with a production server.
- Keep your bot token and dashboard password secure.

---
For feature details and workflow, see `featured.md`. 