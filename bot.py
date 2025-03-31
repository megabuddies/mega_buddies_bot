import os
import logging
import asyncio
import time
import json
from typing import List, Dict, Any, Optional, Union, Tuple

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

# States for conversation handlers
BROADCAST_MESSAGE = 0
AWAITING_CHECK_VALUE = 1
AWAITING_ADD_VALUE = 2
AWAITING_REMOVE_VALUE = 3

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
    
    # Log the event
    db.log_event("start", user.id)
    
    # Create main menu
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main menu with inline buttons"""
    user = update.effective_user
    
    # Create keyboard with main options
    keyboard = [
        [InlineKeyboardButton("Проверить в списке 🔍", callback_data="menu_check")],
        [InlineKeyboardButton("Помощь ℹ️", callback_data="menu_help")]
    ]
    
    # Add admin section if user is admin
    if user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("Админ-панель 🔧", callback_data="menu_admin")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or edit message based on context
    if update.callback_query:
        # Edit existing message
        await update.callback_query.edit_message_text(
            f"Главное меню MegaBuddies\n\nВыберите действие:",
            reply_markup=reply_markup
        )
    else:
        # Send new message
        message = await update.message.reply_text(
            f"Привет, {user.first_name}! Я бот MegaBuddies.\n\nВыберите действие:",
            reply_markup=reply_markup
        )
        # Store message ID for future reference
        if not context.user_data.get('menu_messages'):
            context.user_data['menu_messages'] = []
        context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /help command"""
    await show_help_menu(update, context)

async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the help menu with information"""
    user = update.effective_user
    
    # Base help text for all users
    help_text = (
        "📋 *Справка по командам:*\n\n"
        "• *Проверка данных* — отправьте боту текст или нажмите на кнопку \"Проверить в списке\"\n"
        "• /start — показать главное меню\n"
        "• /help — показать эту справку\n"
    )
    
    # Add admin commands if user is admin
    if user.id in ADMIN_IDS:
        help_text += (
            "\n*Команды администратора:*\n"
            "• /add <значение> — добавить значение в базу\n"
            "• /remove <значение> — удалить значение из базы\n"
            "• /list — показать все значения\n"
            "• /broadcast — отправить сообщение всем пользователям\n"
            "• /stats — показать статистику\n"
        )
    
    # Back button
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or edit message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # Clean up previous menu messages
        await clean_previous_menus(update, context)
        message = await update.message.reply_text(
            help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        # Store message ID
        if not context.user_data.get('menu_messages'):
            context.user_data['menu_messages'] = []
        context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))

async def show_check_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the check value prompt"""
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Введите значение для проверки в вайтлисте:",
            reply_markup=reply_markup
        )
    else:
        # Clean up previous menu messages
        await clean_previous_menus(update, context)
        message = await update.message.reply_text(
            "Введите значение для проверки в вайтлисте:",
            reply_markup=reply_markup
        )
        # Store message ID
        if not context.user_data.get('menu_messages'):
            context.user_data['menu_messages'] = []
        context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))
    
    return AWAITING_CHECK_VALUE

async def handle_check_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the value entered for checking"""
    value = update.message.text.strip()
    
    # Check the value against whitelist
    result = db.check_whitelist(value)
    
    # Update user activity
    db.update_user_activity(update.effective_user.id)
    
    # Create response message
    if result:
        message_text = f"✅ Значение \"{value}\" *найдено* в вайтлисте!"
    else:
        message_text = f"❌ Значение \"{value}\" *не найдено* в вайтлисте."
    
    # Buttons for next action
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить другое значение", callback_data="menu_check")],
        [InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Clean up previous menu messages
    await clean_previous_menus(update, context)
    
    # Send new response
    message = await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Store message ID
    if not context.user_data.get('menu_messages'):
        context.user_data['menu_messages'] = []
    context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))
    
    return ConversationHandler.END

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the admin panel menu"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        # If not admin, show error and return to main menu
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
            await show_main_menu(update, context)
        else:
            await update.message.reply_text("У вас нет прав доступа к этому разделу.")
        return
    
    # Admin menu keyboard
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить", callback_data="admin_add"),
            InlineKeyboardButton("➖ Удалить", callback_data="admin_remove")
        ],
        [
            InlineKeyboardButton("📋 Список", callback_data="admin_list"),
            InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("📨 Рассылка", callback_data="admin_broadcast")
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "*Панель администратора*\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # Clean up previous menu messages
        await clean_previous_menus(update, context)
        message = await update.message.reply_text(
            "*Панель администратора*\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        # Store message ID
        if not context.user_data.get('menu_messages'):
            context.user_data['menu_messages'] = []
        context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /stats command"""
    await show_stats_menu(update, context)

