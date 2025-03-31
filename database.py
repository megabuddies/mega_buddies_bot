import sqlite3
from typing import List, Optional, Tuple

class Database:
    def __init__(self, db_name: str = "mega_buddies.db"):
        self.db_name = db_name
        self._create_tables()

    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Create whitelist table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS whitelist (
            id INTEGER PRIMARY KEY,
            value TEXT UNIQUE
        )
        ''')
        
        # Create users table to track all bot users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            chat_id INTEGER UNIQUE,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()

    def add_to_whitelist(self, value: str) -> bool:
        """Add a value to the whitelist"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO whitelist (value) VALUES (?)", (value,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            # Value already exists
            conn.close()
            return False
        except Exception as e:
            print(f"Error adding to whitelist: {e}")
            conn.close()
            return False

    def remove_from_whitelist(self, value: str) -> bool:
        """Remove a value from the whitelist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM whitelist WHERE value = ?", (value,))
        affected = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return affected

    def check_whitelist(self, value: str) -> bool:
        """Check if a value exists in the whitelist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM whitelist WHERE value = ?", (value,))
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def get_all_whitelist(self) -> List[str]:
        """Get all values in the whitelist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM whitelist")
        result = [row[0] for row in cursor.fetchall()]
        conn.close()
        return result

    def add_user(self, user_id: int, username: Optional[str], first_name: str, 
                 last_name: Optional[str], chat_id: int) -> bool:
        """Add or update a user in the database"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, chat_id) 
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, chat_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def get_all_users(self) -> List[Tuple[int, int]]:
        """Get all users' IDs and chat IDs for broadcasting"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, chat_id FROM users")
        result = cursor.fetchall()
        conn.close()
        return result 