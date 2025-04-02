from typing import Dict, Any, List, Optional, Union
import logging

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import ContextTypes

from src.utils import get_user_details, get_chat_id
from src.utils.helpers import format_error
from src.database import Database

logger = logging.getLogger(__name__)

# Constants
ADMIN_IDS = [6327617477]  # Replace with your admin Telegram user IDs

# Helper for keyboard management
def get_main_keyboard(user_id: int) -> List[List[InlineKeyboardButton]]:
    """Generate main menu keyboard based on user permissions"""
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить", callback_data="action_check")],
    ]
    
    # Add admin buttons if user is admin
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("📊 Статистика", callback_data="action_stats")])
    
    # Add links/FAQ button for all users
    keyboard.append([InlineKeyboardButton("📚 Ссылки/FAQ", callback_data="action_links")])
    
    # Add admin panel button if user is admin
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("🔐 Админ-панель", callback_data="action_admin")])
    
    return keyboard

# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /start command"""
    try:
        db: Database = context.bot_data["db"]
        user_details = get_user_details(update)
        
        # Add user to the database
        await db.add_user(
            user_id=user_details["user_id"],
            username=user_details["username"],
            first_name=user_details["first_name"],
            last_name=user_details["last_name"],
            chat_id=user_details["chat_id"]
        )
        
        # Log the event
        await db.log_event("start", user_details["user_id"])
        
        # Show main menu with inline buttons
        await show_main_menu(update, context)
        
        # Also show persistent keyboard at bottom
        await show_persistent_keyboard(update, context)
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /help command"""
    try:
        await show_help_menu(update, context)
        # Show keyboard after help command
        await show_persistent_keyboard(update, context)
    except Exception as e:
        logger.error(f"Error in help_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /menu command"""
    try:
        await show_main_menu(update, context)
    except Exception as e:
        logger.error(f"Error in menu_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

# UI display functions
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main menu"""
    try:
        user = update.effective_user
        keyboard = get_main_keyboard(user.id)
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Main menu message
        message_text = (
            "*👋 Главное меню MegaBuddies WL Bot*\n\n"
            "Здесь вы можете:\n"
            "• Проверить адрес в вайтлисте\n"
        )
        
        if user and user.id in ADMIN_IDS:
            message_text += "• Просмотреть статистику\n"
        
        message_text += "• Найти полезные ссылки и FAQ\n"
        
        if user and user.id in ADMIN_IDS:
            message_text += "• Управлять вайтлистом (админ)\n"
        
        # Handle message or callback query accordingly
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in show_main_menu: {e}")

async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help information with a back button"""
    try:
        user = update.effective_user
        
        # Base commands for all users
        help_text = (
            "*📚 Справка по MegaBuddies*\n\n"
            "*Основные команды:*\n"
            "• `/start` - Начать работу с ботом\n"
            "• `/help` - Показать эту справку\n"
            "• `/check` - Проверить значение в базе\n"
            "• `/menu` - Открыть главное меню\n\n"
            
            "*Как пользоваться ботом:*\n"
            "1️⃣ Просто напишите текст для мгновенной проверки\n"
            "2️⃣ Используйте кнопки меню для навигации\n"
            "3️⃣ Используйте команды для быстрого доступа к функциям\n\n"
        )
        
        # Add admin commands if user is admin
        if user.id in ADMIN_IDS:
            help_text += (
                "*Команды администратора:*\n"
                "• `/admin` - Панель администратора\n"
                "• `/add` - Добавить значение в базу данных\n"
                "• `/remove` - Удалить значение из базы данных\n"
                "• `/list` - Показать все значения в базе данных\n"
                "• `/broadcast` - Отправить сообщение пользователям\n"
                "• `/stats` - Показать статистику бота\n"
                "• `/export` - Экспортировать базу данных в CSV формат\n"
                "• `/import` - Импортировать данные в базу\n\n"
            )
        
        # Add back button
        keyboard = [[InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Reply with help text
        if update.callback_query:
            await update.callback_query.edit_message_text(
                help_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                help_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in show_help_menu: {e}")

async def show_persistent_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a persistent keyboard at the bottom of the chat"""
    try:
        user = update.effective_user
        
        # Basic buttons for all users
        buttons = [
            [KeyboardButton("🔍 Проверить"), KeyboardButton("❓ Помощь")],
            [KeyboardButton("🏠 Главное меню")]
        ]
        
        # Add admin row for admin users
        if user and user.id in ADMIN_IDS:
            buttons.append([
                KeyboardButton("📊 Статистика"), 
                KeyboardButton("🔐 Админ-панель")
            ])
        
        reply_markup = ReplyKeyboardMarkup(
            buttons,
            resize_keyboard=True,
            one_time_keyboard=False
        )
        
        # Get chat ID
        chat_id = get_chat_id(update)
        if chat_id:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Используйте кнопки ниже для быстрого доступа к функциям бота:",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error in show_persistent_keyboard: {e}")

async def show_links_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show links/FAQ menu"""
    try:
        links_text = (
            "*📚 Полезные ссылки*\n\n"
            "*Официальные ресурсы:*\n"
            "• [Веб-сайт MegaBuddies](https://megabuddies.io)\n"
            "• [Twitter/X](https://x.com/MegaBuddies)\n"
            "• [Discord](https://discord.gg/megabuddies)\n\n"
            
            "*FAQ:*\n"
            "• *Что такое вайтлист?*\n"
            "  Вайтлист - это список адресов, которые получат приоритетный доступ к минту.\n\n"
            "• *Как попасть в вайтлист?*\n"
            "  Следите за анонсами в Discord и Twitter.\n\n"
            "• *Когда минт?*\n"
            "  Следите за анонсами в официальных каналах.\n\n"
        )
        
        # Add back button
        keyboard = [[InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                links_text,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                links_text,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.error(f"Error in show_links_menu: {e}")

# Message handlers
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle regular text messages - direct check functionality"""
    try:
        db: Database = context.bot_data["db"]
        user = update.effective_user
        message_text = update.message.text.strip()
        
        # Update user's last activity
        await db.update_user_activity(user.id)
        
        # Handle keyboard shortcuts
        if message_text == "🔍 Проверить":
            # Show check menu
            await context.bot_data["check_handler"](update, context)
            return
        elif message_text == "❓ Помощь":
            # Show help menu
            await help_command(update, context)
            return
        elif message_text == "🏠 Главное меню":
            # Show main menu
            await menu_command(update, context)
            return
        elif message_text == "📊 Статистика" and user.id in ADMIN_IDS:
            # Show stats menu
            await context.bot_data["stats_handler"](update, context)
            return
        elif message_text == "🔐 Админ-панель" and user.id in ADMIN_IDS:
            # Show admin menu
            await context.bot_data["admin_handler"](update, context)
            return
        
        # Interpret all other text as check request
        result = await db.check_whitelist(message_text)
        
        # Format result
        if result.get("found", False):
            response_text = (
                f"✅ *Значение найдено в вайтлисте!*\n\n"
                f"ID: `{result['id']}`\n"
                f"Значение: `{result['value']}`\n"
                f"Тип WL: `{result['wl_type']}`\n"
                f"Причина: `{result['wl_reason']}`"
            )
        else:
            response_text = "❌ *Значение не найдено в вайтлисте!*"
        
        # Add check again button
        keyboard = [[InlineKeyboardButton("🔍 Проверить ещё", callback_data="action_check")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}") 