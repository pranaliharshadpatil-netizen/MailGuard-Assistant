import sqlite3

# Connect (creates file if not exists)
conn = sqlite3.connect("mailguard.db")
cursor = conn.cursor()

# Create table for storing emails
cursor.execute("""
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT,
    subject TEXT,
    body TEXT,
    category TEXT,
    spam_score INTEGER,
    reasons TEXT,
    date TEXT
)
""")

# Create table for user feedback (learning system)
cursor.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id INTEGER,
    action TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(email_id) REFERENCES emails(id)
)
""")

conn.commit()
conn.close()
print("✅ Database and tables created successfully!")
