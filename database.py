import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name="rats_sx.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Tabla de estafadores
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS scammers (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                blacklisted INTEGER DEFAULT 0
            )
        """)
        
        # Historial de nombres
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS name_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                old_name TEXT,
                change_date TEXT,
                FOREIGN KEY(user_id) REFERENCES scammers(user_id)
            )
        """)
        
        # Historial de usernames
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS username_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                old_username TEXT,
                change_date TEXT,
                FOREIGN KEY(user_id) REFERENCES scammers(user_id)
            )
        """)
        
        # Tabla de reportes (aprobados)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scammer_id INTEGER,
                context TEXT,
                bank_details TEXT,
                reporter_id INTEGER,
                approver_id INTEGER,
                proof_photo_id TEXT,
                created_at TEXT
            )
        """)
        
        # Tabla de reportes pendientes
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS pending_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scammer_id INTEGER,
                scammer_username TEXT,
                scammer_name TEXT,
                context TEXT,
                bank_details TEXT,
                reporter_id INTEGER,
                proof_photo_id TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        
        self.conn.commit()

    def get_scammer(self, identifier):
        # identifier can be ID or username
        if isinstance(identifier, int) or identifier.isdigit():
            self.cursor.execute("SELECT * FROM scammers WHERE user_id = ?", (identifier,))
        else:
            username = identifier.replace("@", "")
            self.cursor.execute("SELECT * FROM scammers WHERE username = ?", (username,))
        return self.cursor.fetchone()

    def get_reports_count(self, user_id):
        self.cursor.execute("SELECT COUNT(*) FROM reports WHERE scammer_id = ?", (user_id,))
        return self.cursor.fetchone()[0]

    def get_name_history(self, user_id):
        self.cursor.execute("SELECT old_name, change_date FROM name_history WHERE user_id = ? ORDER BY id DESC", (user_id,))
        return self.cursor.fetchall()

    def get_username_history(self, user_id):
        self.cursor.execute("SELECT old_username, change_date FROM username_history WHERE user_id = ? ORDER BY id DESC", (user_id,))
        return self.cursor.fetchall()

    def get_pending_reports_count(self, user_id):
        self.cursor.execute("SELECT COUNT(*) FROM pending_reports WHERE scammer_id = ? AND status = 'pending'", (user_id,))
        return self.cursor.fetchone()[0]

    def add_pending_report(self, scammer_id, scammer_username, scammer_name, context, bank_details, reporter_id, proof_photo_id):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO pending_reports 
            (scammer_id, scammer_username, scammer_name, context, bank_details, reporter_id, proof_photo_id, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (scammer_id, scammer_username, scammer_name, context, bank_details, reporter_id, proof_photo_id, now))
        self.conn.commit()
        return self.cursor.lastrowid

    def add_report(self, scammer_id, name, username, context, bank_details, reporter_id, approver_id, proof_photo_id):
        # Check if scammer exists
        self.cursor.execute("SELECT name, username FROM scammers WHERE user_id = ?", (scammer_id,))
        existing = self.cursor.fetchone()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not existing:
            self.cursor.execute("INSERT INTO scammers (user_id, name, username, blacklisted) VALUES (?, ?, ?, 1)", 
                               (scammer_id, name, username))
        else:
            # Update and log history if changed
            if existing[0] != name:
                self.cursor.execute("INSERT INTO name_history (user_id, old_name, change_date) VALUES (?, ?, ?)", 
                                   (scammer_id, existing[0], now))
                self.cursor.execute("UPDATE scammers SET name = ? WHERE user_id = ?", (name, scammer_id))
            
            if existing[1] != username:
                self.cursor.execute("INSERT INTO username_history (user_id, old_username, change_date) VALUES (?, ?, ?)", 
                                   (scammer_id, existing[1], now))
                self.cursor.execute("UPDATE scammers SET username = ? WHERE user_id = ?", (username, scammer_id))
            
            self.cursor.execute("UPDATE scammers SET blacklisted = 1 WHERE user_id = ?", (scammer_id,))

        self.cursor.execute("""
            INSERT INTO reports (scammer_id, context, bank_details, reporter_id, approver_id, proof_photo_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (scammer_id, context, bank_details, reporter_id, approver_id, proof_photo_id, now))
        
        report_id = self.cursor.lastrowid
        self.conn.commit()
        return report_id

db = Database()