async def show_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot statistics for admin"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        # If not admin, show error
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
        else:
            await update.message.reply_text("У вас нет прав доступа к этому разделу.")
        return
    
    try:
        # Get stats from database
        stats = db.get_stats()
        
        # Format statistics message
        stats_text = (
            "*📊 Статистика бота*\n\n"
            
            "*👥 Пользователи:*\n"
            f"• Всего: {stats['users']['total']}\n"
        )
        
        # Add additional user stats if available
        if 'new_7d' in stats['users']:
            stats_text += f"• Новых за 7 дней: {stats['users']['new_7d']}\n"
        if 'new_1d' in stats['users']:
            stats_text += f"• Новых за 24 часа: {stats['users']['new_1d']}\n"
        if 'active_7d' in stats['users']:
            stats_text += f"• Активных за 7 дней: {stats['users']['active_7d']}\n"
        
        stats_text += f"\n*📋 База данных:*\n"
        stats_text += f"• Записей в вайтлисте: {stats['whitelist']['total']}\n\n"
        
        # Add check stats if available
        if 'checks' in stats:
            stats_text += (
                "*🔍 Проверки:*\n"
                f"• За 7 дней: {stats['checks'].get('total_7d', 0)}\n"
                f"  ✅ Успешных: {stats['checks'].get('successful_7d', 0)}\n"
                f"  ❌ Неудачных: {stats['checks'].get('failed_7d', 0)}\n"
                f"• За 24 часа: {stats['checks'].get('total_1d', 0)}\n"
                f"  ✅ Успешных: {stats['checks'].get('successful_1d', 0)}\n"
                f"  ❌ Неудачных: {stats['checks'].get('failed_1d', 0)}\n\n"
            )
        
        # Add daily activity if available
        stats_text += "*📅 Активность по дням:*\n"
        daily_activity = stats.get('daily_activity', {})
        if daily_activity:
            for day, count in daily_activity.items():
                stats_text += f"• {day}: {count}\n"
        else:
            stats_text += "Нет данных\n"
        
        # Add error info if present
        if 'error' in stats:
            stats_text += f"\n⚠️ *Примечание:* Данные могут быть неполными ({stats['error']})\n"
        
    except Exception as e:
        # Fallback message if stats generation fails
        logger.error(f"Error generating stats: {e}")
        stats_text = (
            "*📊 Статистика бота*\n\n"
            "⚠️ Произошла ошибка при получении статистики.\n"
            f"Детали ошибки: {str(e)}\n\n"
            "Попробуйте позже или обратитесь к разработчику."
        )
    
    # Back buttons
    keyboard = [
        [InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # Clean up previous menu messages
        await clean_previous_menus(update, context)
        message = await update.message.reply_text(
            stats_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        # Store message ID
        if not context.user_data.get('menu_messages'):
            context.user_data['menu_messages'] = []
        context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))

async def show_add_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show menu for adding a value to whitelist"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Введите значение для добавления в вайтлист:",
            reply_markup=reply_markup
        )
    
    return AWAITING_ADD_VALUE

async def handle_add_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process adding a value to whitelist"""
    value = update.message.text.strip()
    
    # Add to whitelist
    success = db.add_to_whitelist(value)
    
    # Log event
    db.log_event("add_whitelist", update.effective_user.id, {"value": value}, success)
    
    # Create response message
    if success:
        message_text = f"✅ Значение \"{value}\" успешно добавлено в вайтлист!"
    else:
        message_text = f"⚠️ Значение \"{value}\" уже существует в вайтлисте."
    
    # Buttons for next action
    keyboard = [
        [InlineKeyboardButton("➕ Добавить еще", callback_data="admin_add")],
        [InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Clean up previous menu messages
    await clean_previous_menus(update, context)
    
    # Send new response
    message = await update.message.reply_text(
        message_text,
        reply_markup=reply_markup
    )
    
    # Store message ID
    if not context.user_data.get('menu_messages'):
        context.user_data['menu_messages'] = []
    context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))
    
    return ConversationHandler.END

async def show_remove_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show menu for removing a value from whitelist"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Введите значение для удаления из вайтлиста:",
            reply_markup=reply_markup
        )
    
    return AWAITING_REMOVE_VALUE

async def handle_remove_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process removing a value from whitelist"""
    value = update.message.text.strip()
    
    # Remove from whitelist
    success = db.remove_from_whitelist(value)
    
    # Log event
    db.log_event("remove_whitelist", update.effective_user.id, {"value": value}, success)
    
    # Create response message
    if success:
        message_text = f"✅ Значение \"{value}\" успешно удалено из вайтлиста!"
    else:
        message_text = f"❌ Значение \"{value}\" не найдено в вайтлисте."
    
    # Buttons for next action
    keyboard = [
        [InlineKeyboardButton("➖ Удалить еще", callback_data="admin_remove")],
        [InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Clean up previous menu messages
    await clean_previous_menus(update, context)
    
    # Send new response
    message = await update.message.reply_text(
        message_text,
        reply_markup=reply_markup
    )
    
    # Store message ID
    if not context.user_data.get('menu_messages'):
        context.user_data['menu_messages'] = []
    context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))
    
    return ConversationHandler.END

