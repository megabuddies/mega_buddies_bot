import logging
import os
from typing import Dict, Any, List, Optional, Union, Tuple

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    Document
)
from telegram.ext import ContextTypes, ConversationHandler

from src.utils import get_user_details, get_chat_id, format_stats
from src.utils.helpers import format_error
from src.database import Database
from src.handlers.basic import ADMIN_IDS

logger = logging.getLogger(__name__)

# Conversation states
BROADCAST_MESSAGE = 0

# Admin handlers
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /admin command - admin only"""
    try:
        user = update.effective_user
        
        # Check if user is admin
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для использования этой команды."
            )
            return
        
        # Show admin menu
        await show_admin_menu(update, context)
    except Exception as e:
        logger.error(f"Error in admin_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin panel menu"""
    try:
        # Create admin menu keyboard
        keyboard = [
            [InlineKeyboardButton("📋 Список WL", callback_data="action_list")],
            [
                InlineKeyboardButton("➕ Добавить", callback_data="action_add"),
                InlineKeyboardButton("➖ Удалить", callback_data="action_remove")
            ],
            [InlineKeyboardButton("📊 Статистика", callback_data="action_stats")],
            [
                InlineKeyboardButton("📤 Экспорт", callback_data="action_export"),
                InlineKeyboardButton("📥 Импорт", callback_data="action_import")
            ],
            [InlineKeyboardButton("📢 Рассылка", callback_data="action_broadcast")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Admin panel message
        message_text = (
            "*🔐 Панель администратора*\n\n"
            "Выберите действие из меню ниже:\n\n"
            "• 📋 Список WL - просмотр записей вайтлиста\n"
            "• ➕ Добавить - добавить новую запись\n"
            "• ➖ Удалить - удалить запись\n"
            "• 📊 Статистика - просмотр статистики бота\n"
            "• 📤 Экспорт - экспорт вайтлиста в CSV\n"
            "• 📥 Импорт - импорт вайтлиста из CSV\n"
            "• 📢 Рассылка - отправить сообщение всем пользователям\n"
        )
        
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
        logger.error(f"Error in show_admin_menu: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")
        else:
            await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

# Statistics handlers
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /stats command - admin only"""
    try:
        user = update.effective_user
        
        # Check if user is admin
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для использования этой команды."
            )
            return
        
        # Show statistics
        await show_stats_menu(update, context)
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot statistics"""
    try:
        db: Database = context.bot_data["db"]
        
        # Get statistics
        stats = await db.get_stats()
        
        # Format statistics message
        stats_text = format_stats(stats)
        
        # Add daily activity if available
        daily_activity = stats.get("daily_activity", {})
        if daily_activity:
            stats_text += "\n\n*📅 Активность по дням:*\n"
            for date, count in sorted(daily_activity.items()):
                stats_text += f"{date}: {count} событий\n"
        
        # Add back buttons
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить", callback_data="action_stats")],
            [
                InlineKeyboardButton("👥 Админ-панель", callback_data="action_admin"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error in show_stats_menu: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")
        else:
            await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

# Broadcast handlers
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /broadcast command - admin only"""
    try:
        user = update.effective_user
        
        # Check if user is admin
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для использования этой команды."
            )
            return ConversationHandler.END
        
        # Show broadcast menu
        await show_broadcast_menu(update, context)
        return BROADCAST_MESSAGE
    except Exception as e:
        logger.error(f"Error in broadcast_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

async def show_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show menu for broadcasting a message"""
    try:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_broadcast")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            "*📢 Рассылка сообщений*\n\n"
            "Введите текст для отправки всем пользователям бота.\n"
            "Поддерживается Markdown-форматирование.\n\n"
            "_Например:_ *жирный текст* или _курсив_"
        )
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
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
        logger.error(f"Error in show_broadcast_menu: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")
        else:
            await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle broadcast message from admin and send to all users"""
    try:
        db: Database = context.bot_data["db"]
        message_text = update.message.text.strip()
        
        # Get all users
        all_users = await db.get_all_users()
        total_users = len(all_users)
        
        if total_users == 0:
            await update.message.reply_text("❌ Нет пользователей для рассылки.")
            return ConversationHandler.END
        
        # Show confirmation
        keyboard = [
            [
                InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_broadcast"),
                InlineKeyboardButton("❌ Отмена", callback_data="cancel_broadcast")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Store message for broadcasting
        context.user_data["broadcast_message"] = message_text
        
        await update.message.reply_text(
            f"*📢 Предпросмотр сообщения*\n\n"
            f"{message_text}\n\n"
            f"Сообщение будет отправлено *{total_users}* пользователям.\n"
            f"Подтвердите отправку или отмените.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return BROADCAST_MESSAGE
    except Exception as e:
        logger.error(f"Error in handle_broadcast_message: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and execute broadcast"""
    try:
        query = update.callback_query
        await query.answer()
        
        if "broadcast_message" not in context.user_data:
            await query.edit_message_text("❌ Сообщение для рассылки не найдено.")
            return ConversationHandler.END
        
        # Get message and begin broadcast
        message_text = context.user_data["broadcast_message"]
        
        # Show processing message
        await query.edit_message_text(
            "🔄 Рассылка началась. Это может занять некоторое время...",
            parse_mode='Markdown'
        )
        
        # Start the broadcast process
        await start_broadcast_process(update, context)
        
        # Clear user data
        context.user_data.clear()
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in confirm_broadcast: {e}")
        await query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel broadcast operation"""
    try:
        # Clear user data
        context.user_data.clear()
        
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text("❌ Рассылка отменена.")
        else:
            await update.message.reply_text("❌ Рассылка отменена.")
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in cancel_broadcast: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")
        else:
            await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

async def start_broadcast_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Execute the actual broadcast to all users"""
    try:
        db: Database = context.bot_data["db"]
        message_text = context.user_data.get("broadcast_message", "")
        
        if not message_text:
            return
        
        # Get all users
        all_users = await db.get_all_users()
        total_users = len(all_users)
        
        if total_users == 0:
            if update.callback_query:
                await update.callback_query.edit_message_text("❌ Нет пользователей для рассылки.")
            return
        
        # Add broadcast header
        broadcast_text = (
            "*📢 ОБЪЯВЛЕНИЕ*\n\n"
            f"{message_text}"
        )
        
        # Keep track of statistics
        sent_count = 0
        failed_count = 0
        
        # Send message to all users
        for user_id, chat_id in all_users:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=broadcast_text,
                    parse_mode='Markdown'
                )
                sent_count += 1
                
                # Log successful broadcast
                await db.log_event(
                    "broadcast", 
                    user_id, 
                    {"success": True, "message_length": len(message_text)}, 
                    True
                )
            except Exception as e:
                logger.error(f"Error sending broadcast to user {user_id}: {e}")
                failed_count += 1
                
                # Log failed broadcast
                await db.log_event(
                    "broadcast", 
                    user_id, 
                    {"success": False, "error": str(e)}, 
                    False
                )
        
        # Update status message
        if update.callback_query:
            await update.callback_query.edit_message_text(
                f"✅ Рассылка завершена!\n\n"
                f"• Всего пользователей: {total_users}\n"
                f"• Успешно отправлено: {sent_count}\n"
                f"• Ошибок: {failed_count}"
            )
    except Exception as e:
        logger.error(f"Error in start_broadcast_process: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")

# Export/Import handlers
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /export command - admin only"""
    try:
        user = update.effective_user
        
        # Check if user is admin
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для использования этой команды."
            )
            return
        
        # Start export process
        await handle_export(update, context)
    except Exception as e:
        logger.error(f"Error in export_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def handle_export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Export whitelist to CSV and send to user"""
    try:
        db: Database = context.bot_data["db"]
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"whitelist_export_{timestamp}.csv"
        
        # Do the export
        success, message = await db.export_whitelist_to_csv(filename)
        
        if success:
            # Send the file
            with open(filename, 'rb') as file:
                await update.effective_message.reply_document(
                    document=file,
                    filename=filename,
                    caption=f"✅ Экспорт вайтлиста завершен: {message}"
                )
            
            # Delete the file after sending
            os.remove(filename)
            
            # Log export event
            user_details = get_user_details(update)
            await db.log_event(
                "export", 
                user_details["user_id"], 
                {"success": True, "message": message}, 
                True
            )
        else:
            await update.effective_message.reply_text(f"❌ Ошибка экспорта: {message}")
            
            # Log failed export
            user_details = get_user_details(update)
            await db.log_event(
                "export", 
                user_details["user_id"], 
                {"success": False, "error": message}, 
                False
            )
    except Exception as e:
        logger.error(f"Error in handle_export: {e}")
        await update.effective_message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def import_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /import command - admin only"""
    try:
        user = update.effective_user
        
        # Check if user is admin
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для использования этой команды."
            )
            return
        
        # Show import instructions
        await show_import_menu(update, context)
    except Exception as e:
        logger.error(f"Error in import_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def show_import_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show import menu with instructions"""
    try:
        message_text = (
            "*📥 Импорт вайтлиста*\n\n"
            "Загрузите CSV-файл для импорта в следующем формате:\n"
            "```\n"
            "value,wl_type,wl_reason\n"
            "0x123...,FCFS,Fluffy holder\n"
            "0xabc...,GTD,X contributor\n"
            "```\n\n"
            "Первая строка с заголовками не обязательна.\n"
            "Все столбцы кроме первого (значения) опциональны.\n\n"
            "Выберите режим импорта:"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить новые", callback_data="import_mode_append")],
            [InlineKeyboardButton("🔄 Обновить существующие", callback_data="import_mode_update")],
            [InlineKeyboardButton("♻️ Заменить всё", callback_data="import_mode_overwrite")],
            [InlineKeyboardButton("❌ Отмена", callback_data="back_to_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
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
        logger.error(f"Error in show_import_menu: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")
        else:
            await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def handle_import_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle import mode selection"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("import_mode_"):
            mode = query.data.replace("import_mode_", "")
            context.user_data["import_mode"] = mode
            
            # Show instructions for file upload
            await query.edit_message_text(
                f"*📥 Импорт вайтлиста - {mode}*\n\n"
                f"Пожалуйста, загрузите CSV-файл для импорта в режиме '{mode}'.\n\n"
                f"После загрузки файла процесс импорта начнется автоматически."
            )
        elif query.data == "back_to_admin":
            # Return to admin menu
            await show_admin_menu(update, context)
    except Exception as e:
        logger.error(f"Error in handle_import_mode: {e}")
        await query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")

async def handle_import_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle uploaded CSV file for import"""
    try:
        db: Database = context.bot_data["db"]
        
        # Check if file is provided
        if not update.message.document:
            await update.message.reply_text("❌ Пожалуйста, загрузите CSV-файл.")
            return
        
        # Get import mode
        import_mode = context.user_data.get("import_mode", "append")
        
        # Download the file
        file = await context.bot.get_file(update.message.document.file_id)
        file_path = f"import_temp_{update.message.document.file_name}"
        await file.download_to_drive(file_path)
        
        # Process import
        success, message = await db.import_whitelist_from_csv(file_path, import_mode)
        
        # Delete temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        if success:
            # Log successful import
            user_details = get_user_details(update)
            await db.log_event(
                "import", 
                user_details["user_id"], 
                {"success": True, "mode": import_mode, "message": message}, 
                True
            )
            
            # Send success message with buttons
            keyboard = [
                [InlineKeyboardButton("📋 Просмотр списка", callback_data="action_list")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Импорт успешно завершен!\n\n{message}",
                reply_markup=reply_markup
            )
        else:
            # Log failed import
            user_details = get_user_details(update)
            await db.log_event(
                "import", 
                user_details["user_id"], 
                {"success": False, "mode": import_mode, "error": message}, 
                False
            )
            
            await update.message.reply_text(f"❌ Ошибка импорта: {message}")
    except Exception as e:
        logger.error(f"Error in handle_import_file: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        
        # Delete temporary file if exists
        file_path = f"import_temp_{update.message.document.file_name}"
        if os.path.exists(file_path):
            os.remove(file_path) 