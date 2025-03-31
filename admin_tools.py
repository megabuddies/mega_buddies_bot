import sys
from database import Database

def main():
    """Simple CLI interface for database management"""
    db = Database()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python admin_tools.py add <value> - Add value to whitelist")
        print("  python admin_tools.py remove <value> - Remove value from whitelist")
        print("  python admin_tools.py list - List all values in whitelist")
        print("  python admin_tools.py add_admin <user_id> - Set admin ID in the config")
        return
    
    command = sys.argv[1]
    
    if command == "add" and len(sys.argv) == 3:
        value = sys.argv[2]
        if db.add_to_whitelist(value):
            print(f"Added '{value}' to whitelist")
        else:
            print(f"Value '{value}' already exists in whitelist")
    
    elif command == "remove" and len(sys.argv) == 3:
        value = sys.argv[2]
        if db.remove_from_whitelist(value):
            print(f"Removed '{value}' from whitelist")
        else:
            print(f"Value '{value}' not found in whitelist")
    
    elif command == "list":
        values = db.get_all_whitelist()
        if values:
            print("Values in whitelist:")
            for value in values:
                print(f"- {value}")
        else:
            print("Whitelist is empty")
    
    else:
        print("Invalid command")

if __name__ == "__main__":
    main() 