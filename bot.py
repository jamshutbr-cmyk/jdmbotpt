import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from config import BOT_TOKEN
from db_adapter import db
from keyboards import (
    main_menu_kb, admin_menu_kb, car_navigation_kb, catalog_kb,
    confirm_delete_kb, cancel_kb, back_to_main_kb, search_results_kb
)
from states import AddCarStates, SearchStates
from utils import is_admin, format_car_info, format_stats
import admin_handlers

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Подключаем админ-обработчики
dp.include_router(admin_handlers.router)

# Константы
CARS_PER_PAGE = 6


# ============= КОМАНДЫ =============

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start"""
    welcome_text = await db.get_setting('welcome_text')
    if not welcome_text:
        welcome_text = (
            "🚗 <b>Добро пожаловать в JDM Cars Bot!</b>\n\n"
            "Здесь ты найдешь крутые тачки, сфотографированные на улицах города.\n\n"
            "Выбери действие из меню ниже:"
        )
    
    keyboard = main_menu_kb()
    
    if is_admin(message.from_user.id):
        builder = InlineKeyboardBuilder()
        for row in keyboard.inline_keyboard:
            builder.row(*row)
        builder.row(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))
        keyboard = builder.as_markup()
    
    # Проверяем, есть ли фото приветствия
    welcome_photo = await db.get_setting('welcome_photo')
    
    if welcome_photo:
        await message.answer_photo(
            photo=welcome_photo,
            caption=welcome_text,
            reply_markup=keyboard
        )
    else:
        await message.answer(welcome_text, reply_markup=keyboard)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help"""
    help_text = (
        "ℹ️ <b>Помощь по боту</b>\n\n"
        "🚗 <b>Каталог машин</b> - просмотр всех машин\n"
        "🔍 <b>Поиск</b> - найти машину по марке/модели\n"
        "⭐ <b>Избранное</b> - твои любимые машины\n"
        "🎲 <b>Случайная</b> - показать случайную машину\n"
        "📊 <b>Статистика</b> - статистика бота\n\n"
        "Команды:\n"
        "/start - главное меню\n"
        "/help - эта справка"
    )
    await message.answer(help_text, reply_markup=back_to_main_kb())


# ============= ГЛАВНОЕ МЕНЮ =============

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    
    bot_name = await db.get_setting('bot_name') or 'JDM Cars Bot'
    welcome_text = f"🚗 <b>{bot_name}</b>\n\nВыбери действие из меню:"
    
    keyboard = main_menu_kb()
    
    if is_admin(callback.from_user.id):
        builder = InlineKeyboardBuilder()
        for row in keyboard.inline_keyboard:
            builder.row(*row)
        builder.row(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))
        keyboard = builder.as_markup()
    
    try:
        await callback.message.edit_text(welcome_text, reply_markup=keyboard)
    except:
        await callback.message.delete()
        await callback.message.answer(welcome_text, reply_markup=keyboard)
    
    await callback.answer()


@dp.callback_query(F.data == "about")
async def about_bot(callback: CallbackQuery):
    """О боте"""
    bot_name = await db.get_setting('bot_name') or 'JDM Cars Bot'
    about_text = (
        f"ℹ️ <b>О боте</b>\n\n"
        f"Этот бот создан для каталогизации крутых тачек, "
        f"сфотографированных на улицах города.\n\n"
        f"🎯 Здесь ты найдешь:\n"
        f"• JDM легенды\n"
        f"• Редкие модели\n"
        f"• Тюнингованные машины\n"
        f"• И многое другое!\n\n"
        f"📸 Все фото сделаны энтузиастами автомобильной культуры.\n\n"
        f"<i>Создано <a href='https://t.me/pr0stoy4elovek'>@pr0stoy4elovek</a></i>"
    )
    try:
        await callback.message.edit_text(about_text, reply_markup=back_to_main_kb(), disable_web_page_preview=True)
    except:
        await callback.message.delete()
        await callback.message.answer(about_text, reply_markup=back_to_main_kb(), disable_web_page_preview=True)
    await callback.answer()


# ============= КАТАЛОГ =============

