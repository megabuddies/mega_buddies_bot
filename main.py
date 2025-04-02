import asyncio
import logging
import os
import sys
from typing import Dict, Any, List

from telegram import BotCommand, Update, BotCommandScopeDefault
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from src.database import Database
from src.utils import setup_logging, load_environment
from src.handlers import (
    # Basic handlers
    start_command,
    help_command,
    menu_command,
    handle_text_message,
    show_links_menu,
    
    # Whitelist handlers
    check_command,
    handle_check_value,
    add_command,
    handle_add_value,
    handle_wl_type,
    handle_wl_reason,
    remove_command,
    handle_remove_value,
    list_command,
    handle_whitelist_pagination,
    
    # Admin handlers
    admin_command,
    stats_command,
    broadcast_command,
    handle_broadcast_message,
    confirm_broadcast,
    cancel_broadcast,
    export_command,
    import_command,
    handle_import_mode,
    handle_import_file,
    
    # Conversation states
    AWAITING_CHECK_VALUE,
    AWAITING_ADD_VALUE,
    AWAITING_REMOVE_VALUE,
    AWAITING_WL_TYPE,
    AWAITING_WL_REASON,
    BROADCAST_MESSAGE
)

# Get logger
logger = setup_logging()

async def setup_commands(application: Application) -> None:
    """Define and register bot commands for display in Telegram UI"""
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Показать справку"),
        BotCommand("menu", "Показать главное меню"),
        BotCommand("check", "Проверить значение в вайтлисте"),
        BotCommand("admin", "Открыть панель администратора"),
        BotCommand("stats", "Показать статистику бота"),
        BotCommand("add", "Добавить значение в вайтлист"),
        BotCommand("remove", "Удалить значение из вайтлиста"),
        BotCommand("list", "Показать все записи вайтлиста"),
        BotCommand("broadcast", "Отправить сообщение всем пользователям"),
        BotCommand("export", "Экспортировать вайтлист в CSV"),
        BotCommand("import", "Импортировать вайтлист из CSV")
    ]
    
    await application.bot.set_my_commands(
        commands=commands,
        scope=BotCommandScopeDefault()
    )
    
    logger.info("Bot commands have been set up")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    # Get the callback data
    callback_data = query.data
    
    # Route to appropriate handlers based on callback data
    if callback_data == "back_to_main":
        # Return to main menu
        from src.handlers import show_main_menu
        await show_main_menu(update, context)
    
    elif callback_data == "action_check":
        # Show check menu
        from src.handlers import show_check_menu
        await show_check_menu(update, context)
    
    elif callback_data == "action_admin":
        # Show admin panel
        from src.handlers import show_admin_menu
        await show_admin_menu(update, context)
    
    elif callback_data == "action_stats":
        # Show statistics
        from src.handlers import show_stats_menu
        await show_stats_menu(update, context)
    
    elif callback_data == "action_add":
        # Show add menu
        from src.handlers import show_add_menu
        await show_add_menu(update, context)
    
    elif callback_data == "action_remove":
        # Show remove menu
        from src.handlers import show_remove_menu
        await show_remove_menu(update, context)
    
    elif callback_data == "action_list":
        # Show whitelist contents
        from src.handlers import show_list_menu
        await show_list_menu(update, context)
    
    elif callback_data == "action_broadcast":
        # Show broadcast menu
        from src.handlers import show_broadcast_menu
        await show_broadcast_menu(update, context)
    
    elif callback_data == "action_links":
        # Show links/FAQ menu
        from src.handlers import show_links_menu
        await show_links_menu(update, context)
    
    elif callback_data == "action_export":
        # Handle export action
        from src.handlers import handle_export
        await handle_export(update, context)
    
    elif callback_data == "action_import":
        # Show import menu
        from src.handlers import show_import_menu
        await show_import_menu(update, context)
    
    elif callback_data.startswith("whitelist_"):
        # Handle whitelist pagination
        await handle_whitelist_pagination(update, context)
    
    elif callback_data.startswith("import_mode_"):
        # Handle import mode selection
        await handle_import_mode(update, context)
    
    elif callback_data == "confirm_broadcast":
        # Confirm and execute broadcast
        await confirm_broadcast(update, context)
    
    elif callback_data == "cancel_broadcast":
        # Cancel broadcast
        await cancel_broadcast(update, context)
    
    elif callback_data == "back_to_admin":
        # Return to admin menu
        from src.handlers import show_admin_menu
        await show_admin_menu(update, context)
    
    else:
        # Unknown callback data
        logger.warning(f"Unknown callback data: {callback_data}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors occurring in the dispatcher"""
    logger.error(f"Exception while handling an update: {context.error}")

async def main() -> None:
    """Set up and run the bot"""
    try:
        # Load environment variables
        env = load_environment()
        token = env["bot_token"]
        
        # Initialize database
        db = Database()
        await db.initialize()
        logger.info("Database initialized")
        
        # Initialize bot application
        application = Application.builder().token(token).build()
        
        # Store database in bot_data for access across all handlers
        application.bot_data["db"] = db
        
        # Set up commands
        await setup_commands(application)
        
        # Register handlers
        
        # Basic command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("menu", menu_command))
        
        # Admin command handlers
        application.add_handler(CommandHandler("admin", admin_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("export", export_command))
        application.add_handler(CommandHandler("import", import_command))
        
        # Register check conversation
        check_conversation = ConversationHandler(
            entry_points=[CommandHandler("check", check_command)],
            states={
                AWAITING_CHECK_VALUE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_check_value)
                ]
            },
            fallbacks=[CallbackQueryHandler(handle_callback_query)]
        )
        application.add_handler(check_conversation)
        
        # Save reference to check handler for use from text messages
        application.bot_data["check_handler"] = check_command
        
        # Register add conversation
        add_conversation = ConversationHandler(
            entry_points=[CommandHandler("add", add_command)],
            states={
                AWAITING_ADD_VALUE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_value)
                ],
                AWAITING_WL_TYPE: [
                    CallbackQueryHandler(handle_wl_type)
                ],
                AWAITING_WL_REASON: [
                    CallbackQueryHandler(handle_wl_reason)
                ]
            },
            fallbacks=[CallbackQueryHandler(handle_callback_query)]
        )
        application.add_handler(add_conversation)
        
        # Register remove conversation
        remove_conversation = ConversationHandler(
            entry_points=[CommandHandler("remove", remove_command)],
            states={
                AWAITING_REMOVE_VALUE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_value)
                ]
            },
            fallbacks=[CallbackQueryHandler(handle_callback_query)]
        )
        application.add_handler(remove_conversation)
        
        # Register broadcast conversation
        broadcast_conversation = ConversationHandler(
            entry_points=[CommandHandler("broadcast", broadcast_command)],
            states={
                BROADCAST_MESSAGE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message),
                    CallbackQueryHandler(confirm_broadcast, pattern="^confirm_broadcast$"),
                    CallbackQueryHandler(cancel_broadcast, pattern="^cancel_broadcast$")
                ]
            },
            fallbacks=[CallbackQueryHandler(handle_callback_query)]
        )
        application.add_handler(broadcast_conversation)
        
        # Store admin handler references
        application.bot_data["admin_handler"] = admin_command
        application.bot_data["stats_handler"] = stats_command
        
        # Handle document uploads (for import)
        application.add_handler(MessageHandler(filters.Document.ALL, handle_import_file))
        
        # Handle callback queries
        application.add_handler(CallbackQueryHandler(handle_callback_query))
        
        # Handle general text messages (including direct check functionality)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        
        # Handle errors
        application.add_error_handler(error_handler)
        
        # Start the bot
        logger.info("Starting bot...")
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        # Run until CTRL+C
        logger.info("Bot is running. Press CTRL+C to stop.")
        await application.updater.stop_polling()
        await application.stop()
    
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (CTRL+C)")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")
        sys.exit(1) 