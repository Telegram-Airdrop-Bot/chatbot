import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()
print(f"{'User ID':<15} {'Full Name':<25} {'Username':<20} {'Invite Link'}")
print('-'*90)
for row in c.execute("SELECT user_id, full_name, username, invite_link FROM users"):
    print(f"{row[0]:<15} {row[1] or '':<25} {row[2] or '':<20} {row[3] or ''}")
conn.close() 