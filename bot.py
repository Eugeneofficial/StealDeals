# -*- coding: utf-8 -*-
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
from config import TELEGRAM_TOKEN, GAME_GENRES
from database import get_session, User, Genre, Game
from parsers import SteamParser, EpicParser, GogParser
import asyncio
import schedule
import time
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
SELECTING_GENRES, SELECTING_NOTIFICATIONS = range(2)

# Инициализация парсеров
steam_parser = SteamParser()
epic_parser = EpicParser()
gog_parser = GogParser()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    session = get_session()
    
    # Проверяем, существует ли пользователь
    db_user = session.query(User).filter_by(telegram_id=user.id).first()
    if not db_user:
        db_user = User(
            telegram_id=user.id,
            username=user.username
        )
        session.add(db_user)
        session.commit()
    
    keyboard = [
        [InlineKeyboardButton("🎮 Выбрать жанры", callback_data='select_genres')],
        [InlineKeyboardButton("🔔 Настройки уведомлений", callback_data='notification_settings')],
        [
            InlineKeyboardButton("🎮 Steam", url="https://store.steampowered.com/about/"),
            InlineKeyboardButton("🎮 Epic Games", url="https://store.epicgames.com/download"),
            InlineKeyboardButton("🎮 GOG", url="https://www.gog.com/galaxy")
        ],
        [InlineKeyboardButton("💰 Поддержать разработчика", callback_data='support_dev')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Я бот для поиска скидок и бесплатных игр. Для быстрого доступа:\n"
        "🎮 Steam: https://store.steampowered.com/about/\n"
        "🎮 Epic Games: https://store.epicgames.com/download\n"
        "🎮 GOG Galaxy: https://www.gog.com/galaxy\n\n"
        "Доступные команды:\n"
        "/deals - Показать текущие скидки\n"
        "/free - Показать бесплатные игры\n"
        "/help - Показать справку\n\n"
        "Выберите действие:"
    )
    
    if update.message:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, disable_web_page_preview=True)
    else:
        await update.callback_query.edit_message_text(welcome_message, reply_markup=reply_markup, disable_web_page_preview=True)
    
    return SELECTING_GENRES

async def select_genres(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора жанров"""
    query = update.callback_query
    await query.answer()
    
    session = get_session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    keyboard = []
    for genre_name in GAME_GENRES:
        # Проверяем, выбран ли жанр
        genre = session.query(Genre).filter_by(name=genre_name).first()
        if not genre:
            genre = Genre(name=genre_name)
            session.add(genre)
            session.commit()
        
        is_selected = genre in user.preferred_genres
        keyboard.append([
            InlineKeyboardButton(
                f"{'✅' if is_selected else '❌'} {genre_name}",
                callback_data=f'toggle_genre_{genre.id}'
            )
        ])
    
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data='genres_done')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="Выберите интересующие вас жанры игр:",
        reply_markup=reply_markup
    )
    
    return SELECTING_GENRES

async def genres_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик завершения выбора жанров"""
    query = update.callback_query
    await query.answer()
    
    session = get_session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    selected_genres = [genre.name for genre in user.preferred_genres]
    
    if not selected_genres:
        await query.edit_message_text(
            "⚠️ Вы не выбрали ни одного жанра. Рекомендуем выбрать хотя бы один жанр "
            "для получения более релевантных предложений.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Выбрать жанры", callback_data='select_genres')
            ]])
        )
        return SELECTING_GENRES
    
    await query.edit_message_text(
        f"✅ Отлично! Вы выбрали следующие жанры:\n"
        f"🎯 {', '.join(selected_genres)}\n\n"
        f"Теперь вы будете получать уведомления о скидках и бесплатных играх в этих жанрах.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data='back_to_main')
        ]])
    )
    
    return SELECTING_GENRES

async def toggle_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик переключения жанра"""
    query = update.callback_query
    await query.answer()
    
    genre_id = int(query.data.split('_')[-1])
    session = get_session()
    
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    genre = session.query(Genre).filter_by(id=genre_id).first()
    
    if genre in user.preferred_genres:
        user.preferred_genres.remove(genre)
    else:
        user.preferred_genres.append(genre)
    
    session.commit()
    
    # Обновляем клавиатуру
    await select_genres(update, context)

async def notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик настроек уведомлений"""
    query = update.callback_query
    await query.answer()
    
    session = get_session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    keyboard = [
        [
            InlineKeyboardButton(
                "🔔 Скидки " + ("✅" if user.notify_sales else "❌"),
                callback_data='toggle_sales'
            )
        ],
        [
            InlineKeyboardButton(
                "🎮 Бесплатные игры " + ("✅" if user.notify_free else "❌"),
                callback_data='toggle_free'
            )
        ],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Настройки уведомлений:",
        reply_markup=reply_markup
    )
    
    return SELECTING_NOTIFICATIONS