async def show_list_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all values in whitelist"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
        else:
            await update.message.reply_text("У вас нет прав доступа к этому разделу.")
        return
    
    # Get values from whitelist
    values = db.get_all_whitelist()
    
    # Create response message
    if values:
        values_per_page = 10
        page = context.user_data.get('whitelist_page', 0)
        total_pages = (len(values) + values_per_page - 1) // values_per_page
        
        # Ensure page is valid
        if page >= total_pages:
            page = 0
        
        # Save current page
        context.user_data['whitelist_page'] = page
        
        # Get values for current page
        start = page * values_per_page
        end = min(start + values_per_page, len(values))
        
        message_text = f"*📋 Список значений в вайтлисте ({len(values)} записей)*\n"
        message_text += f"Страница {page+1} из {total_pages}\n\n"
        
        # Add values with numbering
        for i, value in enumerate(values[start:end], start=start+1):
            message_text += f"{i}. `{value}`\n"
        
        # Navigation buttons
        keyboard = []
        nav_row = []
        
        if total_pages > 1:
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️", callback_data="whitelist_prev"))
            
            nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="whitelist_info"))
            
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("▶️", callback_data="whitelist_next"))
            
            keyboard.append(nav_row)
    else:
        message_text = "📋 Вайтлист пуст."
    
    # Back buttons
    keyboard.append([InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")])
    keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # Clean up previous menu messages
        await clean_previous_menus(update, context)
        message = await update.message.reply_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        # Store message ID
        if not context.user_data.get('menu_messages'):
            context.user_data['menu_messages'] = []
        context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))

async def handle_whitelist_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle whitelist pagination buttons"""
    query = update.callback_query
    
    # Get current page
    page = context.user_data.get('whitelist_page', 0)
    
    # Update page based on button
    if query.data == "whitelist_next":
        page += 1
    elif query.data == "whitelist_prev":
        page -= 1
    
    # Save updated page
    context.user_data['whitelist_page'] = page
    
    # Show updated list
    await show_list_menu(update, context)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the broadcast conversation"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return ConversationHandler.END
    
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Clean up previous menu messages
    await clean_previous_menus(update, context)
    
    message = await update.message.reply_text(
        "Введите сообщение для отправки всем пользователям:",
        reply_markup=reply_markup
    )
    
    # Store message ID
    if not context.user_data.get('menu_messages'):
        context.user_data['menu_messages'] = []
    context.user_data['menu_messages'].append((chat_id_from_update(update), message.message_id))
    
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
    
    # Log broadcast event
    db.log_event("broadcast", update.effective_user.id, {"message_length": len(message_text)})
    
    progress_message = await update.message.reply_text(f"Начинаю рассылку для {len(users)} пользователей...")
    
    success_count = 0
    fail_count = 0
    
    # Show progress updates periodically
    progress_interval = max(1, len(users) // 10)
    last_progress_update = time.time()
    
    for i, (user_id, chat_id) in enumerate(users):
        try:
            await context.bot.send_message(chat_id=chat_id, text=message_text)
            success_count += 1
            
            # Update progress message periodically
            if (i % progress_interval == 0 or i == len(users) - 1) and time.time() - last_progress_update > 2:
                progress_percent = int((i + 1) / len(users) * 100)
                await progress_message.edit_text(
                    f"Рассылка: {progress_percent}% ({i+1}/{len(users)})\n"
                    f"✅ Успешно: {success_count}\n"
                    f"❌ Ошибок: {fail_count}"
                )
                last_progress_update = time.time()
            
            # Add a small delay to avoid hitting rate limits
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            fail_count += 1
    
    # Final results with buttons
    keyboard = [
        [InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await progress_message.edit_text(
        f"✅ Рассылка завершена\n\n"
        f"📊 Статистика:\n"
        f"• Всего получателей: {len(users)}\n"
        f"• Успешно доставлено: {success_count}\n"
        f"• Ошибок доставки: {fail_count}",
        reply_markup=reply_markup
    )
    
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the broadcast conversation"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "❌ Рассылка отменена.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")
        ]])
    )
    
    return ConversationHandler.END

async def clean_previous_menus(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete previous menu messages to keep the chat clean"""
    if context.user_data.get('menu_messages'):
        for chat_id, message_id in context.user_data['menu_messages'][-3:]:  # Keep only last 3 to avoid too many deletions
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception as e:
                logger.debug(f"Could not delete message {message_id}: {e}")
        
        # Clear the list after deletion attempts
        context.user_data['menu_messages'] = []

