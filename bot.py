import os
import logging
import asyncio
import time
import json
from typing import List, Dict, Any, Optional, Union, Tuple

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChat
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

# Keys for storing the active message in user_data
ACTIVE_MESSAGE_KEY = 'active_message'  # Store (chat_id, message_id) for active menu

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
    
    # Show main menu with inline buttons
    await show_main_menu(update, context)
    
    # Also show persistent keyboard at bottom
    await show_persistent_keyboard(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main menu with inline buttons"""
    # Identify the user
    user = update.effective_user
    
    # Create keyboard with main options
    keyboard = []
    
    # Add primary actions row
    keyboard.append([
        InlineKeyboardButton("🔍 Проверить значение", callback_data="action_check"),
        InlineKeyboardButton("❓ Помощь", callback_data="action_help")
    ])
    
    # Add admin panel row for admins
    if user.id in ADMIN_IDS:
        keyboard.append([
            InlineKeyboardButton("👑 Панель администратора", callback_data="menu_admin")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Menu title and description
    menu_text = (
        "*🤖 Главное меню MegaBuddies*\n\n"
        "Выберите действие из меню ниже.\n"
        "• Используйте _Проверить значение_ для проверки информации в вайтлисте\n"
        "• Используйте _Помощь_ для получения информации о командах\n"
    )
    
    if user.id in ADMIN_IDS:
        menu_text += "• Используйте _Панель администратора_ для доступа к админ-функциям\n"
    
    menu_text += "\n💡 Совет: В любой момент введите /menu для возврата в это меню"
    
    # Use the new update_or_send_message function
    await update_or_send_message(
        update,
        context,
        menu_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /help command"""
    await show_help_menu(update, context)
    # Show keyboard after help command
    await show_persistent_keyboard(update, context)

async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help information with a back button"""
    user = update.effective_user
    
    # Base commands for all users
    help_text = (
        "*📚 Справка по командам*\n\n"
        "*Основные команды:*\n"
        "• /start - Начать работу с ботом\n"
        "• /help - Показать эту справку\n"
        "• /check - Проверить значение в базе данных\n"
        "• /menu - Открыть главное меню\n"
    )
    
    # Add admin commands if user is admin
    if user.id in ADMIN_IDS:
        help_text += (
            "\n*Команды администратора:*\n"
            "• /admin - Панель администратора\n"
            "• /add - Добавить значение в базу данных\n"
            "• /remove - Удалить значение из базы данных\n"
            "• /list - Показать все значения в базе данных\n"
            "• /broadcast - Отправить сообщение всем пользователям\n"
            "• /stats - Показать статистику бота\n"
        )
    
    # Add back button
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update_or_send_message(
        update,
        context,
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_check_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the check value prompt"""
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update_or_send_message(
        update,
        context,
        "Введите значение для проверки в вайтлисте:",
        reply_markup=reply_markup
    )
    
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
    
    # Use delete_and_update_message instead of update_or_send_message
    await delete_and_update_message(
        update, 
        context,
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
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
            message = await update.message.reply_text("У вас нет прав доступа к этому разделу.")
            await save_active_message(update, context, message)
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
    
    await update_or_send_message(
        update,
        context,
        "*Панель администратора*\n\nВыберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Show persistent keyboard after admin menu
    if not update.callback_query:
        await show_persistent_keyboard(update, context)

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
            message = await update.message.reply_text("У вас нет прав доступа к этому разделу.")
            await save_active_message(update, context, message)
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
    
    await update_or_send_message(
        update,
        context,
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

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
    
    # Use delete_and_update_message instead
    await delete_and_update_message(
        update,
        context,
        message_text,
        reply_markup=reply_markup
    )
    
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
    
    # Use delete_and_update_message instead
    await delete_and_update_message(
        update,
        context,
        message_text,
        reply_markup=reply_markup
    )
    
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
    
    await update_or_send_message(
        update,
        context,
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

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
    
    # Use update_or_send_message instead of creating a new message
    await update_or_send_message(
        update,
        context,
        "Введите сообщение для отправки всем пользователям:",
        reply_markup=reply_markup
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
    
    # Log broadcast event
    db.log_event("broadcast", update.effective_user.id, {"message_length": len(message_text)})
    
    # Try to delete the user's input message
    try:
        await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.debug(f"Could not delete user message: {e}")
    
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

async def show_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show menu for broadcast with options"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
        return
    
    # Instructions for broadcast
    broadcast_text = (
        "*📣 Рассылка сообщений*\n\n"
        "Для отправки сообщения всем пользователям бота, "
        "выберите 'Начать рассылку' и введите текст сообщения.\n\n"
        "После отправки текста сообщения, бот начнет рассылку."
    )
    
    # Add buttons
    keyboard = [
        [InlineKeyboardButton("✉️ Начать рассылку", callback_data="start_broadcast")],
        [InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        # Edit message if callback query
        await update.callback_query.edit_message_text(
            broadcast_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # Send new message if command
        await update.message.reply_text(
            broadcast_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def start_broadcast_from_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start broadcast process from button click"""
    query = update.callback_query
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await query.answer("У вас нет прав доступа к этому разделу.")
        return
    
    # Show message asking for broadcast text
    await query.edit_message_text(
        "*📣 Введите текст сообщения для рассылки:*\n\n"
        "Отправьте текст сообщения, которое будет разослано всем пользователям.",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отменить", callback_data="broadcast_cancel")
        ]])
    )
    
    # Set context variable to expect broadcast message
    context.user_data['expecting_broadcast'] = True

async def start_broadcast_process(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process broadcast message and start sending"""
    message_text = update.message.text
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав доступа к этому разделу.")
        return
    
    # Validate message
    if not message_text or len(message_text.strip()) == 0:
        await update.message.reply_text(
            "Пожалуйста, отправьте непустое текстовое сообщение для рассылки.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")
            ]])
        )
        return
    
    # Get users for broadcasting
    users = db.get_all_users()
    
    if not users:
        await update.message.reply_text(
            "В базе нет пользователей для рассылки.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")
            ]])
        )
        return
    
    # Start broadcast
    status_message = await update.message.reply_text(
        f"🔄 Начинаю рассылку для {len(users)} пользователей...\n\n"
        f"Это может занять некоторое время."
    )
    
    # Send messages
    success_count = 0
    fail_count = 0
    
    for i, (user_id, chat_id) in enumerate(users):
        try:
            # Send the message
            await context.bot.send_message(
                chat_id=chat_id, 
                text=message_text,
                disable_notification=False
            )
            success_count += 1
            
            # Update status message every 10 users
            if (i+1) % 10 == 0 or i+1 == len(users):
                await status_message.edit_text(
                    f"🔄 Рассылка: {i+1}/{len(users)} пользователей...\n"
                    f"✅ Успешно: {success_count}\n"
                    f"❌ Ошибок: {fail_count}"
                )
            
            # Add a small delay to avoid hitting rate limits
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {e}")
            fail_count += 1
    
    # Final status
    await status_message.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"📊 Статистика:\n"
        f"• Всего пользователей: {len(users)}\n"
        f"• Успешно отправлено: {success_count}\n"
        f"• Ошибок: {fail_count}",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")
        ]])
    )
    
    # Log broadcast event
    db.log_event("broadcast", user.id, {
        "total": len(users),
        "success": success_count,
        "fail": fail_count
    })

