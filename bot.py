import os
import logging
import asyncio
import time
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple, Set
import functools

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    BotCommand,
    BotCommandScopeChat
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    PicklePersistence,
    Defaults
)

from database import Database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG)
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
# States for contribution flow
AWAITING_CONTRIBUTE_VALUE = 6
AWAITING_CONTRIBUTE_LINK = 7
AWAITING_CONTRIBUTE_DESCRIPTION = 8

# WL types and reasons
WL_TYPES = ["GTD", "FCFS"]
WL_REASONS = ["Fluffy holder", "X contributor"]

# Keys for storing the active message in user_data
# Store (chat_id, message_id) for active menu
ACTIVE_MESSAGE_KEY = 'active_message'

# Константа для хранения последнего сообщения бота
# Ключ для хранения ID активного сообщения бота
BOT_ACTIVE_MESSAGE_KEY = 'active_bot_message'

# Декоратор для измерения скорости выполнения функций


def measure_time(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        execution_time = time.time() - start_time

        # Логируем только медленные операции (более 0.5 секунды)
        if execution_time > 0.5:
            logger.info(
                f"Performance: {
                    func.__name__} took {
                    execution_time:.2f} seconds")

        return result
    return wrapper

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


async def show_main_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the main menu"""
    # Keyboard for main menu
    keyboard = [
        [InlineKeyboardButton("🔍 Проверить", callback_data="action_check")],
        [InlineKeyboardButton("🔗 Внести свой вклад", callback_data="action_contribute")],
    ]

    # Add admin buttons if user is admin
    user = update.effective_user
    if user and user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton(
            "📊 Статистика", callback_data="action_stats")])

    # Add links/FAQ button for all users
    keyboard.append([InlineKeyboardButton(
        "📚 Ссылки/FAQ", callback_data="action_links")])

    # Add admin panel button if user is admin
    if user and user.id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton(
            "🔐 Админ-панель", callback_data="action_admin")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Main menu message
    message_text = (
        "*👋 Главное меню MegaBuddies WL Bot*\n\n"
        "Здесь вы можете:\n"
        "• Проверить адрес в вайтлисте\n"
        "• Внести свой вклад, поделившись полезными ссылками\n"
    )

    if user and user.id in ADMIN_IDS:
        message_text += "• Просмотреть статистику\n"

    message_text += "• Найти полезные ссылки и FAQ\n"

    if user and user.id in ADMIN_IDS:
        message_text += "• Управлять вайтлистом (админ)\n"

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


async def help_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /help command"""
    await show_help_menu(update, context)
    # Show keyboard after help command
    await show_persistent_keyboard(update, context)


async def show_help_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help information with a back button"""
    user = update.effective_user

    # Base commands for all users
    help_text = (
        "*📚 Справка по MegaBuddies*\n\n"
        "*Основные команды:*\n"
        "• `/start` - Начать работу с ботом\n"
        "• `/help` - Показать эту справку\n"
        "• `/check` - Проверить значение в базе\n"
        "• `/contribute` - Внести свой вклад\n"
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
    keyboard = [[InlineKeyboardButton(
        "🏠 Вернуться в главное меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update_or_send_message(
        update,
        context,
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_check_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show menu for checking a value against whitelist"""
    keyboard = [[InlineKeyboardButton(
        "◀️ Назад", callback_data="back_to_main")]]
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


@measure_time
async def handle_check_value(update: Update,
                             context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle checking a value in the whitelist"""
    user = update.effective_user
    value = update.message.text.strip()

    logger.debug(
        f"Проверка значения в базе данных: '{value}' от пользователя {user.id}")

    try:
        # Check the value against whitelist
        result = db.check_whitelist(value)

        # Log the check event
        db.log_event(
            "check_whitelist",
            update.effective_user.id,
            {"value": value},
            bool(result.get("found", False))
        )

        # Create reply markup with buttons for next actions
        keyboard = [
            [InlineKeyboardButton(
                "🔄 Проверить другое значение", callback_data="action_check")],
            [InlineKeyboardButton(
                "🏠 Вернуться в главное меню", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Prepare response message
        if result.get("found", False):
            message_text = (
                f"✅ {user.first_name}, ваше значение найдено в вайтлисте!\n\n"
                f"*Значение:* `{value}`\n"
                f"*Тип WL:* {result.get('wl_type', 'Не указан')}\n"
                f"*Причина:* {result.get('wl_reason', 'Не указана')}"
            )
        else:
            message_text = (
                f"❌ {
                    user.first_name}, к сожалению, значение `{value}` не найдено в вайтлисте.\n\n"
                f"Мы с нетерпением ждем вашего вклада в проект. "
                f"Следите за анонсами в наших социальных сетях, чтобы узнать о новых возможностях попасть в вайтлист!"
            )

        # Try to delete the user's message for cleaner interface
        try:
            await update.message.delete()
        except Exception as e:
            logger.warning(
                f"Не удалось удалить сообщение пользователя: {e}")

        # Send a new message with the result
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(
            f"Ошибка при проверке значения в базе данных: {e}")
        await update.message.reply_text(
            "⚠️ Произошла ошибка при проверке. Пожалуйста, попробуйте еще раз или обратитесь к администратору.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🏠 Главное меню", callback_data="back_to_main")
            ]])
        )

        # Reset the conversation state for this user
        # Now the user can go in different directions based on buttons
        # or start a new check by sending another message
        return ConversationHandler.END


async def show_admin_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
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
            InlineKeyboardButton(
                "➕ Добавить запись",
                callback_data="admin_add"),
            InlineKeyboardButton(
                "➖ Удалить запись",
                callback_data="admin_remove")
        ],
        [
            InlineKeyboardButton(
                "📋 База данных", callback_data="admin_list"),
            InlineKeyboardButton(
                "📊 Статистика", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(
                "📨 Рассылка", callback_data="admin_broadcast"),
            InlineKeyboardButton(
                "📤 Экспорт", callback_data="admin_export")
        ],
        [
            InlineKeyboardButton(
                "📥 Импорт", callback_data="admin_import")
        ],
        [InlineKeyboardButton("🏠 Вернуться в главное меню",
                              callback_data="back_to_main")]
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
        "• *Экспорт* - выгрузка базы данных в CSV\n"
        "• *Импорт* - загрузка данных из CSV файла\n"
    )

    await update_or_send_message(
        update,
        context,
        admin_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def stats_command(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /stats command"""
    await show_stats_menu(update, context)


async def show_stats_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show statistics of the bot usage"""
    user = update.effective_user

    # Check if user is admin
    if user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
            return
        else:
            await update.message.reply_text("⛔ У вас нет прав доступа к этому разделу.")
            return

    # Get statistics
    total_users = db.get_total_users()
    active_users = db.get_active_users()
    whitelist_count = db.get_whitelist_count()
    checks_count = db.get_checks_count()
    last_day_checks = db.get_checks_count(days=1)
    last_week_checks = db.get_checks_count(days=7)

    # Format message
    stats_text = (
        "*📊 Статистика бота*\n\n"
        f"*Пользователи:*\n"
        f"Всего пользователей: {total_users}\n"
        f"Активных за 7 дней: {active_users}\n\n"

        f"*База данных:*\n"
        f"Записей в базе: {whitelist_count}\n\n"

        f"*Проверки:*\n"
        f"Всего проверок: {checks_count}\n"
        f"За последние 24 часа: {last_day_checks}\n"
        f"За последнюю неделю: {last_week_checks}\n"
    )

    # Add back button
    keyboard = [[InlineKeyboardButton(
        "🏠 Вернуться в главное меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Update message or send new
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


async def show_add_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show menu for adding a value to whitelist"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
            return ConversationHandler.END

        keyboard = [[InlineKeyboardButton(
            "◀️ Назад", callback_data="menu_admin")]]
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

        # Устанавливаем флаг, чтобы знать, что следующее сообщение - для
        # добавления в вайтлист
        context.user_data['expecting_add'] = True
        # Очищаем данные о текущем добавлении
        if 'add_data' in context.user_data:
            del context.user_data['add_data']

        return AWAITING_ADD_VALUE


async def handle_add_value(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the value for whitelist and ask for WL type"""
    value = update.message.text.strip()

    # Добавляем логирование
    logger.debug(
        f"Получено значение для добавления в базу данных: '{value}'")

    # Сохраняем значение в промежуточных данных
    context.user_data['add_data'] = {'value': value}
    logger.debug(
        f"Установлены данные add_data: {
            context.user_data['add_data']}")

    # Создаем клавиатуру для выбора типа вайтлиста
    keyboard = []
    for wl_type in WL_TYPES:
        keyboard.append([InlineKeyboardButton(
            wl_type, callback_data=f"wl_type_{wl_type}")])
    keyboard.append([InlineKeyboardButton(
        "◀️ Отмена", callback_data="menu_admin")])
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

    logger.debug(
        f"Переход в состояние AWAITING_WL_TYPE ({AWAITING_WL_TYPE})")
    return AWAITING_WL_TYPE


async def handle_wl_type(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process WL type selection and ask for reason"""
    query = update.callback_query
    await query.answer()

    # Извлекаем выбранный тип из callback_data
    selected_type = query.data.replace("wl_type_", "")
    logger.debug(f"Выбран тип WL: {selected_type}")

    # Проверяем наличие данных add_data
    if 'add_data' not in context.user_data:
        logger.error(
            "Ошибка: не найдены данные 'add_data' в контексте пользователя")
        await query.edit_message_text(
            "❌ Произошла ошибка: данные о добавлении не найдены. Пожалуйста, начните процесс добавления заново.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "◀️ Назад к добавлению",
                    callback_data="admin_add")
            ]])
        )
        return ConversationHandler.END

    # Проверяем, что тип в списке допустимых
    if selected_type not in WL_TYPES:
        logger.error(
            f"Ошибка: выбранный тип '{selected_type}' отсутствует в списке допустимых типов")
        await query.edit_message_text(
            "❌ Произошла ошибка при выборе типа. Попробуйте снова.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "◀️ Назад к добавлению",
                    callback_data="admin_add")
            ]])
        )
        return ConversationHandler.END

    # Сохраняем тип вайтлиста
    context.user_data['add_data']['wl_type'] = selected_type
    logger.debug(
        f"Обновлены данные add_data: {
            context.user_data['add_data']}")

    # Создаем клавиатуру для выбора причины
    keyboard = []
    for reason in WL_REASONS:
        keyboard.append([InlineKeyboardButton(
            reason, callback_data=f"wl_reason_{reason}")])
    keyboard.append([InlineKeyboardButton(
        "◀️ Отмена", callback_data="menu_admin")])
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

    logger.debug(
        f"Переход в состояние AWAITING_WL_REASON ({AWAITING_WL_REASON})")
    return AWAITING_WL_REASON


async def handle_wl_reason(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process whitelist reason selection"""
    query = update.callback_query
    await query.answer()

    # Get the selected reason
    selected_reason = query.data.replace("wl_reason_", "")

    # Only process if in the right state
    if 'add_data' not in context.user_data:
        logger.warning(
            f"handle_wl_reason вызван без add_data в context.user_data")
        return ConversationHandler.END

    # Save the selected reason
    context.user_data['add_data']['reason'] = selected_reason

    # Get data from context
    add_data = context.user_data.get('add_data', {})
    value = add_data.get('value', 'Не указано')
    wl_type = add_data.get('wl_type', 'FCFS')

    logger.debug(
        f"Данные для добавления в базу: value='{value}', type='{wl_type}', reason='{selected_reason}'")

    try:
        # Добавляем запись в вайтлист
        success = db.add_to_whitelist(value, wl_type, selected_reason)

        # Log event
        db.log_event("add_whitelist", update.effective_user.id, {
            "value": value,
            "wl_type": wl_type,
            "wl_reason": selected_reason
        }, success)

        # Create response message
        if success:
            logger.debug(
                f"Значение '{value}' успешно добавлено в базу данных")
            message_text = (
                f"✅ Запись успешно добавлена в вайтлист!\n\n"
                f"*Значение:* `{value}`\n"
                f"*Тип WL:* {wl_type}\n"
                f"*Причина:* {selected_reason}"
            )
        else:
            logger.debug(
                f"Значение '{value}' уже существует в базе данных")
            message_text = f"⚠️ Значение \"{value}\" уже существует в вайтлисте."

        # Buttons for next action
        keyboard = [
            [InlineKeyboardButton(
                "➕ Добавить еще", callback_data="admin_add")],
            [InlineKeyboardButton("◀️ Назад к админ-панели",
                                  callback_data="menu_admin")],
            [InlineKeyboardButton(
                "🏠 Главное меню", callback_data="back_to_main")]
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
        logger.debug(
            "Данные add_data очищены из контекста пользователя")

        return ConversationHandler.END

    except Exception as e:
        logger.error(
            f"Ошибка при добавлении значения в базу данных: {e}")
        message_text = f"❌ Произошла ошибка при добавлении значения \"{value}\" в базу данных."

        keyboard = [
            [InlineKeyboardButton("↩️ Попробовать снова",
                                  callback_data="admin_add")],
            [InlineKeyboardButton("◀️ Назад к админ-панели",
                                  callback_data="menu_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            message_text,
            reply_markup=reply_markup
        )

        # Очищаем данные о добавлении
        if 'add_data' in context.user_data:
            del context.user_data['add_data']
        logger.debug(
            "Данные add_data очищены из контекста пользователя после ошибки")

        return ConversationHandler.END


async def show_remove_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show menu for removing a value from whitelist"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
            return ConversationHandler.END

        keyboard = [[InlineKeyboardButton(
            "◀️ Назад", callback_data="menu_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.edit_message_text(
                "Введите значение для удаления из вайтлиста:",
                reply_markup=reply_markup
            )

        # Устанавливаем флаг, чтобы знать, что следующее сообщение - для удаления
        # из вайтлиста
        context.user_data['expecting_remove'] = True

        return AWAITING_REMOVE_VALUE


async def handle_remove_value(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process removing a value from whitelist"""
    value = update.message.text.strip()

    # Remove from whitelist
    success = db.remove_from_whitelist(value)

    # Log event
    db.log_event(
        "remove_whitelist", update.effective_user.id, {
            "value": value}, success)

    # Create response message
    if success:
        message_text = f"✅ Значение \"{value}\" успешно удалено из вайтлиста!"
    else:
        message_text = f"❌ Значение \"{value}\" не найдено в вайтлисте."

    # Buttons for next action
    keyboard = [
        [InlineKeyboardButton(
            "➖ Удалить еще", callback_data="admin_remove")],
        [InlineKeyboardButton("◀️ Назад к админ-панели",
                              callback_data="menu_admin")],
        [InlineKeyboardButton(
            "🏠 Главное меню", callback_data="back_to_main")]
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


async def show_list_menu(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all values in whitelist with pagination"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        if update.callback_query:
            await update.callback_query.answer("У вас нет прав доступа к этому разделу.")
            return
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
        # Меньше записей на странице, так как каждая запись теперь содержит
        # больше информации
        items_per_page = 5
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
            f"Страница {page + 1} из {total_pages}\n\n"
        )

        # Add values with numbering in a clean format
        for i, item in enumerate(items[start:end], start=start + 1):
            message_text += (
                f"{i}. `{item['value']}`\n"
                f"   Тип: {
                    item['wl_type']}, Причина: {
                    item['wl_reason']}\n\n"
            )

        # Navigation buttons
        keyboard = []
        nav_row = []

        if total_pages > 1:
            if page > 0:
                nav_row.append(
                    InlineKeyboardButton(
                        "◀️", callback_data="whitelist_prev"))

            nav_row.append(InlineKeyboardButton(
                f"{page + 1}/{total_pages}", callback_data="whitelist_info"))

            if page < total_pages - 1:
                nav_row.append(
                    InlineKeyboardButton(
                        "▶️", callback_data="whitelist_next"))

        keyboard.append(nav_row)
    else:
        message_text = "*📋 База данных*\n\nБаза данных пуста."

        # Back buttons
        keyboard = [
            [InlineKeyboardButton(
                "◀️ Назад к админ-панели", callback_data="menu_admin")],
            [InlineKeyboardButton(
                "🏠 Главное меню", callback_data="back_to_main")]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update_or_send_message(
        update,
        context,
        message_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_whitelist_pagination(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def broadcast_command(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the broadcast conversation"""
    user = update.effective_user
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для использования этой команды.")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(
        "❌ Отмена", callback_data="broadcast_cancel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Use update_or_send_message instead of creating a new message
    await update_or_send_message(
        update,
        context,
        "Введите сообщение для отправки всем пользователям:",
        reply_markup=reply_markup
    )

    return BROADCAST_MESSAGE


async def broadcast_message(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the message to broadcast"""
    message_text = update.message.text

    if not message_text:
        await update_or_send_message(
            update,
            context,
            "Пожалуйста, отправьте текстовое сообщение.",
            InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "❌ Отмена", callback_data="broadcast_cancel")
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
                InlineKeyboardButton(
                    "◀️ Назад", callback_data="menu_admin")
            ]])
        )
        return ConversationHandler.END

    # Log broadcast event
    db.log_event("broadcast", update.effective_user.id,
                 {"message_length": len(message_text)})

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
            if (i % progress_interval == 0 or i == len(users) -
                1) and time.time() - last_progress_update > 2:
                progress_percent = int((i + 1) / len(users) * 100)
                await update_or_send_message(
                    update,
                    context,
                    f"Рассылка: {progress_percent}% ({i + 1}/{len(users)})\n"
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
        [InlineKeyboardButton("◀️ Назад к админ-панели",
                              callback_data="menu_admin")],
        [InlineKeyboardButton(
            "🏠 Главное меню", callback_data="back_to_main")]
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


async def cancel_broadcast(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the broadcast conversation"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "❌ Рассылка отменена.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "◀️ Назад к админ-панели",
                callback_data="menu_admin")
        ]])
    )

    return ConversationHandler.END


async def show_broadcast_menu(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
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
            [InlineKeyboardButton("✉️ Начать рассылку",
                                  callback_data="start_broadcast")],
            [InlineKeyboardButton("◀️ Назад к админ-панели",
                                  callback_data="menu_admin")]
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


async def start_broadcast_from_button(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
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
            InlineKeyboardButton(
                "❌ Отменить", callback_data="broadcast_cancel")
        ]])
    )

    # Set context variable to expect broadcast message
    context.user_data['expecting_broadcast'] = True


async def start_broadcast_process(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
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
                InlineKeyboardButton(
                    "◀️ Назад к админ-панели",
                    callback_data="menu_admin")
            ]])
        )
        return

    # Get users for broadcasting
    users = db.get_all_users()

    if not users:
        await update.message.reply_text(
            "В базе нет пользователей для рассылки.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "◀️ Назад к админ-панели",
                    callback_data="menu_admin")
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
            if (i + 1) % 10 == 0 or i + 1 == len(users):
                await status_message.edit_text(
                    f"🔄 Рассылка: {i + 1}/{len(users)} пользователей...\n"
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
            InlineKeyboardButton(
                "◀️ Назад к админ-панели",
                callback_data="menu_admin")
        ]])
    )

    # Log broadcast event
    db.log_event("broadcast", user.id, {
        "total": len(users),
        "success": success_count,
        "fail": fail_count
    })


async def show_persistent_keyboard(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show a minimal persistent keyboard at the bottom of the chat"""
    user = update.effective_user

    # Create keyboard buttons - simplified for cleaner UI
    keyboard = []

    # Base navigation for all users including Links/FAQ
    keyboard.append(["🔍 Проверить", "📚 Ссылки/FAQ", "🏠 Меню"])

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

    # Set the keyboard without sending a message or with a minimal message
    # Determine the appropriate chat_id
    chat_id = None
    if update.message:
        chat_id = update.message.chat_id
    elif update.callback_query and update.callback_query.message:
        chat_id = update.callback_query.message.chat_id
    elif update.effective_chat:
        chat_id = update.effective_chat.id

    if chat_id:
        # Don't send a message, just update the keyboard
        await context.bot.send_message(
            chat_id=chat_id,
            text="⌨️ Клавиатура активирована",
            reply_markup=reply_markup
        )

    # Add function to delete user message and update or send
    # message


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


    async def save_active_message(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            message) -> None:
        """Save the active message ID for a user to enable in-place updates"""
        context.user_data[ACTIVE_MESSAGE_KEY] = (
            message.chat_id, message.message_id)

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
                logger.debug(
                    f"Could not edit active message {active_message_id}: {e}")

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


    async def clean_old_bot_messages(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE) -> None:
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


    async def handle_message(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for all messages"""
        # Update user's last activity timestamp
        db.update_user_activity(update.effective_user.id)
        
        text = update.message.text.strip()
        
        # Добавляем логирование для диагностики
        user_id = update.effective_user.id
        logger.debug(f"Получено сообщение от пользователя {user_id}: '{text}'")

        # Handle messages based on expected input
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
        elif context.user_data.get('expecting_contribute'):
            logger.debug(f"Обработка сообщения для вклада: '{text}'")
            context.user_data['expecting_contribute'] = False
            await handle_contribute_value(update, context)
            return  # Добавлен явный return, чтобы избежать проверки whitelist
        elif 'conversation_state' in context.user_data:
            state = context.user_data['conversation_state']
            if state == AWAITING_CONTRIBUTE_LINK:
                await handle_contribution_link(update, context)
                return
            elif state == AWAITING_CONTRIBUTE_DESCRIPTION:
                await handle_contribution_description(update, context)
                # Clear the state after handling
                del context.user_data['conversation_state']
                return
        
        # Normal message handling - check whitelist
        # Treat any text as a check query for simplicity
        logger.debug(f"Обработка обычного сообщения как проверки в базе данных: '{text}'")
        
        try:
            # Check the value against whitelist
            value = text
            result = db.check_whitelist(value)
            user = update.effective_user
            
            # Create beautiful response
            if result.get("found", False):
                message_text = (
                    f"*✅ Результат проверки*\n\n"
                    f"Привет, {user.first_name}! 👋\n\n"
                    f"Значение `{value}` *найдено* в базе данных!\n\n"
                    f"У вас {result.get('wl_type', 'Не указан')} WL потому что вы {result.get('wl_reason', 'Не указана')}! 🎉"
                )
            else:
                message_text = (
                    f"*❌ Результат проверки*\n\n"
                    f"Нам жаль, {user.first_name}, но введенного значения пока нет в BuddyWL.\n\n"
                    f"Мы с нетерпением ждем твой вклад и надеемся скоро увидеть тебя уже вместе с твоим Buddy! 💫"
                )
            
            # Buttons for next action
            keyboard = [
                [InlineKeyboardButton("🔄 Проверить другое значение", callback_data="action_check")],
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
            
        except Exception as e:
            logger.error(f"Ошибка при проверке значения в базе данных: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при проверке. Пожалуйста, попробуйте еще раз или обратитесь к администратору.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")
                ]])
            )
        
        # Очищаем активное сообщение
        if BOT_ACTIVE_MESSAGE_KEY in context.chat_data:
            del context.chat_data[BOT_ACTIVE_MESSAGE_KEY]


    async def button_callback(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        callback_data = query.data

        logger.debug(f"Callback query received: {callback_data}")

        # Update user's last activity
        db.update_user_activity(update.effective_user.id)

        # Log the button click
        db.log_event("button_click", update.effective_user.id, {"button": callback_data})

        # Main menu and navigation
        if callback_data == "back_to_main":
            await show_main_menu(update, context)
        elif callback_data == "action_check":
            logger.debug(f"User {update.effective_user.id} pressed Check button")
            await show_check_menu(update, context)
        elif callback_data == "action_stats":
            logger.debug(f"User {update.effective_user.id} pressed Stats button")
            await show_stats_menu(update, context)
        elif callback_data == "action_links":
            logger.debug(f"User {update.effective_user.id} pressed Links button")
            await show_links_menu(update, context)
        elif callback_data == "action_admin":
            logger.debug(f"User {update.effective_user.id} pressed Admin button")
            await show_admin_menu(update, context)
        # Admin functions
        elif callback_data == "menu_admin":
            await show_admin_menu(update, context)
        elif callback_data == "admin_add":
            # Явно устанавливаем флаг ожидания добавления значения
            context.user_data['expecting_add'] = True
            await show_add_menu(update, context)
        elif callback_data == "admin_remove":
            # Явно устанавливаем флаг ожидания удаления значения
            context.user_data['expecting_remove'] = True
            await show_remove_menu(update, context)
        elif callback_data == "admin_list":
            await show_list_menu(update, context)
        elif callback_data == "admin_broadcast":
            await show_broadcast_menu(update, context)
        elif callback_data == "admin_export":
            await handle_export_button(update, context)
        elif callback_data == "admin_import":
            await show_import_menu(update, context)
        # Whitelist pagination
        elif callback_data == "prev_page":
            await handle_whitelist_pagination(update, context, -1)
        elif callback_data == "next_page":
            await handle_whitelist_pagination(update, context, 1)
        # Remove from whitelist with confirmation
        elif callback_data.startswith("remove_"):
            # Extract the value to remove
            value_to_remove = callback_data[7:]  # Remove "remove_" prefix
            success = db.remove_from_whitelist(value_to_remove)

            # Create response message with buttons
            if success:
                message_text = f"Значение '{value_to_remove}' успешно удалено из вайтлиста."
            else:
                message_text = f"Не удалось удалить значение '{value_to_remove}' из вайтлиста."

            # Add a button to go back to admin menu
            keyboard = [[InlineKeyboardButton(
                "◀️ Назад к админ-панели", callback_data="menu_admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Use delete_and_update_message instead of direct edit
            await query.edit_message_text(
                message_text,
                reply_markup=reply_markup
            )
        # Import modes
        elif callback_data == "import_replace":
            await process_import(update, context, "replace")
        elif callback_data == "import_append":
            await process_import(update, context, "append")
        # Broadcast
        elif callback_data == "start_broadcast":
            await start_broadcast_from_button(update, context)
        elif callback_data == "broadcast_cancel":
            await cancel_broadcast(update, context)
        # Whitelist type and reason handling
        elif callback_data.startswith("wl_type_"):
            # Handle whitelist type selection for adding new values
            await handle_wl_type(update, context)
        elif callback_data.startswith("wl_reason_"):
            # Handle whitelist reason selection for adding new values
            await handle_wl_reason(update, context)
        # Contribution functions
        elif callback_data == "action_contribute":
            logger.debug(f"User {update.effective_user.id} pressed Contribute button")
            await show_contribute_menu(update, context)
        elif callback_data == "view_contribute":
            logger.debug(f"User {update.effective_user.id} viewing contributions")
            await show_contributions_menu(update, context)
        elif callback_data == "add_contribution":
            logger.debug(f"User {update.effective_user.id} adding a new contribution")
            result = await start_add_contribution(update, context)
            # If result is a state, register it correctly
            if isinstance(result, int):
                context.user_data['conversation_state'] = result
        else:
            logger.warning(f"Unhandled callback data: {callback_data}")
            await query.answer("Эта функция находится в разработке.")


    async def show_links_menu(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show links and FAQ information"""
        keyboard = [[InlineKeyboardButton(
            "🏠 Вернуться в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message_text = (
            "*📚 Полезные ссылки и FAQ*\n\n"
            "🔗 *Официальные ресурсы проекта Buddies:*\n"
            "• [Официальный сайт](https://megabuddies.io)\n"
            "• [Twitter/X](https://twitter.com/MegaBuddiesNFT)\n"
            "• [Discord](https://discord.gg/megabuddies)\n\n"
            "❓ *Часто задаваемые вопросы:*\n"
            "• *Как попасть в вайтлист?*\n"
            "  Следите за анонсами в официальных каналах\n\n"
            "• *Как проверить статус в вайтлисте?*\n"
            "  Используйте кнопку «Проверить» в главном меню\n\n"
            "• *Где узнать о новых анонсах?*\n"
            "  В Discord и Twitter/X проекта"
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )


    async def menu_command(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for the /menu command"""
        await show_main_menu(update, context)
        # Show keyboard after menu command
        await show_persistent_keyboard(update, context)


    async def setup_commands(application: Application) -> None:
        """Set up bot commands and description"""
        bot = application.bot

        # Commands for all users
        commands = [
            BotCommand("start", "Запустить бота и показать главное меню"),
            BotCommand("menu", "Показать главное меню"),
            BotCommand("help", "Показать справку по командам"),
            BotCommand("check", "Проверить значение в вайтлисте"),
            BotCommand("contribute", "Внести свой вклад с полезными ссылками")
        ]

        # Try to set commands for all users
        try:
            await bot.set_my_commands(commands)
        except Exception as e:
            logger.error(f"Error setting up commands: {e}")

        # Additional commands for admins
        admin_commands = commands + [
            BotCommand("admin", "Админ-панель для управления ботом"),
            BotCommand("list", "Показать все записи в вайтлисте"),
            BotCommand("add", "Добавить новое значение в вайтлист"),
            BotCommand("remove", "Удалить значение из вайтлиста"),
            BotCommand("broadcast", "Отправить сообщение всем пользователям"),
            BotCommand("stats", "Статистика использования бота"),
            BotCommand("export", "Экспортировать базу данных в CSV"),
            BotCommand("import", "Импортировать данные в базу из CSV файла")
        ]

        # Try to set admin commands for each admin
        for admin_id in ADMIN_IDS:
            try:
                scope = BotCommandScopeChat(chat_id=admin_id)
                await bot.set_my_commands(admin_commands, scope=scope)
            except Exception as e:
                logger.error(f"Error setting up admin commands for user {admin_id}: {e}")

        # Set bot description
        await bot.set_my_description(
            "MegaBuddies бот для проверки и управления вайтлистом. "
            "Позволяет проверить статус вашего адреса в базе данных, "
            "а администраторам - управлять записями в вайтлисте."
        )

        # Set short description for bot startup screen
        await bot.set_my_short_description(
            "Бот для проверки и управления вайтлистом MegaBuddies"
        )

        logger.info(
            "Bot commands and descriptions set up successfully")


    async def handle_export_button(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle export button click"""
        user = update.effective_user

        # Only admins can export data
        if user.id not in ADMIN_IDS:
            await update.callback_query.answer("У вас нет прав для экспорта данных.")
            return

        # Change button message to show progress
        await update.callback_query.edit_message_text(
            "🔄 Подготовка экспорта данных...\n\n"
            "Пожалуйста, подождите. Файл будет отправлен в ближайшие секунды."
        )

        try:
            # Export data to CSV
            success, filename = db.export_whitelist_to_csv()

            if success:
                # Send the generated file to the user
                with open(filename, 'rb') as file:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=file,
                        filename=filename,
                        caption="📊 Экспорт базы данных вайтлиста"
                    )

                # Log the export event
                db.log_event(
                    "export_data", user.id, {
                        "format": "csv", "filename": filename}, True)

                # Return to admin menu
                await show_admin_menu(update, context)
            else:
                # Show error and go back to admin menu
                keyboard = [[InlineKeyboardButton(
                    "◀️ Назад к админ-панели", callback_data="menu_admin")]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.callback_query.edit_message_text(
                    "❌ Не удалось экспортировать данные. Возможно, база данных пуста.",
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Error exporting data: {e}")

            # Show error and go back to admin menu
            keyboard = [[InlineKeyboardButton(
                "◀️ Назад к админ-панели", callback_data="menu_admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                f"❌ Ошибка при экспорте данных: {str(e)}",
                reply_markup=reply_markup
            )


    async def export_command(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for the /export command - exports whitelist to CSV"""
        user = update.effective_user

        # Only admins can export data
        if user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔ У вас нет прав для экспорта данных.")
            return

        # Send a message that export is in progress
        progress_message = await update.message.reply_text(
            "🔄 Подготовка экспорта данных...",
            reply_markup=None
        )

        try:
            # Export data to CSV
            success, filename = db.export_whitelist_to_csv()

            if success:
                # Send the generated file to the user
                await progress_message.edit_text("✅ Данные успешно экспортированы! Отправляю файл...")

                with open(filename, 'rb') as file:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
                        document=file,
                        filename=filename,
                        caption="📊 Экспорт базы данных вайтлиста"
                    )

                # Log the export event
                db.log_event(
                    "export_data", user.id, {
                        "format": "csv", "filename": filename}, True)

                # Clean up the progress message
                await progress_message.delete()
            else:
                await progress_message.edit_text("❌ Не удалось экспортировать данные. Возможно, база данных пуста.")
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            await progress_message.edit_text(f"❌ Ошибка при экспорте данных: {str(e)}")


    async def import_command(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for the /import command - starts the import process"""
        user = update.effective_user

        # Only admins can import data
        if user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔ У вас нет прав для импорта данных.")
            return

        # Show import instructions
        message_text = (
            "*📥 Импорт данных в базу*\n\n"
            "Отправьте CSV-файл с данными для импорта.\n\n"
            "Формат файла:\n"
            "• CSV с разделителями-запятыми\n"
            "• Можно с заголовками или без\n"
            "• Столбцы: value, wl_type, wl_reason\n"
            "• Минимально необходим только столбец value\n\n"
            "После загрузки файла вы сможете выбрать режим импорта:\n"
            "• *Добавление* - добавит новые записи к существующим\n"
            "• *Замена* - удалит все существующие записи и загрузит новые"
        )

        # Set the expected file flag
        context.user_data['expecting_import_file'] = True

        # Send import instructions
        await update.message.reply_text(
            message_text,
            parse_mode='Markdown'
        )


    async def handle_import_file(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle CSV file upload for import"""
        user = update.effective_user

        # Only admins can import data
        if user.id not in ADMIN_IDS:
            return

        # Check if we're expecting an import file
        if not context.user_data.get('expecting_import_file', False):
            return

        # Reset the flag
        context.user_data['expecting_import_file'] = False

        # Process the file
        if update.message.document:
            file = update.message.document

            # Check if it's a CSV file
            file_name = file.file_name
            if not file_name.lower().endswith('.csv'):
                await update.message.reply_text(
                    "❌ Пожалуйста, загрузите файл в формате CSV. "
                    "Файл должен иметь расширение .csv",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "↩️ Попробовать снова",
                            callback_data="admin_import")
                    ]])
                )
                return

            # Show processing message
            progress_message = await update.message.reply_text(
                "⏳ Загрузка и обработка файла...",
                reply_markup=None
            )

            try:
                # Download the file
                file_info = await context.bot.get_file(file.file_id)
                downloaded_file = await file_info.download_as_bytearray()

                # Save to temporary file
                import tempfile
                import os

                temp_dir = tempfile.gettempdir()
                temp_file_path = os.path.join(temp_dir, file_name)

                with open(temp_file_path, 'wb') as f:
                    f.write(downloaded_file)

                # Store file path in context for later processing
                context.user_data['import_file_path'] = temp_file_path

                # Show import options
                await progress_message.edit_text(
                    f"✅ Файл {file_name} успешно загружен.\n\n"
                    "Выберите режим импорта:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            "📝 Добавить к существующим", callback_data="import_append")],
                        [InlineKeyboardButton(
                            "🔄 Заменить все данные", callback_data="import_replace")],
                        [InlineKeyboardButton(
                            "❌ Отменить импорт", callback_data="import_cancel")]
                    ])
                )

                # Log event
                db.log_event(
                    "import_file_upload", user.id, {
                        "filename": file_name}, True)

            except Exception as e:
                logger.error(f"Error processing import file: {e}")
                await progress_message.edit_text(
                    f"❌ Ошибка при обработке файла: {str(e)}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "↩️ Попробовать снова",
                            callback_data="admin_import")
                    ]])
                )
            else:
                await update.message.reply_text(
                    "❌ Пожалуйста, отправьте файл в формате CSV.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "↩️ Попробовать снова",
                            callback_data="admin_import")
                    ]])
                )


    async def process_import(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE,
            mode: str) -> None:
        """Process the import with the selected mode"""
        # Get the file path from context
        file_path = context.user_data.get('import_file_path')
        if not file_path:
            await update.callback_query.edit_message_text(
                "❌ Ошибка: файл для импорта не найден. Пожалуйста, загрузите файл снова.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "↩️ Попробовать снова",
                        callback_data="admin_import")
                ]])
            )
            return

        # Update message to show progress
        await update.callback_query.edit_message_text(
            f"⏳ Импорт данных в режиме {mode}...\n\n"
            "Этот процесс может занять некоторое время для больших файлов."
        )

        try:
            # Import the data
            import_mode = "replace" if mode == "replace" else "append"
            success, stats = db.import_whitelist_from_csv(
                file_path, import_mode)

            if success:
                # Format result message
                mode_text = "замены" if mode == "replace" else "добавления"
                message_text = (
                    f"✅ Импорт в режиме {mode_text} завершен успешно!\n\n"
                    f"📊 *Статистика импорта:*\n"
                    f"• Обработано строк: {stats.get('processed', 0)}\n"
                    f"• Добавлено записей: {stats.get('added', 0)}\n"
                    f"• Пропущено (дубликаты): {stats.get('skipped', 0)}\n"
                    f"• Некорректных строк: {stats.get('invalid', 0)}\n\n"
                    f"Всего записей в базе: {db.get_whitelist_count()}"
                )

                # Log event
                db.log_event("import_complete", update.effective_user.id, {
                    "mode": import_mode,
                    "stats": stats
                }, True)

                # Clean up the temporary file
                import os
                try:
                    os.remove(file_path)
                    logger.debug(f"Temporary file {file_path} deleted")
                except Exception as e:
                    logger.warning(
                        f"Could not delete temporary file {file_path}: {e}")

                # Clear the stored file path
                if 'import_file_path' in context.user_data:
                    del context.user_data['import_file_path']

                # Add buttons for next steps
                keyboard = [
                    [InlineKeyboardButton(
                        "📋 Просмотреть базу данных", callback_data="admin_list")],
                    [InlineKeyboardButton(
                        "📥 Импортировать еще", callback_data="admin_import")],
                    [InlineKeyboardButton(
                        "◀️ Назад к админ-панели", callback_data="menu_admin")]
                ]

                # Send result message
                await update.callback_query.edit_message_text(
                    message_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                error_message = stats.get("error", "Неизвестная ошибка")
                await update.callback_query.edit_message_text(
                    f"❌ Ошибка при импорте данных: {error_message}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton(
                            "↩️ Попробовать снова",
                            callback_data="admin_import")
                    ]])
                )
        except Exception as e:
            logger.error(f"Error during import process: {e}")
            await update.callback_query.edit_message_text(
                f"❌ Ошибка при импорте данных: {str(e)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "↩️ Попробовать снова",
                        callback_data="admin_import")
                ]])
            )


    async def show_import_menu(
            update: Update,
            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show the import menu with instructions"""
        user = update.effective_user

        # Only admins can import data
        if user.id not in ADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("У вас нет прав для импорта данных.")
            else:
                await update.message.reply_text("⛔ У вас нет прав для импорта данных.")
            return

        # Set the expected file flag
        context.user_data['expecting_import_file'] = True

        message_text = (
            "*📥 Импорт данных в базу*\n\n"
            "Отправьте CSV-файл с данными для импорта.\n\n"
            "Формат файла:\n"
            "• CSV с разделителями-запятыми\n"
            "• Можно с заголовками или без\n"
            "• Столбцы: value, wl_type, wl_reason\n"
            "• Минимально необходим только столбец value\n\n"
            "После загрузки файла вы сможете выбрать режим импорта:\n"
            "• *Добавление* - добавит новые записи к существующим\n"
            "• *Замена* - удалит все существующие записи и загрузит новые"
        )

        # Add cancel button
        keyboard = [[InlineKeyboardButton(
            "◀️ Назад к админ-панели", callback_data="menu_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Show message
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


    async def error_handler(
            update: object,
            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle errors in the telegram bot"""
        try:
            if update and isinstance(
                    update, Update) and update.effective_message:
                # Only send error to chat if it's a known error for user input
                if isinstance(
                        context.error,
                        (ValueError,
                         KeyError,
                         IndexError)):
                    await update.effective_message.reply_text(
                        "⚠️ Произошла ошибка при обработке вашего запроса. "
                        "Пожалуйста, проверьте ввод и попробуйте снова.",
                        disable_web_page_preview=True
                    )
                else:
                    # For any other errors, send generic message to user
                    await update.effective_message.reply_text(
                        "🛑 Произошла внутренняя ошибка. Администраторы уведомлены. "
                        "Пожалуйста, попробуйте позже или обратитесь к администратору.",
                        disable_web_page_preview=True
                    )

                # Try to restore the conversation state if needed
                if context.user_data.get('expecting_add') or
                context.user_data.get('expecting_remove') or
                context.user_data.get('expecting_check') or
                context.user_data.get('expecting_broadcast') or
                context.user_data.get('expecting_import_file'):

                    # Reset all conversation flags
                    context.user_data['expecting_add'] = False
                    context.user_data['expecting_remove'] = False
                    context.user_data['expecting_check'] = False
                    context.user_data['expecting_broadcast'] = False
                    context.user_data['expecting_import_file'] = False

                    # Clean up any temporary files
                    if 'import_file_path' in context.user_data:
                        import os
                        try:
                            os.remove(context.user_data['import_file_path'])
                        except BaseException:
                            pass
                        del context.user_data['import_file_path']

                    logger.warning("Reset conversation state due to error")

                # Log the error
                logger.error(
                    f"Update {update} caused error {
                        context.error}",
                    exc_info=context.error)

                # Notify admins about critical errors
                if isinstance(context.error, Exception) and not isinstance(
                        context.error, (ValueError, KeyError, IndexError)):
                    for admin_id in ADMIN_IDS:
                        try:
                            error_message = (
                                f"🔴 *Критическая ошибка в боте:*\n\n"
                                f"```\n{str(context.error)[:200]}...\n```"
                            )

                            await context.bot.send_message(
                                chat_id=admin_id,
                                text=error_message,
                                parse_mode='Markdown'
                            )
                        except BaseException:
                            logger.error(
                                f"Failed to notify admin {admin_id} about error")
                        except Exception as e:
                            # If even the error handler fails, just log it
                            logger.critical(f"Error handler failed with {e}", exc_info=e)


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

        # Set higher persistence and stability options
        # Не используем параметр disable_web_page_preview в Defaults
        defaults = Defaults(
            parse_mode='Markdown',
            allow_sending_without_reply=True,
            tzinfo=datetime.timezone.utc
        )
        
        # Create the Application with persistence
        persistence = PicklePersistence(filepath="bot_data")
        
        # Создаем приложение без использования rate_limiter с проблемными параметрами
        application = (
            Application.builder()
            .token(token)
            .defaults(defaults)
            .persistence(persistence)
            .build()
        )
        
        # Setup bot commands and description on startup
        application.post_init = setup_commands
        
        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("menu", menu_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("broadcast", broadcast_command))
        application.add_handler(CommandHandler("admin", show_admin_menu))
        application.add_handler(CommandHandler("export", export_command))
        application.add_handler(CommandHandler("import", import_command))
        application.add_handler(CommandHandler("check", show_check_menu))
        application.add_handler(CommandHandler("contribute", show_contribute_menu))
        
        # Add conversation handlers
        
        # Add conversation handler for contributions
        contribution_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("contribute", show_contribute_menu),
                CallbackQueryHandler(start_add_contribution, pattern="^add_contribution$")
            ],
            states={
                AWAITING_CONTRIBUTE_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contribution_link)],
                AWAITING_CONTRIBUTE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contribution_description)]
            },
            fallbacks=[CallbackQueryHandler(show_contributions_menu, pattern="^view_contribute$")],
            name="contribution_conversation",
            persistent=True
        )
        application.add_handler(contribution_conv_handler)
        
        # Add conversation handler for check
        check_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("check", show_check_menu),
                CallbackQueryHandler(show_check_menu, pattern="^action_check$")
            ],
            states={
                AWAITING_CHECK_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_check_value)]
            },
            fallbacks=[CallbackQueryHandler(button_callback)],
            name="check_conversation",
            persistent=False,
            per_chat=True
        )
        application.add_handler(check_conv_handler)
        
        # Add conversation handler for adding values
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
            fallbacks=[CallbackQueryHandler(button_callback)],
            name="add_conversation",
            persistent=False,
            per_chat=True
        )
        application.add_handler(add_conv_handler)
        
        # Add conversation handler for removing values
        remove_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("remove", show_remove_menu),
                CallbackQueryHandler(show_remove_menu, pattern="^admin_remove$")
            ],
            states={
                AWAITING_REMOVE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_remove_value)]
            },
            fallbacks=[CallbackQueryHandler(button_callback)],
            name="remove_conversation",
            persistent=False,
            per_chat=True
        )
        application.add_handler(remove_conv_handler)
        
        # Add conversation handler for broadcasting messages
        broadcast_conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("broadcast", broadcast_command),
                CallbackQueryHandler(show_broadcast_menu, pattern="^admin_broadcast$")
            ],
            states={
                BROADCAST_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message)]
            },
            fallbacks=[CallbackQueryHandler(button_callback)],
            name="broadcast_conversation",
            persistent=False,
            per_chat=True
        )
        application.add_handler(broadcast_conv_handler)
        
        # Add handler for document uploads (for import)
        application.add_handler(MessageHandler(filters.Document.ALL, handle_import_file))
        
        # Add callback query handler - перемещено после ConversationHandler, но перед MessageHandler
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Add message handler to catch all unhandled messages
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Start the Bot
        logger.info("Starting the bot...")
        application.run_polling()


    if __name__ == "__main__":
        main()
