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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG
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
AWAITING_WL_TYPE = 4
AWAITING_WL_REASON = 5

# WL types and reasons
WL_TYPES = ["GTD", "FCFS"]
WL_REASONS = ["Fluffy holder", "X contributor"]

# Keys for storing the active message in user_data
ACTIVE_MESSAGE_KEY = 'active_message'  # Store (chat_id, message_id) for active menu

# Константа для хранения последнего сообщения бота
BOT_ACTIVE_MESSAGE_KEY = 'active_bot_message'  # Ключ для хранения ID активного сообщения бота

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
    
    # Приветственное сообщение с красивым форматированием
    welcome_text = (
        f"👋 *Добро пожаловать, {user.first_name}!*\n\n"
        f"Я бот *MegaBuddies*, который поможет вам проверить информацию в нашей базе данных.\n\n"
        f"🔹 Просто отправьте мне текст для проверки в базе\n"
        f"🔹 Или используйте встроенные кнопки меню для навигации\n\n"
        f"Открываю главное меню..."
    )
    
    # First send welcome message
    message = await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown'
    )
    
    # Then show main menu with inline buttons
    await show_main_menu(update, context)
    
    # Also show persistent keyboard at bottom
    await show_persistent_keyboard(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main menu with inline keyboard"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Проверить", callback_data="check"),
            InlineKeyboardButton("ℹ️ Помощь", callback_data="help"),
            InlineKeyboardButton("🔗 Links/FAQ", callback_data="links")
        ]
    ]
    
    if is_admin(update.effective_user):
    keyboard.append([
            InlineKeyboardButton("➕ Добавить", callback_data="add"),
            InlineKeyboardButton("🔍 Просмотр", callback_data="view")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    menu_text = (
        f"👋 Привет, {update.effective_user.first_name}!\n\n"
        "Это бот для проверки и управления BuddyWL.\n\n"
        "✅ Нажмите *Проверить* чтобы проверить значение в вайтлисте\n"
        "ℹ️ Нажмите *Помощь* для получения справки\n"
        "🔗 Нажмите *Links/FAQ* для просмотра полезных ссылок"
    )
    
    if is_admin(update.effective_user):
        menu_text += (
            "\n\n*Команды администратора:*\n"
            "➕ *Добавить* - добавить новое значение в вайтлист\n"
            "🔍 *Просмотр* - просмотреть все значения в вайтлисте"
        )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            menu_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
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
            "• `/stats` - Показать статистику бота\n\n"
        )
    
    # Add back button
    keyboard = [[InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update_or_send_message(
        update,
        context,
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_check_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show menu for checking a value against whitelist"""
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = "Введите значение для проверки в базе данных:"
    
    if update.callback_query:
        # Когда нажата кнопка "Проверить ещё", отправляем новое сообщение
        # вместо редактирования текущего
        query = update.callback_query
        await query.answer()
        
        # Отправляем новое сообщение
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup
        )
    
    # Устанавливаем флаг, чтобы знать, что следующее сообщение - для проверки
    context.user_data['expecting_check'] = True
    
    # Очищаем активное сообщение, чтобы не редактировать его
    if BOT_ACTIVE_MESSAGE_KEY in context.chat_data:
        del context.chat_data[BOT_ACTIVE_MESSAGE_KEY]
    
    return AWAITING_CHECK_VALUE

async def handle_check_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle checking a value in the whitelist"""
    user = update.effective_user
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "Пожалуйста, введите значение для проверки в вайтлисте:"
        )
        # Set state to waiting for check input
        context.user_data["waiting_for"] = "check_input"
        return
    
    # If we're here from a message, get the value from the message
    if "waiting_for" in context.user_data and context.user_data["waiting_for"] == "check_input":
        value = update.message.text.strip()
        context.user_data.pop("waiting_for", None)
    else:
        # Direct message case, not from callback flow
    value = update.message.text.strip()
    
    # Check if the value is in the whitelist
    result = db.is_in_whitelist(value)
    logging.info(f"Check result for '{value}': {result}")
    
    # Build keyboard for next actions
    keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if result:
        wl_type = result.get('type', 'Не указан')
        reason = result.get('reason', 'Не указана')
        timestamp = result.get('timestamp', 'Не указано')
        
        message_text = (
            f"✅ Поздравляем, {user.first_name}!\n\n"
            f"Значение *{value}* найдено в вайтлисте MegaBuddies!\n\n"
            f"*Тип вайтлиста:* {wl_type}\n"
            f"*Причина:* {reason}\n"
            f"*Добавлено:* {timestamp}"
        )
    else:
        message_text = (
            f"❌ Нам жаль, {user.first_name}, но введенного значения пока нет в BuddyWL.\n\n"
            f"Мы с нетерпением ждем твой вклад и надеемся скоро увидеть тебя уже вместе с твоим Buddy! 🤗"
        )
    
    # Send new message with results
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the admin panel menu"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        # If not admin, show error and return to main menu
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
            await show_main_menu(update, context)
        else:
            await update_or_send_message(
                update, 
                context,
                "⛔ У вас нет прав доступа к этому разделу.",
                parse_mode='Markdown'
            )
        return
    
    # Admin menu keyboard - optimized layout
    keyboard = [
        [
            InlineKeyboardButton("➕ Добавить запись", callback_data="admin_add"),
            InlineKeyboardButton("➖ Удалить запись", callback_data="admin_remove")
        ],
        [
            InlineKeyboardButton("📋 База данных", callback_data="admin_list"),
            InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("📨 Рассылка сообщений", callback_data="admin_broadcast")
        ],
        [InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_text = (
        "*👑 Панель администратора*\n\n"
        "Выберите действие из списка ниже:\n\n"
        "• *Добавить* - добавление записи в базу данных\n"
        "• *Удалить* - удаление записи из базы данных\n"
        "• *База данных* - просмотр всех записей\n"
        "• *Статистика* - просмотр статистики использования\n"
        "• *Рассылка* - отправка сообщений пользователям\n"
    )
    
    await update_or_send_message(
        update,
        context,
        admin_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

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
            "⌨️ Введите значение для добавления в базу данных.\n\n"
            "❗️ Важно: следующее сообщение будет добавлено в базу данных.",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "⌨️ Введите значение для добавления в базу данных.\n\n"
            "❗️ Важно: следующее сообщение будет добавлено в базу данных.",
            reply_markup=reply_markup
        )
    
    # Устанавливаем флаг, чтобы знать, что следующее сообщение - для добавления в вайтлист
    context.user_data['expecting_add'] = True
    # Очищаем данные о текущем добавлении
    if 'add_data' in context.user_data:
        del context.user_data['add_data']
    
    return AWAITING_ADD_VALUE

async def handle_add_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the value for whitelist and ask for WL type"""
    value = update.message.text.strip()
    
    # Добавляем логирование
    logger.debug(f"Получено значение для добавления в базу данных: '{value}'")
    
    # Сохраняем значение в промежуточных данных
    context.user_data['add_data'] = {'value': value}
    logger.debug(f"Установлены данные add_data: {context.user_data['add_data']}")
    
    # Создаем клавиатуру для выбора типа вайтлиста
    keyboard = []
    for wl_type in WL_TYPES:
        keyboard.append([InlineKeyboardButton(wl_type, callback_data=f"wl_type_{wl_type}")])
    keyboard.append([InlineKeyboardButton("◀️ Отмена", callback_data="menu_admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем запрос на выбор типа вайтлиста
    message_text = (
        f"Значение для добавления: *{value}*\n\n"
        f"Выберите тип вайтлиста:"
    )
    
    # Удаляем сообщение пользователя
    try:
        await context.bot.delete_message(
            chat_id=update.message.chat_id,
            message_id=update.message.message_id
        )
    except Exception as e:
        logger.debug(f"Could not delete user message: {e}")
    
    # Отправляем сообщение с кнопками для выбора типа
    await update_or_send_message(
        update,
        context,
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.debug(f"Переход в состояние AWAITING_WL_TYPE ({AWAITING_WL_TYPE})")
    return AWAITING_WL_TYPE

async def handle_wl_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process WL type selection and ask for reason"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем выбранный тип из callback_data
    selected_type = query.data.replace("wl_type_", "")
    logger.debug(f"Выбран тип WL: {selected_type}")
    
    # Проверяем наличие данных add_data
    if 'add_data' not in context.user_data:
        logger.error("Ошибка: не найдены данные 'add_data' в контексте пользователя")
        await query.edit_message_text(
            "❌ Произошла ошибка: данные о добавлении не найдены. Пожалуйста, начните процесс добавления заново.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад к добавлению", callback_data="admin_add")
            ]])
        )
        return ConversationHandler.END
    
    # Проверяем, что тип в списке допустимых
    if selected_type not in WL_TYPES:
        logger.error(f"Ошибка: выбранный тип '{selected_type}' отсутствует в списке допустимых типов")
        await query.edit_message_text(
            "❌ Произошла ошибка при выборе типа. Попробуйте снова.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад к добавлению", callback_data="admin_add")
            ]])
        )
        return ConversationHandler.END
    
    # Сохраняем тип вайтлиста
    context.user_data['add_data']['wl_type'] = selected_type
    logger.debug(f"Обновлены данные add_data: {context.user_data['add_data']}")
    
    # Создаем клавиатуру для выбора причины
    keyboard = []
    for reason in WL_REASONS:
        keyboard.append([InlineKeyboardButton(reason, callback_data=f"wl_reason_{reason}")])
    keyboard.append([InlineKeyboardButton("◀️ Отмена", callback_data="menu_admin")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем запрос на выбор причины
    value = context.user_data['add_data']['value']
    message_text = (
        f"Значение для добавления: *{value}*\n"
        f"Тип вайтлиста: *{selected_type}*\n\n"
        f"Выберите причину добавления в вайтлист:"
    )
    
    await query.edit_message_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.debug(f"Переход в состояние AWAITING_WL_REASON ({AWAITING_WL_REASON})")
    return AWAITING_WL_REASON

async def handle_wl_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process WL reason and add to whitelist"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем выбранную причину из callback_data
    selected_reason = query.data.replace("wl_reason_", "")
    logger.debug(f"Выбрана причина WL: {selected_reason}")
    
    # Проверяем наличие данных add_data
    if 'add_data' not in context.user_data or 'value' not in context.user_data.get('add_data', {}):
        logger.error("Ошибка: не найдены полные данные 'add_data' в контексте пользователя")
        await query.edit_message_text(
            "❌ Произошла ошибка: данные о добавлении не найдены или неполные. Пожалуйста, начните процесс добавления заново.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад к добавлению", callback_data="admin_add")
            ]])
        )
        return ConversationHandler.END
    
    # Проверяем, что причина в списке допустимых
    if selected_reason not in WL_REASONS:
        logger.error(f"Ошибка: выбранная причина '{selected_reason}' отсутствует в списке допустимых причин")
        await query.edit_message_text(
            "❌ Произошла ошибка при выборе причины. Попробуйте снова.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад к добавлению", callback_data="admin_add")
            ]])
        )
        return ConversationHandler.END
    
    # Получаем сохраненные данные
    add_data = context.user_data.get('add_data', {})
    value = add_data.get('value', '')
    wl_type = add_data.get('wl_type', 'FCFS')
    
    logger.debug(f"Данные для добавления в базу: value='{value}', type='{wl_type}', reason='{selected_reason}'")
    
    # Добавляем запись в вайтлист
    try:
        success = db.add_to_whitelist(value, wl_type, selected_reason)
    
    # Log event
        db.log_event("add_whitelist", update.effective_user.id, {
            "value": value, 
            "wl_type": wl_type, 
            "wl_reason": selected_reason
        }, success)
    
    # Create response message
    if success:
            logger.debug(f"Значение '{value}' успешно добавлено в базу данных")
            message_text = (
                f"✅ Запись успешно добавлена в вайтлист!\n\n"
                f"*Значение:* `{value}`\n"
                f"*Тип WL:* {wl_type}\n"
                f"*Причина:* {selected_reason}"
            )
    else:
            logger.debug(f"Значение '{value}' уже существует в базе данных")
        message_text = f"⚠️ Значение \"{value}\" уже существует в вайтлисте."
    
    # Buttons for next action
    keyboard = [
        [InlineKeyboardButton("➕ Добавить еще", callback_data="admin_add")],
        [InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
        # Send the response
        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Очищаем данные о добавлении
        if 'add_data' in context.user_data:
            del context.user_data['add_data']
            logger.debug("Данные add_data очищены из контекста пользователя")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении значения в базу данных: {e}")
        message_text = f"❌ Произошла ошибка при добавлении значения \"{value}\" в базу данных."
        
        keyboard = [
            [InlineKeyboardButton("↩️ Попробовать снова", callback_data="admin_add")],
            [InlineKeyboardButton("◀️ Назад к админ-панели", callback_data="menu_admin")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
        message_text,
        reply_markup=reply_markup
    )
    
        # Очищаем данные о добавлении
        if 'add_data' in context.user_data:
            del context.user_data['add_data']
            logger.debug("Данные add_data очищены из контекста пользователя после ошибки")
        
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
    
    # Устанавливаем флаг, чтобы знать, что следующее сообщение - для удаления из вайтлиста
    context.user_data['expecting_remove'] = True
    
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
    """Show all values in whitelist with pagination"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
        else:
            await update_or_send_message(
                update,
                context,
                "⛔ У вас нет прав доступа к этому разделу.",
                parse_mode='Markdown'
            )
        return
    
    # Get values from whitelist
    items = db.get_all_whitelist()
    
    # Create response message
    if items:
        items_per_page = 5  # Меньше записей на странице, так как каждая запись теперь содержит больше информации
        page = context.user_data.get('whitelist_page', 0)
        total_pages = (len(items) + items_per_page - 1) // items_per_page
        
        # Ensure page is valid
        if page >= total_pages:
            page = 0
        
        # Save current page
        context.user_data['whitelist_page'] = page
        
        # Get values for current page
        start = page * items_per_page
        end = min(start + items_per_page, len(items))
        
        message_text = (
            f"*📋 База данных*\n\n"
            f"Всего записей: {len(items)}\n"
            f"Страница {page+1} из {total_pages}\n\n"
        )
        
        # Add values with numbering in a clean format
        for i, item in enumerate(items[start:end], start=start+1):
            message_text += (
                f"{i}. `{item['value']}`\n"
                f"   Тип: {item['wl_type']}, Причина: {item['wl_reason']}\n\n"
            )
        
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
        message_text = "*📋 База данных*\n\nБаза данных пуста."
    
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
        await update_or_send_message(
            update,
            context,
            "Пожалуйста, отправьте текстовое сообщение.",
            InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Отмена", callback_data="broadcast_cancel")
            ]])
        )
        return BROADCAST_MESSAGE
    
    users = db.get_all_users()
    
    if not users:
        await update_or_send_message(
            update,
            context,
            "В базе нет пользователей для рассылки.",
            InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="menu_admin")
            ]])
        )
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
    
    # Use our main message for progress updates
    await update_or_send_message(
        update,
        context,
        f"Начинаю рассылку для {len(users)} пользователей..."
    )
    
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
                await update_or_send_message(
                    update,
                    context,
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
    
    await update_or_send_message(
        update,
        context,
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
    """Show a minimal persistent keyboard at the bottom of the chat"""
    user = update.effective_user
    
    # Create keyboard buttons - simplified for cleaner UI
    keyboard = []
    
    # Just basic navigation - minimalist approach
    keyboard.append(["🔍 Проверить", "🏠 Меню"])
    
    # Add admin button if user is admin
    if user.id in ADMIN_IDS:
        keyboard.append(["👑 Админ"])
    
    # Create the reply markup with the keyboard
    reply_markup = ReplyKeyboardMarkup(
        keyboard,
        resize_keyboard=True,      # Make the keyboard smaller
        one_time_keyboard=False,   # Keep the keyboard visible
        selective=False,           # Show to all users in the chat
        input_field_placeholder="Введите текст для проверки..."  # Helpful placeholder
    )
    
    # Set the keyboard without sending a message
    if update.message:
        await update.message.reply_text(
            "⌨️ Клавиатура активирована",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await context.bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text="⌨️ Клавиатура активирована",
            reply_markup=reply_markup
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⌨️ Клавиатура активирована",
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
    """Delete user message and update the single bot message or send a new one"""
    # Try to delete the user's message if possible
    if update.message:
        try:
            await context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
        except Exception as e:
            logger.debug(f"Could not delete user message: {e}")
    
    # Then update the bot's single message
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
    """Update existing message or send a new one for clean interface"""
    # If this is a callback query, try to edit the message
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return
        except Exception as e:
            logger.debug(f"Could not edit callback query message: {e}")
    
    # If we have an active message ID for this chat, try to edit it
    chat_id = chat_id_from_update(update)
    if BOT_ACTIVE_MESSAGE_KEY in context.chat_data:
        active_message_id = context.chat_data[BOT_ACTIVE_MESSAGE_KEY]
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=active_message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return
        except Exception as e:
            logger.debug(f"Could not edit active message {active_message_id}: {e}")
    
    # If we couldn't edit, send a new message
    if update.message:
        message = await update.message.reply_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    else:
        message = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    
    # Store the message ID as the active one for this chat
    context.chat_data[BOT_ACTIVE_MESSAGE_KEY] = message.message_id

async def clean_old_bot_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clean up old bot messages to keep chat clean, except the active message"""
    chat_id = chat_id_from_update(update)
    
    # If we have an active message, keep track of it
    active_message_id = None
    if BOT_ACTIVE_MESSAGE_KEY in context.chat_data:
        active_message_id = context.chat_data[BOT_ACTIVE_MESSAGE_KEY]
    
    # Try to get recent messages to delete old ones
    try:
        # We can only delete recent messages that the bot sent
        # We'll use getUpdates with a limit to avoid excessive API calls
        # This is an approximation as getUpdates has limitations
        recent_updates = await context.bot.get_updates(limit=10, timeout=0)
        
        # Find messages from this bot in this chat
        bot_id = context.bot.id
        for bot_update in recent_updates:
            if (bot_update.message and 
                bot_update.message.from_user and 
                bot_update.message.from_user.id == bot_id and
                bot_update.message.chat_id == chat_id and
                (active_message_id is None or bot_update.message.message_id != active_message_id)):
                
                # Try to delete this old message
                try:
                    await context.bot.delete_message(
                        chat_id=chat_id,
                        message_id=bot_update.message.message_id
                    )
                except Exception as e:
                    logger.debug(f"Could not delete old bot message: {e}")
    except Exception as e:
        logger.debug(f"Error getting updates to clean messages: {e}")

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
    
    # Добавляем логирование для диагностики
    user_id = update.effective_user.id
    logger.debug(f"Получено сообщение от пользователя {user_id}: '{text}'")
    logger.debug(f"Текущие флаги пользователя: expecting_check={context.user_data.get('expecting_check')}, expecting_add={context.user_data.get('expecting_add')}, expecting_remove={context.user_data.get('expecting_remove')}")
    
    # Handle button presses from persistent keyboard - simplified
    if text == "🔍 Проверить":
        await show_check_menu(update, context)
        return
    elif text == "🏠 Меню":
        await show_main_menu(update, context)
        return
    elif text == "👑 Админ" and update.effective_user.id in ADMIN_IDS:
        await show_admin_menu(update, context)
        return
    
    # Handle conversation states with явным приоритетом для добавления и удаления
    if context.user_data.get('expecting_add'):
        logger.debug(f"Обработка сообщения для добавления в базу данных: '{text}'")
        context.user_data['expecting_add'] = False
        await handle_add_value(update, context)
        return  # Добавлен явный return, чтобы избежать проверки whitelist
    elif context.user_data.get('expecting_remove'):
        logger.debug(f"Обработка сообщения для удаления из базы данных: '{text}'")
        context.user_data['expecting_remove'] = False
        await handle_remove_value(update, context)
        return  # Добавлен явный return, чтобы избежать проверки whitelist
    elif context.user_data.get('expecting_check'):
        logger.debug(f"Обработка сообщения для проверки в базе данных: '{text}'")
        context.user_data['expecting_check'] = False
        await handle_check_value(update, context)
        return  # Добавлен явный return, чтобы избежать проверки whitelist
    elif context.user_data.get('expecting_broadcast'):
        logger.debug(f"Обработка сообщения для рассылки: '{text}'")
        context.user_data['expecting_broadcast'] = False
        await start_broadcast_process(update, context)
        return  # Добавлен явный return, чтобы избежать проверки whitelist
    else:
        # Normal message handling - check whitelist
        # Treat any text as a check query for simplicity
        logger.debug(f"Обработка обычного сообщения как проверки в базе данных: '{text}'")
        
        # Check the value against whitelist
        value = text
        result = db.check_whitelist(value)
        user = update.effective_user
        
        # Create beautiful response
        if result["found"]:
            message_text = (
                f"*✅ Результат проверки*\n\n"
                f"Привет, {user.first_name}! 👋\n\n"
                f"Значение `{value}` *найдено* в базе данных!\n\n"
                f"У вас {result['wl_type']} WL потому что вы {result['wl_reason']}! 🎉"
            )
        else:
            message_text = (
                f"*❌ Результат проверки*\n\n"
                f"Нам жаль, {user.first_name}, но введенного значения пока нет в BuddyWL.\n\n"
                f"Мы с нетерпением ждем твой вклад и надеемся скоро увидеть тебя уже вместе с твоим Buddy! 🤗"
            )
        
        # Buttons for next action
        keyboard = [
            [InlineKeyboardButton("🔄 Проверить ещё", callback_data="action_check")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Try to delete the user message for cleaner interface
        try:
            await context.bot.delete_message(
                chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
        except Exception as e:
            logger.debug(f"Could not delete user message: {e}")
        
        # Всегда отправляем новое сообщение с результатом
        chat_id = update.effective_chat.id
        await context.bot.send_message(
            chat_id=chat_id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Очищаем активное сообщение
        if BOT_ACTIVE_MESSAGE_KEY in context.chat_data:
            del context.chat_data[BOT_ACTIVE_MESSAGE_KEY]

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    logging.info(f"Button callback: {data}, User: {update.effective_user.id}, Username: {update.effective_user.username}")

    if data == "check":
        await handle_check_value(update, context)
    elif data == "help":
        await show_help_menu(update, context)
    elif data == "links":
        await show_links_menu(update, context)
    elif data == "back_to_main":
        await show_main_menu(update, context)
    elif data == "add" and is_admin(update.effective_user):
        await handle_add_value(update, context)
    elif data == "view" and is_admin(update.effective_user):
        context.user_data["page"] = 0
        await handle_view_values(update, context)
    elif data == "next_page" and is_admin(update.effective_user):
        context.user_data["page"] = context.user_data.get("page", 0) + 1
        await handle_view_values(update, context)
    elif data == "prev_page" and is_admin(update.effective_user):
        context.user_data["page"] = max(0, context.user_data.get("page", 0) - 1)
        await handle_view_values(update, context)
    elif data.startswith("wl_type_"):
        # Extract whitelist type from callback
        wl_type = data.replace("wl_type_", "")
        # Save whitelist type to user_data
        context.user_data["wl_type"] = wl_type
        # Show reason selection keyboard
        await show_reason_selection(update, context)
    elif data.startswith("reason_"):
        # Extract reason from callback
        reason = data.replace("reason_", "")
        # Save reason to user_data
        context.user_data["reason"] = reason
        # Complete the add action
        await add_value_to_db(update, context)
        else:
        logging.warning(f"Unknown callback data: {data}")
        await query.edit_message_text(text="Неизвестное действие!")
        await show_main_menu(update, context)

async def show_links_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show useful links and FAQ for MegaBuddies project"""
    
    # Links content
    links_text = (
        "*🔗 Полезные ссылки и FAQ*\n\n"
        "*Официальные ресурсы MegaBuddies:*\n\n"
        "• [Официальный сайт](https://megabuddies.io)\n"
        "• [Twitter/X](https://twitter.com/megabuddies)\n"
        "• [Discord](https://discord.gg/megabuddies)\n"
        "• [Telegram канал](https://t.me/megabuddies_official)\n"
        "• [Telegram чат](https://t.me/megabuddies_chat)\n\n"
        
        "*Часто задаваемые вопросы:*\n\n"
        "• *Что такое BuddyWL?*\n"
        "  Это вайтлист для участников, которые внесли вклад в проект.\n\n"
        "• *Как попасть в вайтлист?*\n"
        "  Присоединяйтесь к нашему Discord или Telegram для получения информации о текущих активностях.\n\n"
        "• *Когда запуск проекта?*\n"
        "  Следите за обновлениями в наших официальных каналах.\n\n"
    )
    
    # Back button
    keyboard = [[InlineKeyboardButton("🏠 Вернуться в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
    if update.callback_query:
        await update.callback_query.edit_message_text(
            links_text,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            disable_web_page_preview=True  # Disable previews for cleaner UI
        )
    else:
        await update.message.reply_text(
            links_text,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

async def handle_links_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /links command"""
    await show_links_menu(update, context)

async def setup_commands(application: Application) -> None:
    """Setup bot commands and descriptions"""
    commands = [
        BotCommand("start", "Запустить бота и показать главное меню"),
        BotCommand("help", "Показать справку"),
        BotCommand("check", "Проверить значение в вайтлисте"),
        BotCommand("links", "Показать полезные ссылки")
    ]
    
    # Настраиваем команды
    await application.bot.set_my_commands(commands)
    
    # Настраиваем описание бота, которое будет отображаться до старта
    bot_description = (
        "🤖 MegaBuddies WL Bot\n\n"
        "Официальный бот проекта MegaBuddies для проверки статуса в вайтлисте."
        " Узнайте, есть ли вы в вайтлисте, получите полезные ссылки и информацию о проекте."
    )
    
    try:
        await application.bot.set_my_description(bot_description)
        logging.info("Bot description successfully set")
        
        # Настраиваем короткое описание
        await application.bot.set_my_short_description("MegaBuddies WL Bot - проверка статуса в вайтлисте и управление")
        logging.info("Bot short description successfully set")
    except Exception as e:
        logging.error(f"Error setting bot description: {e}")

    logging.info("Bot commands and descriptions setup completed")

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
    application.add_handler(CommandHandler("links", handle_links_command))
    
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
        entry_points=[
            CommandHandler("add", show_add_menu),
            CallbackQueryHandler(show_add_menu, pattern="^admin_add$")
        ],
        states={
            AWAITING_ADD_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_add_value)],
            AWAITING_WL_TYPE: [CallbackQueryHandler(handle_wl_type, pattern="^wl_type_")],
            AWAITING_WL_REASON: [CallbackQueryHandler(handle_wl_reason, pattern="^wl_reason_")]
        },
        fallbacks=[
            CallbackQueryHandler(button_callback, pattern="^menu_admin$"),
            CallbackQueryHandler(button_callback, pattern="^back_to_main$"),
            MessageHandler(filters.COMMAND, button_callback)
        ],
        name="add_conversation",
        persistent=False,
        per_chat=True,
        per_user=True
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
    
    # Add command handler for menu command
    application.add_handler(CommandHandler("menu", show_main_menu))
    
    # Add callback query handler - перемещено после ConversationHandler, но перед MessageHandler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler - последним, чтобы перехватывать только те сообщения, которые не обработаны другими обработчиками
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Setup bot commands and descriptions
    application.job_queue.run_once(lambda _: asyncio.create_task(setup_commands(application)), 0)
    
    # Start the Bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info("Bot stopped")

if __name__ == "__main__":
    main() 