def chat_id_from_update(update: Update) -> int:
    """Extract chat ID from an update object"""
    if update.effective_chat:
        return update.effective_chat.id
    elif update.callback_query and update.callback_query.message:
        return update.callback_query.message.chat_id
    elif update.message:
        return update.message.chat_id
    else:
        # Fallback - should not happen in normal operation
        return 0

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    # Update user activity
    db.update_user_activity(query.from_user.id)
    
    # Log button event
    db.log_event("button_click", query.from_user.id, {"button": query.data})
    
    # Main menu options
    if query.data == "back_to_main" or query.data == "menu_main":
        await show_main_menu(update, context)
    elif query.data == "menu_check":
        result = await show_check_menu(update, context)
        context.user_data['expecting_check'] = True
    elif query.data == "menu_help":
        await show_help_menu(update, context)
    elif query.data == "menu_admin":
        await show_admin_menu(update, context)
    
    # Admin panel options
    elif query.data == "admin_add":
        result = await show_add_menu(update, context)
        context.user_data['expecting_add'] = True
    elif query.data == "admin_remove":
        result = await show_remove_menu(update, context)
        context.user_data['expecting_remove'] = True
    elif query.data == "admin_list":
        await show_list_menu(update, context)
    elif query.data == "admin_stats":
        await show_stats_menu(update, context)
    elif query.data == "admin_broadcast":
        await query.edit_message_text(
            "Для начала рассылки используйте команду /broadcast",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")
            ]])
        )
    
    # Whitelist pagination
    elif query.data in ["whitelist_next", "whitelist_prev"]:
        await handle_whitelist_pagination(update, context)
    elif query.data == "whitelist_info":
        # Just acknowledge the button press without doing anything
        pass
    
    # Broadcast cancel
    elif query.data == "broadcast_cancel":
        await cancel_broadcast(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for processing all non-command messages"""
    if not update.message or not update.message.text:
        return
    
    # Update user activity
    db.update_user_activity(update.effective_user.id)
    
    text = update.message.text.strip()
    
    # Handle different conversation states
    if context.user_data.get('expecting_check'):
        context.user_data['expecting_check'] = False
        await handle_check_value(update, context)
    elif context.user_data.get('expecting_add'):
        context.user_data['expecting_add'] = False
        await handle_add_value(update, context)
    elif context.user_data.get('expecting_remove'):
        context.user_data['expecting_remove'] = False
        await handle_remove_value(update, context)
    else:
        # Normal message handling - check whitelist
        if db.check_whitelist(text):
            keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Значение \"{text}\" *найдено* в вайтлисте!",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔍 Проверить другое значение", callback_data="menu_check")],
                [InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"❌ Значение \"{text}\" *не найдено* в вайтлисте.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

def main() -> None:
    """Start the bot"""
    # Get the bot token from environment variables
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("No BOT_TOKEN found in environment variables!")
        return
    
    # Initialize database
    try:
        logger.info("Initializing database...")
        global db
        db = Database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        return
    
    # Create the Application
    application = Application.builder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", show_admin_menu))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("list", show_list_menu))
    
    # Add conversation handler for check
    check_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("check", show_check_menu)],
        states={
            AWAITING_CHECK_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_check_value)]
        },
        fallbacks=[CallbackQueryHandler(button_callback)],
        name="check_conversation",
        persistent=False
    )
    application.add_handler(check_conv_handler)
    
    # Add conversation handler for add
    add_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", show_add_menu)],
        states={
            AWAITING_ADD_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_value)]
        },
        fallbacks=[CallbackQueryHandler(button_callback)],
        name="add_conversation",
        persistent=False
    )
    application.add_handler(add_conv_handler)
    
    # Add conversation handler for remove
    remove_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("remove", show_remove_menu)],
        states={
            AWAITING_REMOVE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_value)]
        },
        fallbacks=[CallbackQueryHandler(button_callback)],
        name="remove_conversation",
        persistent=False
    )
    application.add_handler(remove_conv_handler)
    
    # Add conversation handler for broadcast
    broadcast_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_command)],
        states={
            BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message)]
        },
        fallbacks=[CallbackQueryHandler(cancel_broadcast, pattern="^broadcast_cancel$")],
        name="broadcast_conversation",
        persistent=False
    )
    application.add_handler(broadcast_conv_handler)
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling()
    
    logger.info("Bot stopped")

if __name__ == "__main__":
    main() 