@dp.callback_query(F.data == "catalog")
@dp.callback_query(F.data.startswith("nav_"))
async def show_catalog(callback: CallbackQuery):
    """Показать каталог (листание карточек)"""
    # Определяем индекс
    current_index = 0
    if callback.data.startswith("nav_"):
        current_index = int(callback.data.split("_")[1])
    
    # Получаем все машины
    all_cars = await db.get_all_cars(limit=1000)
    
    if not all_cars:
        text = "😔 Каталог пока пуст.\n\nСкоро здесь появятся крутые тачки!"
        try:
            await callback.message.edit_text(text, reply_markup=back_to_main_kb())
        except:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=back_to_main_kb())
        await callback.answer()
        return
    
    # Получаем текущую машину
    car = all_cars[current_index]
    
    # Увеличиваем счетчик просмотров
    await db.increment_views(car['id'], callback.from_user.id)
    
    # Проверяем избранное
    is_fav = await db.is_favorite(callback.from_user.id, car['id'])
    is_adm = is_admin(callback.from_user.id)
    
    text = format_car_info(car)
    # Жёсткая обрезка прямо перед отправкой
    if len(text) > 1024:
        text = text[:1020] + "..."
    
    # Отправляем/обновляем карточку
    try:
        await callback.message.delete()
    except:
        pass
    
    try:
        await callback.message.answer_photo(
            photo=car['photo_id'],
            caption=text,
            reply_markup=car_navigation_kb(current_index, len(all_cars), car['id'], is_fav, is_adm)
        )
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await callback.message.answer(
            text,
            reply_markup=car_navigation_kb(current_index, len(all_cars), car['id'], is_fav, is_adm)
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("car_"))
async def show_car(callback: CallbackQuery):
    """Показать карточку автомобиля (из поиска)"""
    car_id = int(callback.data.split("_")[1])
    car = await db.get_car(car_id)
    
    if not car:
        await callback.answer("❌ Машина не найдена", show_alert=True)
        return
    
    # Увеличиваем счетчик просмотров
    await db.increment_views(car_id, callback.from_user.id)
    
    # Проверяем, в избранном ли
    is_fav = await db.is_favorite(callback.from_user.id, car_id)
    is_adm = is_admin(callback.from_user.id)
    
    text = format_car_info(car)
    
    # Отправляем фото с описанием (без навигации, т.к. из поиска)
    builder = InlineKeyboardBuilder()
    
    fav_text = "💔 Убрать из избранного" if is_fav else "❤️ В избранное"
    builder.row(InlineKeyboardButton(text=fav_text, callback_data=f"fav_{car_id}"))
    
    if is_adm:
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{car_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{car_id}")
        )
    
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=car['photo_id'],
        caption=text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# ============= ИЗБРАННОЕ =============

@dp.callback_query(F.data.startswith("fav_"))
async def toggle_favorite(callback: CallbackQuery):
    """Добавить/убрать из избранного"""
    car_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    is_fav = await db.is_favorite(user_id, car_id)
    
    if is_fav:
        await db.remove_from_favorites(user_id, car_id)
        await callback.answer("💔 Убрано из избранного")
    else:
        await db.add_to_favorites(user_id, car_id)
        await callback.answer("❤️ Добавлено в избранное")
    
    # Обновляем клавиатуру
    # Проверяем, есть ли навигация (из каталога или из поиска)
    if callback.message.reply_markup and len(callback.message.reply_markup.inline_keyboard) > 2:
        # Это из каталога с навигацией - нужно найти индекс
        all_cars = await db.get_all_cars(limit=1000)
        current_index = 0
        for i, car in enumerate(all_cars):
            if car['id'] == car_id:
                current_index = i
                break
        
        is_adm = is_admin(user_id)
        await callback.message.edit_reply_markup(
            reply_markup=car_navigation_kb(current_index, len(all_cars), car_id, not is_fav, is_adm)
        )
    else:
        # Это из поиска - простая клавиатура
        is_adm = is_admin(user_id)
        builder = InlineKeyboardBuilder()
        
        fav_text = "💔 Убрать из избранного" if not is_fav else "❤️ В избранное"
        builder.row(InlineKeyboardButton(text=fav_text, callback_data=f"fav_{car_id}"))
        
        if is_adm:
            builder.row(
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{car_id}"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{car_id}")
            )
        
        builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))
        
        await callback.message.edit_reply_markup(reply_markup=builder.as_markup())


