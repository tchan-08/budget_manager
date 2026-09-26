import sqlite3 as db

connection = db.connect("database.db")
cursor = connection.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

#bug fixed, balance not saving, now saved to a Info profile in database
query = """CREATE TABLE IF NOT EXISTS Info (
        key TEXT PRIMARY KEY,
        value FLOAT
        );"""
cursor.execute(query)
print("info table created")

#create goals table
query = """CREATE TABLE IF NOT EXISTS Goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    target FLOAT NOT NULL,
    deadline INTEGER NOT NULL,
    progress FLOAT DEFAULT 0,
    completed BOOLEAN DEFAULT 0,
    parent_id INTEGER DEFAULT NULL,
    priority TEXT CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH')) NOT NULL DEFAULT 'LOW',
    FOREIGN KEY(parent_id) REFERENCES Goals(id) ON DELETE SET NULL
);"""
cursor.execute(query)
print("goal table created")

#create recurring items table
query = """CREATE TABLE IF NOT EXISTS Recurring_Items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('INCOME', 'EXPENSE')) NOT NULL,
    target FLOAT NOT NULL,
    frequency INTEGER NOT NULL,
    start_date TEXT NOT NULL
);"""
cursor.execute(query)
print("recurring_item table created")

#create transactions table
query = """CREATE TABLE IF NOT EXISTS Transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    type TEXT CHECK(type IN ('INCOME', 'EXPENSE')) NOT NULL,
    amount FLOAT NOT NULL,
    date DATE NOT NULL,
    goal_id INTEGER,
    recurring_idw  INTEGER,
    is_savings BOOLEAN DEFAULT 0,
    FOREIGN KEY(goal_id) REFERENCES Goals(id) ON DELETE SET NULL,
    FOREIGN KEY(recurring_id) REFERENCES Recurring_Items(id) ON DELETE SET NULL
);"""
cursor.execute(query)
print("transactions table created")

connection.commit()
connection.close()