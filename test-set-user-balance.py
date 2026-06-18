import sqlite3

USERNAME = "WhoIsTRBS"
NEW_BALANCE = int(input("Enter Dev Balance: "))

db = sqlite3.connect("casino.db")

db.execute(
    "UPDATE users SET balance = ? WHERE username = ?",
    (NEW_BALANCE, USERNAME),
)

db.commit()
db.close()

print(f"Balance updated for {USERNAME}: {NEW_BALANCE}")