# MegaBuddies Whitelist Bot

Telegram bot for managing and verifying entries in a whitelist for MegaBuddies project.

## Features

- ✅ Check if an address/value is in the whitelist
- 👥 User account tracking and statistics
- 📊 Admin dashboard with usage metrics
- 📝 Whitelist management (add, remove, list entries)
- 📤 Export whitelist to CSV
- 📥 Import whitelist from CSV
- 📢 Broadcast messages to all users

## Project Structure

The project is organized with a modular architecture:

```
mega_buddies_bot/
├── main.py              # Main entry point and app setup
├── requirements.txt     # Dependencies
├── .env                 # Environment variables (private)
├── .env.example         # Example environment config
├── src/                 # Source code
│   ├── database/        # Database operations
│   │   ├── __init__.py
│   │   └── db.py        # Database class with async operations
│   ├── handlers/        # Bot command handlers
│   │   ├── __init__.py
│   │   ├── basic.py     # Basic commands (start, help, menu)
│   │   ├── whitelist.py # Whitelist operations (check, add, remove)
│   │   └── admin.py     # Admin operations (stats, broadcast)
│   └── utils/           # Utilities
│       ├── __init__.py
│       └── helpers.py   # Helper functions
└── mega_buddies.db      # SQLite database
```

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/mega_buddies_bot.git
cd mega_buddies_bot
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Configure the bot:
- Copy `.env.example` to `.env`
- Add your Telegram Bot Token to `.env`:
```
BOT_TOKEN=your_bot_token_here
```

4. Run the bot:
```
python main.py
```

## Bot Commands

- `/start` - Start the bot and see main menu
- `/help` - Show help information
- `/menu` - Display main menu
- `/check` - Check a value against the whitelist
- `/admin` - Access admin panel (admin only)
- `/stats` - Show bot statistics (admin only)
- `/add` - Add a value to the whitelist (admin only)
- `/remove` - Remove a value from the whitelist (admin only)
- `/list` - List all values in the whitelist (admin only)
- `/broadcast` - Send a message to all users (admin only)
- `/export` - Export whitelist to CSV (admin only)
- `/import` - Import whitelist from CSV (admin only)

## Technical Details

- Built with python-telegram-bot 20.8
- Uses SQLite database with aiosqlite for async operations
- Implements proper error handling and logging
- Follows separation of concerns with modular architecture
- Fully asynchronous using Python's asyncio

## Security

- Admin functionality is restricted to authorized user IDs
- Environment variables used for sensitive data
- Input validation for all user-provided values

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
- `/list` - List all values in the whitelist (admin only)
- `/broadcast` - Send a message to all users (admin only)
- `/export` - Export whitelist to CSV (admin only)
- `/import` - Import whitelist from CSV (admin only)

## Technical Details

- Built with python-telegram-bot 20.8
- Uses SQLite database with aiosqlite for async operations
- Implements proper error handling and logging
- Follows separation of concerns with modular architecture
- Fully asynchronous using Python's asyncio

## Security

- Admin functionality is restricted to authorized user IDs
- Environment variables used for sensitive data
- Input validation for all user-provided values

## License

This project is licensed under the MIT License - see the LICENSE file for details. 