@dp.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery):
    """Показать избранное"""
    favorites = await db.get_favorites(callback.from_user.id)
    
    if not favorites:
        text = (
            "⭐ <b>Избранное</b>\n\n"
            "У тебя пока нет избранных машин.\n\n"
            "Добавляй понравившиеся машины в избранное, "
            "нажимая ❤️ на карточке автомобиля!"
        )
        try:
            await callback.message.edit_text(text, reply_markup=back_to_main_kb())
        except:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=back_to_main_kb())
        await callback.answer()
        return
    
    # Показываем первую машину из избранного
    car = favorites[0]
    
    await db.increment_views(car['id'], callback.from_user.id)
    
    is_fav = True  # Точно в избранном
    is_adm = is_admin(callback.from_user.id)
    
    text = "⭐ <b>Избранное</b>\n\n" + format_car_info(car)
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer_photo(
        photo=car['photo_id'],
        caption=text,
        reply_markup=car_navigation_kb(0, len(favorites), car['id'], is_fav, is_adm)
    )
    await callback.answer()


# ============= ПОИСК =============

@dp.callback_query(F.data == "search")
async def start_search(callback: CallbackQuery, state: FSMContext):
    """Начать поиск"""
    text = (
        "🔍 <b>Поиск машины</b>\n\n"
        "Введи марку или модель автомобиля:"
    )
    try:
        await callback.message.edit_text(text, reply_markup=cancel_kb())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=cancel_kb())
    
    await state.set_state(SearchStates.waiting_for_query)
    await callback.answer()


@dp.message(SearchStates.waiting_for_query)
async def process_search(message: Message, state: FSMContext):
    """Обработка поискового запроса"""
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer("❌ Запрос слишком короткий. Введи минимум 2 символа.")
        return
    
    results = await db.search_cars(query)
    
    await state.clear()
    
    if not results:
        await message.answer(
            f"😔 По запросу '<b>{query}</b>' ничего не найдено.\n\n"
            "Попробуй другой запрос.",
            reply_markup=back_to_main_kb()
        )
        return
    
    # Показываем список найденных машин
    text = f"🔍 <b>Результаты поиска</b>\n\nНайдено: {len(results)}\n\n"
    
    for i, car in enumerate(results[:10], 1):  # Показываем первые 10
        year = f" ({car['year']})" if car.get('year') else ""
        text += f"{i}. {car['brand']} {car['model']}{year}\n"
    
    if len(results) > 10:
        text += f"\n... и ещё {len(results) - 10}"
    
    # Создаём кнопки для выбора
    builder = InlineKeyboardBuilder()
    for car in results[:10]:
        year = f" ({car['year']})" if car.get('year') else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{car['brand']} {car['model']}{year}",
                callback_data=f"car_{car['id']}"
            )
        )
    
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))
    
    await message.answer(text, reply_markup=builder.as_markup())


# ============= СЛУЧАЙНАЯ МАШИНА =============

@dp.callback_query(F.data == "random")
async def show_random_car(callback: CallbackQuery):
    """Показать случайную машину"""
    car = await db.get_random_car()
    
    if not car:
        await callback.answer("😔 В базе пока нет машин", show_alert=True)
        return
    
    # Увеличиваем счетчик просмотров
    await db.increment_views(car['id'], callback.from_user.id)
    
    is_fav = await db.is_favorite(callback.from_user.id, car['id'])
    is_adm = is_admin(callback.from_user.id)
    
    text = "🎲 <b>Случайная машина дня!</b>\n\n" + format_car_info(car)
    
    # Простая клавиатура без навигации
    builder = InlineKeyboardBuilder()
    
    fav_text = "💔 Убрать из избранного" if is_fav else "❤️ В избранное"
    builder.row(InlineKeyboardButton(text=fav_text, callback_data=f"fav_{car['id']}"))
    
    # Кнопка "Ещё одну"
    builder.row(InlineKeyboardButton(text="🎲 Ещё одну", callback_data="random"))
    
    if is_adm:
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{car['id']}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{car['id']}")
        )
    
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))
    
    await callback.message.delete()
    await callback.message.answer_photo(
        photo=car['photo_id'],
        caption=text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# ============= СТАТИСТИКА =============

@dp.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    stats = await db.get_stats()
    text = format_stats(stats)
    
    try:
        await callback.message.edit_text(text, reply_markup=back_to_main_kb())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=back_to_main_kb())
    
    await callback.answer()


# ============= ОТМЕНА =============

@dp.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await back_to_main(callback, state)


# Запуск бота
async def main():
    # Инициализация базы данных
    await db.init_db()
    logger.info("База данных инициализирована")
    
    # Запуск бота
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
