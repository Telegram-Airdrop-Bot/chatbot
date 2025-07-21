from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest
import config  # <-- config.py import করুন

app = Client(
    "AutoApproveBot",
    bot_token=config.BOT_TOKEN,
    api_id=config.API_ID,
    api_hash=config.API_HASH
)

CHAT_ID = config.CHAT_ID
WELCOME_TEXT = getattr(config, "WELCOME_TEXT", "🎉 Hi {mention}, you are now a member of {title}!")

print("Bot is running and waiting for join requests...")

@app.on_chat_join_request(filters.chat(CHAT_ID))
async def approve_and_dm(client: Client, join_request: ChatJoinRequest):
    user = join_request.from_user
    chat = join_request.chat

    await client.approve_chat_join_request(chat.id, user.id)
    print(f"Approved: {user.first_name} ({user.id}) in {chat.title}")

    try:
        await client.send_message(
            user.id,
            WELCOME_TEXT.format(mention=user.mention, title=chat.title)
        )
        print(f"DM sent to {user.first_name} ({user.id})")
    except Exception as e:
        print(f"Failed to send DM to {user.first_name} ({user.id}): {e}")

app.run()