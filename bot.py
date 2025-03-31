import os
import logging
import asyncio
from typing import List, Dict, Any

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)

from database import Database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

# Admin IDs - replace with actual admin user IDs
ADMIN_IDS = [6327617477]  # Add your admin Telegram user IDs here

# Define command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /start command"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Add user to the database
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        chat_id=chat_id
    )
    
    # Create keyboard with main commands
    keyboard = []
    keyboard.append(["/check - Проверить в списке"])
    keyboard.append(["/help - Помощь"])
    
    # Add admin commands if user is admin
    if user.id in ADMIN_IDS:
        keyboard.append(["/admin - Панель администратора"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот MegaBuddies. Отправь мне свой ID или другую информацию для проверки в базе данных.",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /help command"""
    user = update.effective_user
    
    # Base commands for all users
    message = (
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/check - Проверить значение в базе данных\n"
    )
    
    # Add admin commands if user is admin
    if user.id in ADMIN_IDS:
        message += (
            "\nКоманды администратора:\n"
            "/admin - Панель администратора\n"
            "/add <значение> - Добавить значение в базу данных\n"
            "/remove <значение> - Удалить значение из базы данных\n"
            "/list - Показать все значения в базе данных\n"
            "/broadcast - Отправить сообщение всем пользователям"
        )
    
    await update.message.reply_text(message)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for admin panel with inline buttons"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("Добавить в список", callback_data="admin_add"),
            InlineKeyboardButton("Удалить из списка", callback_data="admin_remove")
        ],
        [
            InlineKeyboardButton("Показать список", callback_data="admin_list"),
            InlineKeyboardButton("Рассылка", callback_data="admin_broadcast")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Панель администратора:", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_add":
        await query.message.reply_text("Используйте команду /add <значение> для добавления в список")
    elif query.data == "admin_remove":
        await query.message.reply_text("Используйте команду /remove <значение> для удаления из списка")
    elif query.data == "admin_list":
        # Reuse the list_whitelist function
        await list_whitelist(update, context)
    elif query.data == "admin_broadcast":
        await query.message.reply_text("Введите /broadcast <сообщение> для отправки сообщения всем пользователям")
    elif query.data == "check_value":
        await query.message.reply_text("Введите значение для проверки:")
        context.user_data["expecting_check"] = True

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /check command with prompt"""
    await update.message.reply_text("Введите значение для проверки:")
    context.user_data["expecting_check"] = True

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for checking a value against the whitelist"""
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите значение для проверки. Пример: /check 12345")
        return
    
    value = context.args[0]
    if db.check_whitelist(value):
        await update.message.reply_text("Вы в вайтлисте! ✅")
    else:
        await update.message.reply_text("Вы не в вайтлисте. ❌")

async def add_to_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin handler to add a value to the whitelist"""
    # Check if user is admin
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return
    
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите значение для добавления. Пример: /add 12345")
        return
    
    value = context.args[0]
    if db.add_to_whitelist(value):
        await update.message.reply_text(f"Значение '{value}' добавлено в вайтлист.")
    else:
        await update.message.reply_text(f"Значение '{value}' уже существует в вайтлисте.")

async def remove_from_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin handler to remove a value from the whitelist"""
    # Check if user is admin
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return
    
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите значение для удаления. Пример: /remove 12345")
        return
    
    value = context.args[0]
    if db.remove_from_whitelist(value):
        await update.message.reply_text(f"Значение '{value}' удалено из вайтлиста.")
    else:
        await update.message.reply_text(f"Значение '{value}' не найдено в вайтлисте.")

async def list_whitelist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin handler to list all values in the whitelist"""
    # Check if user is admin
    user_id = update.effective_user.id if update.effective_user else None
    if user_id not in ADMIN_IDS:
        if update.message:
            await update.message.reply_text("У вас нет прав для использования этой команды.")
        return
    
    values = db.get_all_whitelist()
    if values:
        message = "Значения в вайтлисте:\n" + "\n".join(values)
    else:
        message = "Вайтлист пуст."
    
    # Handle both direct command and callback query
    if update.callback_query:
        await update.callback_query.message.reply_text(message)
    else:
        await update.message.reply_text(message)

# States for broadcast conversation
BROADCAST_MESSAGE = 0

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the broadcast conversation"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "Введите сообщение для отправки всем пользователям:"
    )
    return BROADCAST_MESSAGE

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the message to broadcast"""
    message_text = update.message.text
    
    if not message_text:
        await update.message.reply_text("Пожалуйста, отправьте текстовое сообщение.")
        return BROADCAST_MESSAGE
    
    users = db.get_all_users()
    
    if not users:
        await update.message.reply_text("В базе нет пользователей для рассылки.")
        return ConversationHandler.END
    
    await update.message.reply_text(f"Начинаю рассылку для {len(users)} пользователей...")
    
    success_count = 0
    fail_count = 0
    
    for user_id, chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message_text)
            success_count += 1
            # Add a small delay to avoid hitting rate limits
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"Рассылка завершена.\nУспешно отправлено: {success_count}\nОшибок: {fail_count}"
    )
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the broadcast conversation"""
    await update.message.reply_text("Рассылка отменена.")
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for processing all non-command messages"""
    if not update.message or not update.message.text:
        return
    
    text = update.message.text.strip()
    
    # If we're expecting a value to check, do the check
    if context.user_data.get("expecting_check"):
        context.user_data["expecting_check"] = False
        if db.check_whitelist(text):
            await update.message.reply_text("Вы в вайтлисте! ✅")
        else:
            await update.message.reply_text("Вы не в вайтлисте. ❌")
    else:
        # Normal message handling
        if db.check_whitelist(text):
            await update.message.reply_text("Вы в вайтлисте! ✅")
        else:
            await update.message.reply_text("Вы не в вайтлисте. ❌")

def main() -> None:
    """Start the bot"""
    # Get the bot token from environment variables
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("No BOT_TOKEN found in environment variables!")
        return
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("add", add_to_whitelist))
    application.add_handler(CommandHandler("remove", remove_from_whitelist))
    application.add_handler(CommandHandler("list", list_whitelist))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add conversation handler for broadcast
    broadcast_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_command)],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message)],
        },
        fallbacks=[CommandHandler("cancel", cancel_broadcast)],
    )
    application.add_handler(broadcast_conv_handler)
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    application.run_polling()
    
    logger.info("Bot started")

if __name__ == "__main__":
    main() 
