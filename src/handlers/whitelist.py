import logging
from typing import Dict, Any, List, Optional, Union, Tuple

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from telegram.ext import ContextTypes, ConversationHandler

from src.utils import get_user_details, format_check_result
from src.utils.helpers import format_error
from src.database import Database
from src.handlers.basic import ADMIN_IDS

logger = logging.getLogger(__name__)

# Conversation states
AWAITING_CHECK_VALUE = 1
AWAITING_ADD_VALUE = 2
AWAITING_REMOVE_VALUE = 3
AWAITING_WL_TYPE = 4
AWAITING_WL_REASON = 5

# WL types and reasons
WL_TYPES = ["GTD", "FCFS"]
WL_REASONS = ["Fluffy holder", "X contributor"]

# Check handlers
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /check command"""
    try:
        # Show check menu
        await show_check_menu(update, context)
        return AWAITING_CHECK_VALUE
    except Exception as e:
        logger.error(f"Error in check_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

async def show_check_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show menu for checking a value against whitelist"""
    try:
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = "Введите значение для проверки в базе данных:"
        
        if update.callback_query:
            # For callback queries, send a new message instead of editing
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
        else:
            # For direct commands
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
        
        return AWAITING_CHECK_VALUE
    except Exception as e:
        logger.error(f"Error in show_check_menu: {e}")
        return ConversationHandler.END

