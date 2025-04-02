import os
import logging
from typing import Optional, Any, Dict
from dotenv import load_dotenv
from telegram import Update

# Configure logging
def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    return logger

# Environment variables
def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()
    
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable is not set!")
    
    return {
        "bot_token": bot_token
    }

# Helper functions for update objects
def get_user_details(update: Update) -> Dict[str, Any]:
    """Extract user details from an update object"""
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None
    
    return {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "chat_id": chat_id
    }

def get_chat_id(update: Update) -> Optional[int]:
    """Extract chat ID from an update object"""
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message.chat_id
    elif update.message:
        return update.message.chat_id
    elif update.edited_message:
        return update.edited_message.chat_id
    elif update.effective_chat:
        return update.effective_chat.id
    return None

# Error handling
def format_error(e: Exception) -> str:
    """Format an exception into a readable error message"""
    error_type = type(e).__name__
    error_msg = str(e)
    return f"{error_type}: {error_msg}"

# Text formatting
def format_check_result(result: Dict[str, Any]) -> str:
    """Format whitelist check result for display"""
    if result.get("found", False):
        return (
            f"✅ *Значение найдено в вайтлисте!*\n\n"
            f"ID: `{result['id']}`\n"
            f"Значение: `{result['value']}`\n"
            f"Тип WL: `{result['wl_type']}`\n"
            f"Причина: `{result['wl_reason']}`"
        )
    else:
        return "❌ *Значение не найдено в вайтлисте!*"

def format_stats(stats: Dict[str, Any]) -> str:
    """Format statistics for display"""
    if "error" in stats:
        return f"❌ Ошибка при получении статистики: {stats['error']}"
    
    total_users = stats.get("total_users", 0)
    active_users_24h = stats.get("active_users_24h", 0)
    active_users_7d = stats.get("active_users_7d", 0)
    new_users_7d = stats.get("new_users_7d", 0)
    check_events_24h = stats.get("check_events_24h", 0)
    check_events_7d = stats.get("check_events_7d", 0)
    successful_checks_7d = stats.get("successful_checks_7d", 0)
    whitelist_count = stats.get("whitelist_count", 0)
    
    # Calculate percentages
    success_rate = (successful_checks_7d / check_events_7d * 100) if check_events_7d > 0 else 0
    active_rate = (active_users_7d / total_users * 100) if total_users > 0 else 0
    
    return (
        "*📊 Статистика бота*\n\n"
        f"*👥 Пользователи:*\n"
        f"Всего: {total_users}\n"
        f"Активных (24ч): {active_users_24h}\n"
        f"Активных (7д): {active_users_7d} ({active_rate:.1f}%)\n"
        f"Новых (7д): {new_users_7d}\n\n"
        
        f"*🔍 Проверки:*\n"
        f"За 24ч: {check_events_24h}\n"
        f"За 7д: {check_events_7d}\n"
        f"Успешных (7д): {successful_checks_7d} ({success_rate:.1f}%)\n\n"
        
        f"*📝 Вайтлист:*\n"
        f"Всего записей: {whitelist_count}"
    ) 