async def toggle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик переключения уведомлений"""
    query = update.callback_query
    await query.answer()
    
    session = get_session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    if query.data == 'toggle_sales':
        user.notify_sales = not user.notify_sales
    elif query.data == 'toggle_free':
        user.notify_free = not user.notify_free
    
    session.commit()
    
    # Обновляем клавиатуру
    await notification_settings(update, context)

async def support_dev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик кнопки поддержки разработчика"""
    query = update.callback_query
    await query.answer()
    
    support_message = (
        "💰 *Поддержать разработчика*\n\n"
        "Если вам нравится бот и вы хотите поддержать его развитие, "
        "вы можете сделать это с помощью Яндекс.Денег:\n\n"
        "`410019367949637`\n\n"
        "По всем вопросам обращайтесь к @EvgenyPivko\n\n"
        "Спасибо за вашу поддержку! 🙏"
    )
    
    keyboard = [
        [InlineKeyboardButton("💳 Яндекс.Деньги", url="https://yoomoney.ru/to/410019367949637")],
        [InlineKeyboardButton("💬 Написать разработчику", url="https://t.me/EvgenyPivko")],
        [InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        support_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return SELECTING_GENRES

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "🎮 *Доступные команды:*\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/settings - Настройки уведомлений\n"
        "/deals - Показать текущие скидки\n"
        "/free - Показать бесплатные игры\n\n"
        "📝 *Как пользоваться:*\n"
        "1. Выберите интересующие вас жанры игр\n"
        "2. Настройте уведомления\n"
        "3. Получайте уведомления о скидках и бесплатных играх\n\n"
        "❓ По всем вопросам обращайтесь к @EvgenyPivko\n\n"
        "💰 Поддержать разработчика: `410019367949637` (Яндекс.Деньги)"
    )
    
    keyboard = [
        [InlineKeyboardButton("💰 Поддержать разработчика", callback_data='support_dev')],
        [InlineKeyboardButton("◀️ Назад", callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)

async def deals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /deals"""
    session = get_session()
    user = session.query(User).filter_by(telegram_id=update.effective_user.id).first()
    
    status_message = await update.message.reply_text(
        "🔍 Поиск скидок...\n"
        "Это может занять несколько секунд."
    )
    
    try:
        # Получаем скидки асинхронно
        tasks = [
            steam_parser.get_deals(user.min_discount),
            epic_parser.get_deals(user.min_discount),
            gog_parser.get_deals(user.min_discount)
        ]
        results = await asyncio.gather(*tasks)
        
        all_deals = []
        for deals in results:
            all_deals.extend(deals)
        
        # Фильтруем по жанрам пользователя
        if user.preferred_genres:
            preferred_genre_names = [genre.name for genre in user.preferred_genres]
            all_deals = [
                deal for deal in all_deals 
                if any(genre in preferred_genre_names for genre in deal.genres)
            ]
        
        # Сортируем по размеру скидки
        all_deals.sort(key=lambda x: x.discount_percent, reverse=True)
        
        await status_message.delete()
        
        if not all_deals:
            await update.message.reply_text(
                "😔 К сожалению, сейчас нет подходящих скидок.\n"
                "Попробуйте изменить настройки жанров или минимальной скидки."
            )
            return
        
        # Отправляем максимум 5 игр с задержкой
        for i, deal in enumerate(all_deals[:5]):
            if i > 0:
                await asyncio.sleep(0.5)  # Задержка между сообщениями
                
            message = (
                f"🎮 *{deal.title}*\n"
                f"💰 Цена: {'Бесплатно!' if deal.is_free else f'~~{deal.original_price}₽~~ *{deal.current_price}₽*'}\n"
                f"📉 Скидка: *{deal.discount_percent}%*\n"
                f"🏪 Платформа: *{deal.platform.upper()}*\n"
                f"🎯 Жанры: {', '.join(deal.genres)}"
            )
            
            # Формируем правильную ссылку для магазина
            store_url = deal.url
            if deal.platform.lower() == 'steam':
                store_url = f"https://store.steampowered.com/app/{deal.store_id}"
            elif deal.platform.lower() == 'epic':
                store_url = f"https://store.epicgames.com/p/{deal.store_id}"
            elif deal.platform.lower() == 'gog':
                store_url = f"https://www.gog.com/game/{deal.store_id}"
            
            keyboard = [
                [InlineKeyboardButton(
                    "🎮 Открыть в магазине" if deal.is_free else "🛒 Купить",
                    url=store_url
                )],
                [InlineKeyboardButton(
                    "📥 Скачать клиент",
                    url=f"https://{'store.steampowered.com/about/' if deal.platform.lower() == 'steam' else 'store.epicgames.com/download' if deal.platform.lower() == 'epic' else 'www.gog.com/galaxy'}"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message, 
                parse_mode='Markdown', 
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
    except Exception as e:
        logger.error(f"Error in deals_command: {e}")
        await status_message.edit_text(
            "😔 Произошла ошибка при поиске скидок.\n"
            "Пожалуйста, попробуйте позже."
        )

async def free_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /free"""
    status_message = await update.message.reply_text(
        "🔍 Поиск бесплатных игр...\n"
        "Это может занять несколько секунд."
    )
    
    try:
        # Получаем бесплатные игры асинхронно
        tasks = [
            steam_parser.get_free_games(),
            epic_parser.get_free_games(),
            gog_parser.get_free_games()
        ]
        results = await asyncio.gather(*tasks)
        
        all_games = []
        for games in results:
            all_games.extend(games)
        
        await status_message.delete()
        
        if not all_games:
            await update.message.reply_text(
                "😔 К сожалению, сейчас нет бесплатных игр.\n"
                "Попробуйте проверить позже."
            )
            return
        
        # Отправляем информацию о каждой игре с задержкой
        for i, game in enumerate(all_games):
            if i > 0:
                await asyncio.sleep(0.5)  # Задержка между сообщениями
                
            message = (
                f"🎮 *{game.title}*\n"
                f"🏪 Платформа: *{game.platform.upper()}*\n"
                f"🎯 Жанры: {', '.join(game.genres)}\n"
                f"💰 Статус: *Бесплатно!*"
            )
            
            # Формируем правильную ссылку для магазина
            store_url = game.url
            if game.platform.lower() == 'steam':
                store_url = f"https://store.steampowered.com/app/{game.store_id}"
            elif game.platform.lower() == 'epic':
                store_url = f"https://store.epicgames.com/p/{game.store_id}"
            elif game.platform.lower() == 'gog':
                store_url = f"https://www.gog.com/game/{game.store_id}"
            
            keyboard = [
                [InlineKeyboardButton("🎮 Получить бесплатно", url=store_url)],
                [InlineKeyboardButton(
                    "📥 Скачать клиент",
                    url=f"https://{'store.steampowered.com/about/' if game.platform.lower() == 'steam' else 'store.epicgames.com/download' if game.platform.lower() == 'epic' else 'www.gog.com/galaxy'}"
                )]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
            
    except Exception as e:
        logger.error(f"Error in free_command: {e}")
        await status_message.edit_text(
            "😔 Произошла ошибка при поиске бесплатных игр.\n"
            "Пожалуйста, попробуйте позже."
        )

def main():
    """Запуск бота"""
    # Настраиваем лимиты для оптимизации
    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .concurrent_updates(True)  # Включаем параллельную обработку обновлений
        .build()
    )
    
    # Добавляем обработчики команд
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECTING_GENRES: [
                CallbackQueryHandler(select_genres, pattern='^select_genres$'),
                CallbackQueryHandler(toggle_genre, pattern='^toggle_genre_'),
                CallbackQueryHandler(genres_done, pattern='^genres_done$'),
                CallbackQueryHandler(notification_settings, pattern='^notification_settings$'),
                CallbackQueryHandler(help_command, pattern='^help$'),
                CallbackQueryHandler(support_dev, pattern='^support_dev$'),
                CallbackQueryHandler(start, pattern='^back_to_main$')
            ],
            SELECTING_NOTIFICATIONS: [
                CallbackQueryHandler(toggle_notification, pattern='^toggle_'),
                CallbackQueryHandler(start, pattern='^back_to_main$')
            ]
        },
        fallbacks=[CommandHandler('start', start)],
        per_message=False
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('deals', deals_command))
    application.add_handler(CommandHandler('free', free_command))
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 