async def handle_check_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the check value submitted by the user"""
    try:
        db: Database = context.bot_data["db"]
        
        # Get value from message
        value = update.message.text.strip()
        
        # Update user activity
        user_details = get_user_details(update)
        await db.update_user_activity(user_details["user_id"])
        
        # Check the value in the whitelist
        result = await db.check_whitelist(value)
        
        # Format the result message
        response_text = format_check_result(result)
        
        # Add check again button
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить ещё", callback_data="action_check")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in handle_check_value: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

# Add handlers
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /add command - admin only"""
    try:
        user = update.effective_user
        
        # Check if user is admin
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для использования этой команды."
            )
            return ConversationHandler.END
        
        # Show add menu
        await show_add_menu(update, context)
        return AWAITING_ADD_VALUE
    except Exception as e:
        logger.error(f"Error in add_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

async def show_add_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show menu for adding a value to whitelist"""
    try:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_add")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = "Введите значение для добавления в вайтлист:"
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
        
        return AWAITING_ADD_VALUE
    except Exception as e:
        logger.error(f"Error in show_add_menu: {e}")
        return ConversationHandler.END

async def handle_add_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the value to be added to the whitelist"""
    try:
        # Store the value in context for later use
        context.user_data["add_value"] = update.message.text.strip()
        
        # Show WL type selection
        keyboard = []
        for wl_type in WL_TYPES:
            keyboard.append([InlineKeyboardButton(wl_type, callback_data=f"wl_type_{wl_type}")])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_add")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Выберите тип вайтлиста для значения:\n\n`{context.user_data['add_value']}`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return AWAITING_WL_TYPE
    except Exception as e:
        logger.error(f"Error in handle_add_value: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

async def handle_wl_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the selected whitelist type"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("wl_type_"):
            wl_type = query.data.replace("wl_type_", "")
            context.user_data["wl_type"] = wl_type
            
            # Show WL reason selection
            keyboard = []
            for reason in WL_REASONS:
                keyboard.append([InlineKeyboardButton(reason, callback_data=f"wl_reason_{reason}")])
            
            keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_add")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"Выберите причину вайтлиста для значения:\n\n"
                f"`{context.user_data['add_value']}`\n\n"
                f"Тип: `{wl_type}`",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return AWAITING_WL_REASON
        elif query.data == "cancel_add":
            await query.edit_message_text("❌ Операция добавления отменена.")
            return ConversationHandler.END
        else:
            await query.edit_message_text("❌ Неизвестный выбор. Операция отменена.")
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in handle_wl_type: {e}")
        await query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

async def handle_wl_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the selected whitelist reason and add to database"""
    try:
        query = update.callback_query
        await query.answer()
        
        db: Database = context.bot_data["db"]
        
        if query.data.startswith("wl_reason_"):
            wl_reason = query.data.replace("wl_reason_", "")
            value = context.user_data.get("add_value", "")
            wl_type = context.user_data.get("wl_type", "FCFS")
            
            if not value:
                await query.edit_message_text("❌ Ошибка: значение для добавления не задано.")
                return ConversationHandler.END
            
            # Add to database
            success = await db.add_to_whitelist(value, wl_type, wl_reason)
            
            if success:
                # Log the add event
                user_details = get_user_details(update)
                await db.log_event(
                    "add_whitelist", 
                    user_details["user_id"], 
                    {"value": value, "wl_type": wl_type, "wl_reason": wl_reason}, 
                    True
                )
                
                response_text = (
                    f"✅ Значение успешно добавлено в вайтлист!\n\n"
                    f"Значение: `{value}`\n"
                    f"Тип WL: `{wl_type}`\n"
                    f"Причина: `{wl_reason}`"
                )
            else:
                response_text = f"❌ Значение `{value}` уже существует в базе данных или произошла ошибка."
            
            # Add buttons for actions after adding
            keyboard = [
                [InlineKeyboardButton("➕ Добавить ещё", callback_data="action_add")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                response_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Clear user data
            context.user_data.clear()
            
            return ConversationHandler.END
        elif query.data == "cancel_add":
            await query.edit_message_text("❌ Операция добавления отменена.")
            context.user_data.clear()
            return ConversationHandler.END
        else:
            await query.edit_message_text("❌ Неизвестный выбор. Операция отменена.")
            context.user_data.clear()
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in handle_wl_reason: {e}")
        await query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")
        context.user_data.clear()
        return ConversationHandler.END

# Remove handlers
async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /remove command - admin only"""
    try:
        user = update.effective_user
        
        # Check if user is admin
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для использования этой команды."
            )
            return ConversationHandler.END
        
        # Show remove menu
        await show_remove_menu(update, context)
        return AWAITING_REMOVE_VALUE
    except Exception as e:
        logger.error(f"Error in remove_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

async def show_remove_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show menu for removing a value from whitelist"""
    try:
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_remove")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = "Введите значение для удаления из вайтлиста:"
        
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup
            )
        
        return AWAITING_REMOVE_VALUE
    except Exception as e:
        logger.error(f"Error in show_remove_menu: {e}")
        return ConversationHandler.END

async def handle_remove_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the value to be removed from the whitelist"""
    try:
        db: Database = context.bot_data["db"]
        value = update.message.text.strip()
        
        # Check if value exists first
        check_result = await db.check_whitelist(value)
        
        if not check_result.get("found", False):
            await update.message.reply_text(
                f"❌ Значение `{value}` не найдено в базе данных.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Remove from database
        success = await db.remove_from_whitelist(value)
        
        if success:
            # Log the remove event
            user_details = get_user_details(update)
            await db.log_event(
                "remove_whitelist", 
                user_details["user_id"], 
                {"value": value}, 
                True
            )
            
            response_text = f"✅ Значение `{value}` успешно удалено из вайтлиста!"
        else:
            response_text = f"❌ Ошибка при удалении значения `{value}` из базы данных."
        
        # Add buttons for actions after removing
        keyboard = [
            [InlineKeyboardButton("➖ Удалить ещё", callback_data="action_remove")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            response_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in handle_remove_value: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")
        return ConversationHandler.END

# List handlers
async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /list command - admin only"""
    try:
        user = update.effective_user
        
        # Check if user is admin
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(
                "❌ У вас нет прав администратора для использования этой команды."
            )
            return
        
        # Show whitelist contents with pagination
        await show_list_menu(update, context)
    except Exception as e:
        logger.error(f"Error in list_command: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def show_list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show whitelist entries with pagination"""
    try:
        db: Database = context.bot_data["db"]
        
        # Default page number
        page = context.user_data.get("whitelist_page", 0)
        per_page = 10
        offset = page * per_page
        
        # Get whitelist entries for current page
        whitelist_data = await db.get_all_whitelist(limit=per_page, offset=offset)
        total_count = await db.get_whitelist_count()
        
        # Calculate total pages
        total_pages = (total_count + per_page - 1) // per_page
        
        if not whitelist_data:
            message_text = "📝 Вайтлист пуст. Нет записей для отображения."
            keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
        else:
            # Format whitelist entries
            message_text = f"📝 *Записи вайтлиста* (страница {page + 1}/{total_pages}):\n\n"
            
            for idx, item in enumerate(whitelist_data, start=1):
                message_text += (
                    f"{idx + offset}. `{item['value']}`\n"
                    f"   Тип: `{item['wl_type']}`, Причина: `{item['wl_reason']}`\n\n"
                )
            
            # Add pagination buttons
            keyboard = []
            
            # Navigation row
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data="whitelist_prev"))
            
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("➡️ Вперёд", callback_data="whitelist_next"))
            
            if nav_row:
                keyboard.append(nav_row)
            
            # Actions row
            keyboard.append([
                InlineKeyboardButton("➕ Добавить", callback_data="action_add"),
                InlineKeyboardButton("➖ Удалить", callback_data="action_remove")
            ])
            
            # Back to main menu
            keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])
        
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
        logger.error(f"Error in show_list_menu: {e}")
        if update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}")
        else:
            await update.message.reply_text(f"❌ Произошла ошибка: {format_error(e)}")

async def handle_whitelist_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pagination for whitelist display"""
    try:
        query = update.callback_query
        await query.answer()
        
        # Current page
        page = context.user_data.get("whitelist_page", 0)
        
        if query.data == "whitelist_next":
            # Next page
            context.user_data["whitelist_page"] = page + 1
        elif query.data == "whitelist_prev":
            # Previous page
            context.user_data["whitelist_page"] = max(0, page - 1)
        
        # Show updated page
        await show_list_menu(update, context)
    except Exception as e:
        logger.error(f"Error in handle_whitelist_pagination: {e}")
        await query.edit_message_text(f"❌ Произошла ошибка: {format_error(e)}") 