async def show_persistent_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a persistent keyboard at the bottom of the chat"""
    user = update.effective_user
    
    # Create keyboard buttons
    keyboard = []
    
    # Add common actions
    keyboard.append(["🔍 Проверить", "❓ Помощь"])
    keyboard.append(["🏠 Главное меню"])
    
    # Add admin row if user is admin
    if user.id in ADMIN_IDS:
        keyboard.append(["👑 Админ-панель", "📊 Статистика"])
    
    # Create the reply markup with the keyboard
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,      # Make the keyboard smaller
        one_time_keyboard=False,   # Keep the keyboard visible after selection
        selective=False,           # Show to all users in the chat
        input_field_placeholder="Выберите действие..."  # Placeholder text in input field
    )
    
    # Send new message with keyboard
    if update.message:
        message = await update.message.reply_text(
            "Используйте клавиатуру для быстрого доступа к функциям бота.",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        message = await context.bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text="Используйте клавиатуру для быстрого доступа к функциям бота.",
            reply_markup=reply_markup
        )
    else:
        message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Используйте клавиатуру для быстрого доступа к функциям бота.",
            reply_markup=reply_markup
        )

# Add function to delete user message and update or send message
async def delete_and_update_message(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    text: str, 
    reply_markup=None, 
    parse_mode=None
) -> None:
    """Delete user message, update existing menu message or send a new one"""
    # Try to delete the user's message if possible
    if update.message:
        try:
            await context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
        except Exception as e:
            logger.debug(f"Could not delete user message: {e}")
    
    # Now update or send a new message
    await update_or_send_message(update, context, text, reply_markup, parse_mode)

# Add function to save active message
async def save_active_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message) -> None:
    """Save the active message ID for a user to enable in-place updates"""
    context.user_data[ACTIVE_MESSAGE_KEY] = (message.chat_id, message.message_id)

# Add function to update or send message
async def update_or_send_message(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    text: str, 
    reply_markup=None, 
    parse_mode=None
) -> None:
    """Update existing message or send a new one if no active message exists"""
    if update.callback_query:
        # If this is a callback query, edit the message that originated it
        try:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return
        except Exception as e:
            logger.debug(f"Could not edit callback query message: {e}")
    
    # Check if there's an active message we can edit
    if ACTIVE_MESSAGE_KEY in context.user_data:
        chat_id, message_id = context.user_data[ACTIVE_MESSAGE_KEY]
        try:
            message = await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return
        except Exception as e:
            logger.debug(f"Could not edit message {message_id}: {e}")
    
    # If we couldn't edit an existing message, send a new one
    if update.message:
        message = await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    else:
        # Fallback for callback queries when edit fails
        chat_id = update.effective_chat.id
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    
    # Save this as the new active message
    await save_active_message(update, context, message)

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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for processing all non-command messages"""
    if not update.message or not update.message.text:
        return
    
    # Update user activity
    db.update_user_activity(update.effective_user.id)
    
    text = update.message.text.strip()
    
    # Handle button presses from persistent keyboard
    if text == "🔍 Проверить":
        await show_check_menu(update, context)
        return
    elif text == "❓ Помощь":
        await show_help_menu(update, context)
        return
    elif text == "🏠 Главное меню":
        await show_main_menu(update, context)
        return
    elif text == "👑 Админ-панель" and update.effective_user.id in ADMIN_IDS:
        await show_admin_menu(update, context)
        return
    elif text == "📊 Статистика" and update.effective_user.id in ADMIN_IDS:
        await show_stats_menu(update, context)
        return
    
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
    elif context.user_data.get('expecting_broadcast'):
        context.user_data['expecting_broadcast'] = False
        await start_broadcast_process(update, context)
    else:
        # Normal message handling - check whitelist
        if db.check_whitelist(text):
            keyboard = [
                [InlineKeyboardButton("🔍 Проверить другое значение", callback_data="action_check")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Use delete_and_update_message instead
            await delete_and_update_message(
                update,
                context,
                f"✅ Значение \"{text}\" *найдено* в вайтлисте!",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔍 Проверить другое значение", callback_data="action_check")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Use delete_and_update_message instead
            await delete_and_update_message(
                update,
                context,
                f"❌ Значение \"{text}\" *не найдено* в вайтлисте.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    # Extract the callback data
    data = query.data
    
    # Main menu actions
    if data == "action_check":
        await show_check_menu(update, context)
    elif data == "action_help":
        await show_help_menu(update, context)
    # Admin menu navigation
    elif data == "menu_admin":
        await show_admin_menu(update, context)
    elif data == "back_to_main":
        # Back to main menu
        await show_main_menu(update, context)
    # Admin actions
    elif data == "admin_add":
        await show_add_menu(update, context)
    elif data == "admin_remove":
        await show_remove_menu(update, context)
    elif data == "admin_list":
        await show_list_menu(update, context)
    elif data == "admin_broadcast":
        await show_broadcast_menu(update, context)
    elif data == "admin_stats":
        await show_stats_menu(update, context)
    # Broadcast actions
    elif data == "broadcast_cancel":
        await cancel_broadcast(update, context)
    elif data == "start_broadcast":
        await start_broadcast_from_button(update, context)
    # Other callbacks
    elif data.startswith("remove_"):
        # Extract the value to remove
        value_to_remove = data[7:]  # Remove "remove_" prefix
        success = db.remove_from_whitelist(value_to_remove)
        
        # Create response message with buttons
        if success:
            message_text = f"Значение '{value_to_remove}' успешно удалено из вайтлиста."
        else:
            message_text = f"Не удалось удалить значение '{value_to_remove}' из вайтлиста."
        
        # Add a button to go back to admin menu
        keyboard = [[InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Use delete_and_update_message instead of direct edit
        await delete_and_update_message(
            update,
            context,
            message_text,
            reply_markup=reply_markup
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
        persistent=False,
        per_chat=True
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
        persistent=False,
        per_chat=True
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
        persistent=False,
        per_chat=True
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
        persistent=False,
        per_chat=True
    )
    application.add_handler(broadcast_conv_handler)
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Set up the menu commands
    async def setup_commands(application):
        bot = application.bot
        commands = [
            BotCommand("start", "Начать работу с ботом"),
            BotCommand("help", "Показать справку"),
            BotCommand("check", "Проверить значение в списке"),
            BotCommand("menu", "Открыть главное меню")
        ]
        
        # Add admin commands for admin users only
        admin_commands = commands + [
            BotCommand("admin", "Панель администратора"),
            BotCommand("add", "Добавить значение в список"),
            BotCommand("remove", "Удалить значение из списка"),
            BotCommand("list", "Показать все значения в списке"),
            BotCommand("broadcast", "Отправить сообщение всем пользователям"),
            BotCommand("stats", "Показать статистику бота")
        ]
        
        # Set regular commands for all users
        await bot.set_my_commands(commands)
        
        # Set admin commands for admin users
        for admin_id in ADMIN_IDS:
            try:
                await bot.set_my_commands(
                    admin_commands,
                    scope=BotCommandScopeChat(chat_id=admin_id)
                )
            except Exception as e:
                logger.error(f"Failed to set admin commands for user {admin_id}: {e}")
    
    # Run the setup_commands function on startup
    application.post_init = setup_commands
    
    # Add command handler for menu command
    application.add_handler(CommandHandler("menu", show_main_menu))
    
    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling()
    
    logger.info("Bot stopped")

if __name__ == "__main__":
    main() 
