import sqlite3

conn = sqlite3.connect('users.db')
cursor = conn.cursor()

# Check all messages
cursor.execute('SELECT * FROM messages ORDER BY id DESC LIMIT 10')
messages = cursor.fetchall()
print("Recent messages:")
for msg in messages:
    print(f"ID: {msg[0]}, User: {msg[1]}, Sender: {msg[2]}, Message: {msg[3]}, Time: {msg[4]}")

# Check for media messages
cursor.execute('SELECT * FROM messages WHERE message LIKE "%[image]%" OR message LIKE "%[video]%" OR message LIKE "%[voice]%" OR message LIKE "%[audio]%" ORDER BY id DESC LIMIT 5')
media_messages = cursor.fetchall()
print("\nMedia messages:")
for msg in media_messages:
    print(f"ID: {msg[0]}, User: {msg[1]}, Sender: {msg[2]}, Message: {msg[3]}, Time: {msg[4]}")

conn.close() 