import sqlite3
import datetime
from typing import List, Optional, Tuple, Dict, Any
from contextlib import contextmanager

class Database:
    def __init__(self, db_name: str = "mega_buddies.db"):
        self.db_name = db_name
        self._create_tables()
        self._migrate_database()
        
        # Cache initialization
        self._cache = {}
        self._cache_ttl = {}
        self._cache_enabled = True

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections to ensure proper cleanup"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_name)
            yield conn
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
                    
    def _execute_query(self, query: str, params=(), fetch_one=False, fetch_all=False, commit=False):
        """Execute a query with proper connection handling"""
        result = None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            elif commit:
                conn.commit()
                result = cursor.rowcount
                
        return result

    def _create_tables(self):
        """Create necessary tables if they don't exist"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Create whitelist table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS whitelist (
            id INTEGER PRIMARY KEY,
            value TEXT NOT NULL,
            wl_type TEXT DEFAULT 'FCFS',
            wl_reason TEXT DEFAULT 'Fluffy holder'
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
            joined_at TIMESTAMP DEFAULT (datetime('now'))
        )
        ''')
        
        # Create events table for statistics
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY,
            event_type TEXT NOT NULL,
            user_id INTEGER,
            timestamp TIMESTAMP DEFAULT (datetime('now')),
            data TEXT,
            success INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Create indexes for faster queries
        # Index on whitelist value for faster lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_whitelist_value ON whitelist(value)')
        
        # Index on event_type and timestamp for statistics queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(event_type, timestamp)')
        
        # Index on users last_activity for active users queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity)')
        
        conn.commit()
        conn.close()
    
    def _migrate_database(self):
        """Check and update database schema if needed"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Check if last_activity column exists in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add last_activity column if it doesn't exist
        if 'last_activity' not in columns:
            print("Migrating database: Adding last_activity column to users table")
            try:
                # Add column without default value
                cursor.execute('''
                ALTER TABLE users
                ADD COLUMN last_activity TIMESTAMP
                ''')
                
                # Update existing users with current timestamp
                cursor.execute('''
                UPDATE users SET last_activity = datetime('now')
                ''')
                
                conn.commit()
                print("Migration completed successfully")
            except Exception as e:
                print(f"Error during migration: {e}")
                conn.rollback()
        
        # Check if whitelist table has the new columns
        cursor.execute("PRAGMA table_info(whitelist)")
        whitelist_columns = [column[1] for column in cursor.fetchall()]
        
        # Add new columns to whitelist table if they don't exist
        if 'wl_type' not in whitelist_columns:
            print("Migrating database: Adding wl_type column to whitelist table")
            try:
                cursor.execute('''
                ALTER TABLE whitelist
                ADD COLUMN wl_type TEXT DEFAULT 'FCFS'
                ''')
                conn.commit()
                print("Added wl_type column successfully")
            except Exception as e:
                print(f"Error adding wl_type column: {e}")
                conn.rollback()
        
        if 'wl_reason' not in whitelist_columns:
            print("Migrating database: Adding wl_reason column to whitelist table")
            try:
                cursor.execute('''
                ALTER TABLE whitelist
                ADD COLUMN wl_reason TEXT DEFAULT 'Fluffy holder'
                ''')
                conn.commit()
                print("Added wl_reason column successfully")
            except Exception as e:
                print(f"Error adding wl_reason column: {e}")
                conn.rollback()
        
        conn.close()

    def add_to_whitelist(self, value: str, wl_type: str = "FCFS", wl_reason: str = "Fluffy holder") -> bool:
        """Add a value to the whitelist with type and reason"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Проверяем, существует ли уже это значение
            cursor.execute("SELECT id FROM whitelist WHERE value = ?", (value,))
            if cursor.fetchone():
                conn.close()
                return False
                
            cursor.execute(
                "INSERT INTO whitelist (value, wl_type, wl_reason) VALUES (?, ?, ?)", 
                (value, wl_type, wl_reason)
            )
            conn.commit()
            conn.close()
            
            # Invalidate cache keys that might contain stale data after this change
            self._invalidate_cache_key(f"whitelist_check_{value}")
            self._invalidate_cache_key("whitelist_count")
            
            return True
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
        
        # Invalidate cache keys that might contain stale data after this change
        self._invalidate_cache_key(f"whitelist_check_{value}")
        self._invalidate_cache_key("whitelist_count")
        
        return affected

    def check_whitelist(self, value: str) -> Dict[str, Any]:
        """Check if a value exists in the whitelist and return details"""
        # Try to get from cache first
        cache_key = f"whitelist_check_{value}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            # We still record the check event, but don't query DB again
            self.log_event("check", None, {"value": value, "result": cached_result["found"], "cached": True}, cached_result["found"])
            return cached_result
        
        # Not in cache, query the database
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT id, value, wl_type, wl_reason FROM whitelist WHERE value = ?", (value,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            result = {
                "found": True,
                "id": row[0],
                "value": row[1],
                "wl_type": row[2],
                "wl_reason": row[3]
            }
        else:
            result = {"found": False}
        
        # Record the check event
        self.log_event("check", None, {"value": value, "result": result["found"]}, result["found"])
        
        # Cache the result for 5 minutes
        self._set_cache(cache_key, result, 300)
        
        return result

    def get_all_whitelist(self) -> List[Dict[str, Any]]:
        """Get all values in the whitelist with their details"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT id, value, wl_type, wl_reason FROM whitelist")
        rows = cursor.fetchall()
        conn.close()
        
        result = []
        for row in rows:
            result.append({
                "id": row[0],
                "value": row[1],
                "wl_type": row[2],
                "wl_reason": row[3]
            })
        
        return result
    
    def get_whitelist_count(self) -> int:
        """Get the count of items in the whitelist"""
        # Try to get from cache first
        cache_key = "whitelist_count"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Not in cache, query the database
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM whitelist")
        result = cursor.fetchone()[0]
        conn.close()
        
        # Cache the result for 5 minutes
        self._set_cache(cache_key, result, 300)
        
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
                    SET username = ?, first_name = ?, last_name = ?, chat_id = ?, last_activity = datetime('now')
                    WHERE user_id = ?
                """, (username, first_name, last_name, chat_id, user_id))
            else:
                # Insert new user
                cursor.execute("""
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, chat_id, last_activity) 
                    VALUES (?, ?, ?, ?, ?, datetime('now'))
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
                UPDATE users SET last_activity = datetime('now')
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
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_activity >= datetime('now', ?)
            """, (f'-{days} days',))
            result = cursor.fetchone()[0]
            conn.close()
            return result
        except sqlite3.OperationalError as e:
            # If the column doesn't exist, return total users count as fallback
            if "no such column: last_activity" in str(e):
                print("Warning: last_activity column not found, returning total users count instead")
                return self.get_users_count()
            raise
    
    def log_event(self, event_type: str, user_id: Optional[int], data: dict = None, success: bool = True) -> bool:
        """Log an event for statistics"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Convert data dict to string if provided
            data_str = str(data) if data else None
            
            cursor.execute("""
                INSERT INTO events (event_type, user_id, data, success, timestamp)
                VALUES (?, ?, ?, ?, datetime('now'))
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
        try:
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
        except Exception as e:
            print(f"Error getting stats: {e}")
            # Return basic stats in case of error
            return {
                "users": {"total": self.get_users_count()},
                "whitelist": {"total": self.get_whitelist_count()},
                "error": str(e)
            }
    
    def get_daily_activity(self) -> Dict[str, int]:
        """Get activity count by day of week for the last 30 days"""
        try:
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
        except Exception as e:
            print(f"Error getting daily activity: {e}")
            return {}

    def get_total_users(self) -> int:
        """Get the total number of users in the database"""
        # Try to get from cache first
        cache_key = "total_users"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
            
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        result = cursor.fetchone()[0]
        conn.close()
        
        # Cache the result for 5 minutes
        self._set_cache(cache_key, result, 300)
        
        return result
    
    def get_active_users(self, days: int = 7) -> int:
        """Get the number of active users in the last specified days"""
        # Try to get from cache first
        cache_key = f"active_users_{days}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
            
        # Not cached, query the database
        result = self.get_active_users_count(days)
        
        # Cache the result for 5 minutes
        self._set_cache(cache_key, result, 300)
        
        return result
    
    def get_checks_count(self, days: int = None) -> int:
        """Get the count of check operations, optionally filtered by time period"""
        # Try to get from cache first
        cache_key = f"checks_count_{days if days is not None else 'all'}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result is not None:
            return cached_result
            
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        if days is not None:
            # Get checks for the last N days
            cursor.execute("""
                SELECT COUNT(*) 
                FROM events 
                WHERE event_type = 'check' 
                AND timestamp >= datetime('now', ?)
            """, (f'-{days} days',))
        else:
            # Get all checks
            cursor.execute("SELECT COUNT(*) FROM events WHERE event_type = 'check'")
            
        result = cursor.fetchone()[0]
        conn.close()
        
        # Cache the result - shorter time for recent checks (1 minute), longer for all-time (5 minutes)
        cache_time = 60 if days is not None and days <= 1 else 300
        self._set_cache(cache_key, result, cache_time)
        
        return result

    def import_whitelist_from_csv(self, file_path: str, mode: str = "append") -> tuple:
        """Import whitelist data from a CSV file
        
        Args:
            file_path: Path to the CSV file
            mode: 'append' to add to existing data, 'replace' to replace all data
            
        Returns:
            tuple: (success, stats) where stats is a dict with import statistics
        """
        try:
            import csv
            
            # Statistics to return
            stats = {
                "processed": 0,
                "added": 0,
                "skipped": 0,
                "invalid": 0
            }
            
            # If replacing, clear existing whitelist
            if mode == "replace":
                conn = sqlite3.connect(self.db_name)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM whitelist")
                conn.commit()
                conn.close()
                print(f"Cleared existing whitelist for replacement import")
            
            # Read and process CSV file
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                # Detect if file has headers
                sample = csvfile.read(1024)
                csvfile.seek(0)
                has_header = csv.Sniffer().has_header(sample)
                
                # Setup CSV reader
                reader = csv.reader(csvfile)
                if has_header:
                    # Skip header row
                    next(reader)
                
                # Process each row
                for row in reader:
                    stats["processed"] += 1
                    
                    # Skip empty rows
                    if not row or not any(row):
                        stats["invalid"] += 1
                        continue
                    
                    # Extract data based on row length
                    if len(row) >= 4:
                        # Full format: id, value, wl_type, wl_reason
                        value = row[1].strip()
                        wl_type = row[2].strip() if row[2].strip() else "FCFS"
                        wl_reason = row[3].strip() if row[3].strip() else "Fluffy holder"
                    elif len(row) == 3:
                        # Format: value, wl_type, wl_reason
                        value = row[0].strip()
                        wl_type = row[1].strip() if row[1].strip() else "FCFS"
                        wl_reason = row[2].strip() if row[2].strip() else "Fluffy holder"
                    elif len(row) == 2:
                        # Format: value, wl_type
                        value = row[0].strip()
                        wl_type = row[1].strip() if row[1].strip() else "FCFS" 
                        wl_reason = "Fluffy holder"
                    elif len(row) == 1:
                        # Format: value only
                        value = row[0].strip()
                        wl_type = "FCFS"
                        wl_reason = "Fluffy holder"
                    else:
                        # Should never reach here due to check above
                        stats["invalid"] += 1
                        continue
                    
                    # Skip if value is empty
                    if not value:
                        stats["invalid"] += 1
                        continue
                    
                    # Try to add to whitelist
                    success = self.add_to_whitelist(value, wl_type, wl_reason)
                    if success:
                        stats["added"] += 1
                    else:
                        stats["skipped"] += 1
            
            print(f"Import completed. Processed: {stats['processed']}, Added: {stats['added']}, "
                  f"Skipped: {stats['skipped']}, Invalid: {stats['invalid']}")
            return True, stats
            
        except Exception as e:
            print(f"Error importing whitelist from CSV: {e}")
            return False, {"error": str(e)}

    def export_whitelist_to_csv(self, filename: str = "whitelist_export.csv") -> tuple:
        """Export whitelist data to a CSV file
        
        Args:
            filename: The name of the CSV file to export to
            
        Returns:
            tuple: (success, filename) where filename is path to the exported file
        """
        try:
            import csv
            from datetime import datetime
            
            # Get all whitelist entries
            whitelist_data = self.get_all_whitelist()
            
            if not whitelist_data:
                print("No data to export")
                return False, None
            
            # Add timestamp to filename to avoid overwriting
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_with_timestamp = f"{filename.split('.')[0]}_{timestamp}.csv"
            
            # Write data to CSV file
            with open(filename_with_timestamp, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['id', 'value', 'wl_type', 'wl_reason']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for entry in whitelist_data:
                    writer.writerow(entry)
            
            print(f"Export successful: {filename_with_timestamp}")
            return True, filename_with_timestamp
        except Exception as e:
            print(f"Error exporting whitelist to CSV: {e}")
            return False, None

    def _get_from_cache(self, key: str):
        """Get a value from cache if it exists and is not expired"""
        if not self._cache_enabled:
            return None
            
        if key not in self._cache:
            return None
            
        # Check if cache entry has expired
        if key in self._cache_ttl and self._cache_ttl[key] < datetime.datetime.now():
            # Cache expired
            del self._cache[key]
            del self._cache_ttl[key]
            return None
            
        return self._cache[key]
        
    def _set_cache(self, key: str, value, ttl_seconds: int = 60):
        """Store a value in cache with expiration time"""
        if not self._cache_enabled:
            return
            
        self._cache[key] = value
        self._cache_ttl[key] = datetime.datetime.now() + datetime.timedelta(seconds=ttl_seconds)
        
    def _clear_cache(self):
        """Clear all cached values"""
        self._cache = {}
        self._cache_ttl = {}
        
    def _invalidate_cache_key(self, key: str):
        """Remove a specific key from cache"""
        if key in self._cache:
            del self._cache[key]
        if key in self._cache_ttl:
            del self._cache_ttl[key] 