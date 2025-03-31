import sqlite3
import datetime
from typing import List, Optional, Tuple, Dict, Any

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
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create events table for statistics
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL,
            user_id INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT,
            success INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
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
        
        # Record the check event
        self.log_event("check", None, {"value": value, "result": result}, result)
        
        return result

    def get_all_whitelist(self) -> List[str]:
        """Get all values in the whitelist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM whitelist")
        result = [row[0] for row in cursor.fetchall()]
        conn.close()
        return result
    
    def get_whitelist_count(self) -> int:
        """Get the count of items in the whitelist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM whitelist")
        result = cursor.fetchone()[0]
        conn.close()
        return result

    def add_user(self, user_id: int, username: Optional[str], first_name: str, 
                 last_name: Optional[str], chat_id: int) -> bool:
        """Add or update a user in the database"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Check if user already exists
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                # Update existing user's last activity
                cursor.execute("""
                    UPDATE users 
                    SET username = ?, first_name = ?, last_name = ?, chat_id = ?, last_activity = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (username, first_name, last_name, chat_id, user_id))
            else:
                # Insert new user
                cursor.execute("""
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, chat_id) 
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, username, first_name, last_name, chat_id))
                
                # Log new user event
                self.log_event("new_user", user_id)
                
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            return False
    
    def update_user_activity(self, user_id: int) -> bool:
        """Update user's last activity timestamp"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET last_activity = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error updating user activity: {e}")
            return False
    
    def get_all_users(self) -> List[Tuple[int, int]]:
        """Get all users' IDs and chat IDs for broadcasting"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, chat_id FROM users")
        result = cursor.fetchall()
        conn.close()
        return result
    
    def get_users_count(self) -> int:
        """Get the total number of users"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        result = cursor.fetchone()[0]
        conn.close()
        return result
    
    def get_new_users_count(self, days: int = 7) -> int:
        """Get the number of new users in the last N days"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE joined_at >= datetime('now', ?)
        """, (f'-{days} days',))
        result = cursor.fetchone()[0]
        conn.close()
        return result
    
    def get_active_users_count(self, days: int = 7) -> int:
        """Get the number of active users in the last N days"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE last_activity >= datetime('now', ?)
        """, (f'-{days} days',))
        result = cursor.fetchone()[0]
        conn.close()
        return result
    
    def log_event(self, event_type: str, user_id: Optional[int], data: dict = None, success: bool = True) -> bool:
        """Log an event for statistics"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Convert data dict to string if provided
            data_str = str(data) if data else None
            
            cursor.execute("""
                INSERT INTO events (event_type, user_id, data, success, timestamp)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (event_type, user_id, data_str, 1 if success else 0))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error logging event: {e}")
            return False
    
    def get_event_count(self, event_type: str, days: int = 7, success: Optional[bool] = None) -> int:
        """Get the count of specific events in the last N days"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        query = """
            SELECT COUNT(*) FROM events 
            WHERE event_type = ? AND timestamp >= datetime('now', ?)
        """
        params = [event_type, f'-{days} days']
        
        if success is not None:
            query += " AND success = ?"
            params.append(1 if success else 0)
        
        cursor.execute(query, params)
        result = cursor.fetchone()[0]
        conn.close()
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        stats = {
            "users": {
                "total": self.get_users_count(),
                "new_7d": self.get_new_users_count(7),
                "new_1d": self.get_new_users_count(1),
                "active_7d": self.get_active_users_count(7)
            },
            "whitelist": {
                "total": self.get_whitelist_count()
            },
            "checks": {
                "total_7d": self.get_event_count("check", 7),
                "successful_7d": self.get_event_count("check", 7, True),
                "failed_7d": self.get_event_count("check", 7, False),
                "total_1d": self.get_event_count("check", 1),
                "successful_1d": self.get_event_count("check", 1, True),
                "failed_1d": self.get_event_count("check", 1, False)
            },
            "daily_activity": self.get_daily_activity()
        }
        return stats
    
    def get_daily_activity(self) -> Dict[str, int]:
        """Get activity count by day of week for the last 30 days"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # SQLite's strftime('%w') returns 0-6 with 0 being Sunday
        cursor.execute("""
            SELECT 
                CASE strftime('%w', timestamp)
                    WHEN '0' THEN 'Воскресенье'
                    WHEN '1' THEN 'Понедельник'
                    WHEN '2' THEN 'Вторник'
                    WHEN '3' THEN 'Среда'
                    WHEN '4' THEN 'Четверг'
                    WHEN '5' THEN 'Пятница'
                    WHEN '6' THEN 'Суббота'
                END as day_of_week,
                COUNT(*) as count
            FROM events
            WHERE timestamp >= datetime('now', '-30 days')
            GROUP BY day_of_week
            ORDER BY strftime('%w', timestamp)
        """)
        
        result = cursor.fetchall()
        conn.close()
        
        # Convert to dictionary
        activity_by_day = {day: count for day, count in result}
        return activity_by_day 