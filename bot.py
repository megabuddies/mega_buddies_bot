import os
import logging
import asyncio
from typing import List, Dict, Any

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes,
    filters
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
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот MegaBuddies. Отправь мне свой ID или другую информацию для проверки в базе данных."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /help command"""
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n"
        "/check <значение> - Проверить значение в базе данных\n"
        "\nАдминистраторы:\n"
        "/add <значение> - Добавить значение в базу данных\n"
        "/remove <значение> - Удалить значение из базы данных\n"
        "/list - Показать все значения в базе данных\n"
        "/broadcast <сообщение> - Отправить сообщение всем пользователям"
    )

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
    # Check if user is admin (Add your admin user IDs here)
    admin_ids = [6327617477]  # Replace with actual admin user IDs
    if update.effective_user.id not in admin_ids:
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
    admin_ids = [6327617477]  # Replace with actual admin user IDs
    if update.effective_user.id not in admin_ids:
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
    admin_ids = [6327617477]  # Replace with actual admin user IDs
    if update.effective_user.id not in admin_ids:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return
    
    values = db.get_all_whitelist()
    if values:
        message = "Значения в вайтлисте:\n" + "\n".join(values)
    else:
        message = "Вайтлист пуст."
    
    await update.message.reply_text(message)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin handler to broadcast a message to all users"""
    # Check if user is admin
    admin_ids = [6327617477]  # Replace with actual admin user IDs
    if update.effective_user.id not in admin_ids:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return
    
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите сообщение для рассылки. Пример: /broadcast Важное сообщение!")
        return
    
    message = " ".join(context.args)
    users = db.get_all_users()
    
    success_count = 0
    fail_count = 0
    
    await update.message.reply_text(f"Начинаю рассылку для {len(users)} пользователей...")
    
    for user_id, chat_id in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            fail_count += 1
        
        # Add a small delay to avoid hitting rate limits
        await asyncio.sleep(0.05)
    
    await update.message.reply_text(
        f"Рассылка завершена.\nУспешно отправлено: {success_count}\nОшибок: {fail_count}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for processing all non-command messages"""
    # Check if the message could be a whitelist value
    text = update.message.text.strip()
    
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
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("add", add_to_whitelist))
    application.add_handler(CommandHandler("remove", remove_from_whitelist))
    application.add_handler(CommandHandler("list", list_whitelist))
    application.add_handler(CommandHandler("broadcast", broadcast))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    application.run_polling()
    
    logger.info("Bot started")

if __name__ == "__main__":
    main() 
