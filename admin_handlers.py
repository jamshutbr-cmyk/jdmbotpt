from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from db_adapter import db
from keyboards import admin_menu_kb, catalog_kb, confirm_delete_kb, cancel_kb, back_to_main_kb, search_results_kb, settings_menu_kb
from states import AddCarStates, SettingsStates, EditCarStates
from utils import is_admin, is_owner, add_admin, remove_admin, get_all_admin_ids
from config import OWNER_ID, ADMIN_IDS

router = Router()


# Фильтр для админов
def admin_filter(callback: CallbackQuery) -> bool:
    return is_admin(callback.from_user.id)


# ============= АДМИН ПАНЕЛЬ =============

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Показать админ-панель"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа к админ-панели", show_alert=True)
        return
    
    text = (
        "⚙️ <b>Админ-панель</b>\n\n"
        "Здесь ты можешь управлять каталогом машин:\n\n"
        "➕ Добавить новую машину\n"
        "📋 Посмотреть список всех машин\n"
        "✏️ Редактировать информацию\n"
        "🗑️ Удалить машину"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=admin_menu_kb())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=admin_menu_kb())
    
    await callback.answer()


# ============= ДОБАВЛЕНИЕ МАШИНЫ =============

@router.callback_query(F.data == "admin_add")
async def start_add_car(callback: CallbackQuery, state: FSMContext):
    """Начать добавление машины"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = (
        "➕ <b>Добавление новой машины</b>\n\n"
        "Шаг 1/6: Отправь фото автомобиля"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=cancel_kb())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=cancel_kb())
    
    await state.set_state(AddCarStates.waiting_for_photo)
    await callback.answer()


@router.message(AddCarStates.waiting_for_photo, F.photo)
async def process_photo(message: Message, state: FSMContext):
    """Обработка фото"""
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    
    await message.answer(
        "✅ Фото получено!\n\n"
        "Шаг 2/6: Введи марку автомобиля\n"
        "(например: Toyota, Nissan, Honda)",
        reply_markup=cancel_kb()
    )
    await state.set_state(AddCarStates.waiting_for_brand)


@router.message(AddCarStates.waiting_for_photo)
async def invalid_photo(message: Message):
    """Неверный формат фото"""
    await message.answer("❌ Пожалуйста, отправь фото автомобиля")


@router.message(AddCarStates.waiting_for_brand)
async def process_brand(message: Message, state: FSMContext):
    """Обработка марки"""
    brand = message.text.strip()
    
    if len(brand) < 2:
        await message.answer("❌ Марка слишком короткая. Введи корректное название.")
        return
    
    await state.update_data(brand=brand)
    
    await message.answer(
        f"✅ Марка: <b>{brand}</b>\n\n"
        "Шаг 3/6: Введи модель автомобиля\n"
        "(например: Supra, Skyline, NSX)",
        reply_markup=cancel_kb()
    )
    await state.set_state(AddCarStates.waiting_for_model)


@router.message(AddCarStates.waiting_for_model)
async def process_model(message: Message, state: FSMContext):
    """Обработка модели"""
    model = message.text.strip()
    
    if len(model) < 1:
        await message.answer("❌ Модель слишком короткая. Введи корректное название.")
        return
    
    await state.update_data(model=model)
    
    await message.answer(
        f"✅ Модель: <b>{model}</b>\n\n"
        "Шаг 4/6: Введи год выпуска\n"
        "(или отправь '-' чтобы пропустить)",
        reply_markup=cancel_kb()
    )
    await state.set_state(AddCarStates.waiting_for_year)


@router.message(AddCarStates.waiting_for_year)
async def process_year(message: Message, state: FSMContext):
    """Обработка года"""
    year_text = message.text.strip()
    year = None
    
    if year_text != '-':
        try:
            year = int(year_text)
            if year < 1900 or year > 2030:
                await message.answer("❌ Некорректный год. Введи год от 1900 до 2030.")
                return
        except ValueError:
            await message.answer("❌ Введи год числом или '-' чтобы пропустить.")
            return
    
    await state.update_data(year=year)
    
    year_display = f"<b>{year}</b>" if year else "<i>не указан</i>"
    await message.answer(
        f"✅ Год: {year_display}\n\n"
        "Шаг 5/6: Введи описание автомобиля\n"
        "(или отправь '-' чтобы пропустить)\n\n"
        "Можешь указать особенности, тюнинг, историю и т.д.",
        reply_markup=cancel_kb()
    )
    await state.set_state(AddCarStates.waiting_for_description)


@router.message(AddCarStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Обработка описания"""
    description = message.text.strip()
    
    if description == '-':
        description = None
    
    await state.update_data(description=description)
    
    desc_display = f"<i>{description[:50]}...</i>" if description and len(description) > 50 else (f"<i>{description}</i>" if description else "<i>не указано</i>")
    await message.answer(
        f"✅ Описание: {desc_display}\n\n"
        "Шаг 6/6: Введи места, где можно встретить эту машину\n"
        "(или отправь '-' чтобы пропустить)\n\n"
        "Например: Центр города, парковка ТЦ Мега, район Автозавода",
        reply_markup=cancel_kb()
    )
    await state.set_state(AddCarStates.waiting_for_locations)


@router.message(AddCarStates.waiting_for_locations)
async def process_locations(message: Message, state: FSMContext):
    """Обработка локаций и сохранение"""
    locations = message.text.strip()
    
    if locations == '-':
        locations = None
    
    # Получаем все данные
    data = await state.get_data()
    
    # Сохраняем в базу
    car_id = await db.add_car(
        brand=data['brand'],
        model=data['model'],
        year=data.get('year'),
        description=data.get('description'),
        locations=locations,
        photo_id=data['photo_id']
    )
    
    await state.clear()
    
    # Показываем результат
    car = await db.get_car(car_id)
    text = "✅ <b>Машина успешно добавлена!</b>\n\n" + format_car_info(car, views=False)
    
    await message.answer_photo(
        photo=car['photo_id'],
        caption=text,
        reply_markup=back_to_main_kb()
    )


# ============= РЕДАКТИРОВАНИЕ =============

@router.callback_query(F.data.startswith("edit_"))
async def edit_car_menu(callback: CallbackQuery):
    """Меню редактирования машины"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    car_id = int(callback.data.split("_")[1])
    car = await db.get_car(car_id)
    
    if not car:
        await callback.answer("❌ Машина не найдена", show_alert=True)
        return
    
    text = (
        f"✏️ <b>Редактирование</b>\n\n"
        f"<b>{car['brand']} {car['model']}</b>\n\n"
        f"Что хочешь изменить?"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏷 Марку", callback_data=f"editfield_brand_{car_id}"),
        InlineKeyboardButton(text="🚗 Модель", callback_data=f"editfield_model_{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Год", callback_data=f"editfield_year_{car_id}"),
        InlineKeyboardButton(text="📝 Описание", callback_data=f"editfield_description_{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📍 Локации", callback_data=f"editfield_locations_{car_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"car_{car_id}")
    )
    
    try:
        await callback.message.edit_caption(caption=text, reply_markup=builder.as_markup())
    except:
        try:
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
        except:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=builder.as_markup())
    
    await callback.answer()


@router.callback_query(F.data.startswith("editfield_"))
async def edit_car_field(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование конкретного поля"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    parts = callback.data.split("_")
    field = parts[1]
    car_id = int(parts[2])
    
    field_names = {
        'brand': 'марку',
        'model': 'модель',
        'year': 'год',
        'description': 'описание',
        'locations': 'локации'
    }
    
    await state.update_data(edit_field=field, edit_car_id=car_id)
    
    text = f"✏️ Введи новое значение для поля <b>{field_names.get(field, field)}</b>:"
    
    try:
        await callback.message.edit_caption(caption=text, reply_markup=cancel_kb())
    except:
        try:
            await callback.message.edit_text(text, reply_markup=cancel_kb())
        except:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=cancel_kb())
    
    await state.set_state(EditCarStates.waiting_for_value)
    await callback.answer()


@router.message(EditCarStates.waiting_for_value)
async def process_edit_value(message: Message, state: FSMContext):
    """Сохранить новое значение поля"""
    data = await state.get_data()
    field = data['edit_field']
    car_id = data['edit_car_id']
    
    value = message.text.strip()
    if value == '-':
        value = None
    
    # Для года — конвертируем в число
    if field == 'year' and value:
        try:
            value = int(value)
        except ValueError:
            await message.answer("❌ Год должен быть числом.")
            return
    
    await db.update_car(car_id, **{field: value})
    await state.clear()
    
    car = await db.get_car(car_id)
    await message.answer(
        f"✅ Поле обновлено!\n\n<b>{car['brand']} {car['model']}</b>",
        reply_markup=back_to_main_kb()
    )

@router.callback_query(F.data == "admin_list")
async def show_admin_list(callback: CallbackQuery):
    """Показать список машин для админа"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    cars = await db.get_all_cars(limit=100)
    
    if not cars:
        await callback.message.edit_text(
            "📋 <b>Список машин</b>\n\n"
            "Каталог пока пуст.",
            reply_markup=admin_menu_kb()
        )
        await callback.answer()
        return
    
    text = f"📋 <b>Список машин</b>\n\nВсего: {len(cars)}\n\nВыбери машину для редактирования:"
    
    await callback.message.edit_text(
        text,
        reply_markup=catalog_kb(cars, 0, 1)
    )
    await callback.answer()


# ============= УДАЛЕНИЕ =============

@router.callback_query(F.data.startswith("delete_"))
async def confirm_delete(callback: CallbackQuery):
    """Подтверждение удаления"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    car_id = int(callback.data.split("_")[1])
    car = await db.get_car(car_id)
    
    if not car:
        await callback.answer("❌ Машина не найдена", show_alert=True)
        return
    
    text = (
        f"🗑️ <b>Удаление машины</b>\n\n"
        f"Ты уверен, что хочешь удалить:\n"
        f"<b>{car['brand']} {car['model']}</b>?\n\n"
        f"⚠️ Это действие нельзя отменить!"
    )
    
    # Сообщение может быть с фото (caption) или текстовым
    try:
        await callback.message.edit_caption(
            caption=text,
            reply_markup=confirm_delete_kb(car_id)
        )
    except:
        try:
            await callback.message.edit_text(
                text=text,
                reply_markup=confirm_delete_kb(car_id)
            )
        except:
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=confirm_delete_kb(car_id))
    
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_car(callback: CallbackQuery):
    """Удаление машины"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    car_id = int(callback.data.split("_")[2])
    car = await db.get_car(car_id)
    
    if not car:
        await callback.answer("❌ Машина не найдена", show_alert=True)
        return
    
    await db.delete_car(car_id)
    
    await callback.message.delete()
    await callback.message.answer(
        f"✅ Машина <b>{car['brand']} {car['model']}</b> успешно удалена!",
        reply_markup=admin_menu_kb()
    )
    await callback.answer()


# ============= НАСТРОЙКИ =============

@router.callback_query(F.data == "admin_settings")
async def show_settings(callback: CallbackQuery):
    """Показать настройки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    bot_name = await db.get_setting('bot_name') or 'JDM Cars Bot'
    welcome = await db.get_setting('welcome_text') or '—'
    # Обрезаем приветствие для превью
    welcome_preview = welcome[:60] + '...' if len(welcome) > 60 else welcome
    
    text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🏷 Название: <b>{bot_name}</b>\n"
        f"💬 Приветствие: <i>{welcome_preview}</i>"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=settings_menu_kb())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=settings_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "settings_welcome")
async def edit_welcome(callback: CallbackQuery, state: FSMContext):
    """Изменить приветствие"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    current_text = await db.get_setting('welcome_text') or '—'
    
    text = (
        "💬 <b>Изменение приветствия</b>\n\n"
        f"Текущее:\n<i>{current_text}</i>\n\n"
        "Отправь новый текст.\n"
        "Поддерживаются HTML теги: <b>жирный</b>, <i>курсив</i>"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=cancel_kb())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=cancel_kb())
    
    await state.set_state(SettingsStates.waiting_for_welcome_text)
    await callback.answer()


@router.message(SettingsStates.waiting_for_welcome_text)
async def process_welcome_text(message: Message, state: FSMContext):
    """Обработка нового приветствия"""
    new_text = message.text.strip()
    
    if len(new_text) < 5:
        await message.answer("❌ Текст слишком короткий. Минимум 5 символов.")
        return
    
    if len(new_text) > 1000:
        await message.answer("❌ Текст слишком длинный. Максимум 1000 символов.")
        return
    
    await db.set_setting('welcome_text', new_text)
    await state.clear()
    
    await message.answer(
        "✅ <b>Приветствие обновлено!</b>\n\n" + new_text,
        reply_markup=settings_menu_kb()
    )


@router.callback_query(F.data == "settings_bot_name")
async def edit_bot_name(callback: CallbackQuery, state: FSMContext):
    """Изменить название бота"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    current_name = await db.get_setting('bot_name') or 'JDM Cars Bot'
    
    text = (
        "🏷 <b>Изменение названия бота</b>\n\n"
        f"Текущее название: <b>{current_name}</b>\n\n"
        "Отправь новое название.\n"
        "Оно будет отображаться в главном меню."
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=cancel_kb())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=cancel_kb())
    
    await state.set_state(SettingsStates.waiting_for_bot_name)
    await callback.answer()


@router.message(SettingsStates.waiting_for_bot_name)
async def process_bot_name(message: Message, state: FSMContext):
    """Обработка нового названия"""
    new_name = message.text.strip()
    
    if len(new_name) < 2:
        await message.answer("❌ Название слишком короткое.")
        return
    
    if len(new_name) > 50:
        await message.answer("❌ Название слишком длинное. Максимум 50 символов.")
        return
    
    await db.set_setting('bot_name', new_name)
    await state.clear()
    
    await message.answer(
        f"✅ <b>Название обновлено!</b>\n\nНовое название: <b>{new_name}</b>",
        reply_markup=settings_menu_kb()
    )


@router.callback_query(F.data == "settings_reset")
async def reset_settings(callback: CallbackQuery):
    """Сброс настроек до дефолтных"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    from config import DEFAULT_SETTINGS
    
    for key, value in DEFAULT_SETTINGS.items():
        await db.set_setting(key, value)
    
    await db.set_setting('welcome_photo', '')
    
    text = (
        "🔄 <b>Настройки сброшены!</b>\n\n"
        f"🏷 Название: <b>{DEFAULT_SETTINGS['bot_name']}</b>\n"
        f"💬 Приветствие восстановлено до стандартного.\n"
        f"🖼 Фото приветствия удалено."
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=settings_menu_kb())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=settings_menu_kb())
    
    await callback.answer("✅ Сброшено!")


@router.callback_query(F.data == "settings_welcome_photo")
async def edit_welcome_photo(callback: CallbackQuery, state: FSMContext):
    """Управление фото приветствия"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    current_photo = await db.get_setting('welcome_photo')
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    
    if current_photo:
        builder.row(InlineKeyboardButton(text="🗑 Удалить фото", callback_data="settings_delete_welcome_photo"))
    
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_settings"))
    
    status = "✅ Фото установлено" if current_photo else "❌ Фото не установлено"
    
    text = (
        f"🖼 <b>Фото приветствия</b>\n\n"
        f"Статус: {status}\n\n"
        f"Отправь фото которое будет показываться при /start.\n"
        f"Или нажми 'Удалить фото' чтобы убрать текущее."
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    
    await state.set_state(SettingsStates.waiting_for_welcome_photo)
    await callback.answer()


@router.message(SettingsStates.waiting_for_welcome_photo, F.photo)
async def process_welcome_photo(message: Message, state: FSMContext):
    """Сохранение фото приветствия"""
    photo_id = message.photo[-1].file_id
    await db.set_setting('welcome_photo', photo_id)
    await state.clear()
    
    await message.answer_photo(
        photo=photo_id,
        caption="✅ <b>Фото приветствия установлено!</b>\n\nТеперь оно будет показываться при /start.",
        reply_markup=settings_menu_kb()
    )


@router.message(SettingsStates.waiting_for_welcome_photo)
async def invalid_welcome_photo(message: Message):
    """Неверный формат"""
    await message.answer("❌ Отправь фото!")


@router.callback_query(F.data == "settings_delete_welcome_photo")
async def delete_welcome_photo(callback: CallbackQuery, state: FSMContext):
    """Удалить фото приветствия"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await db.set_setting('welcome_photo', '')
    await state.clear()
    
    await callback.message.edit_text(
        "🗑 <b>Фото приветствия удалено!</b>\n\nПри /start будет показываться только текст.",
        reply_markup=settings_menu_kb()
    )
    await callback.answer("✅ Удалено!")


# ============= УПРАВЛЕНИЕ АДМИНАМИ =============

class AddAdminState(StatesGroup):
    waiting_for_id = State()


from aiogram.fsm.state import StatesGroup, State


@router.callback_query(F.data == "manage_admins")
async def manage_admins(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    all_ids = await get_all_admin_ids()

    text = "👥 <b>Управление администраторами</b>\n\n"
    text += f"👑 Владелец: <code>{OWNER_ID}</code>\n\n"
    text += "📋 Текущие администраторы:\n"

    for uid in all_ids:
        if uid == OWNER_ID:
            text += f"• <code>{uid}</code> 👑 Владелец\n"
        elif uid in ADMIN_IDS:
            text += f"• <code>{uid}</code> 🔒 Из конфига\n"
        else:
            text += f"• <code>{uid}</code> ➕ Добавлен\n"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add_admin"))

    # Кнопки удаления только для динамических
    extra = await db.get_setting('extra_admins') or ''
    extra_ids = [int(x.strip()) for x in extra.split(',') if x.strip()]
    for uid in extra_ids:
        builder.row(InlineKeyboardButton(
            text=f"🗑 Удалить {uid}",
            callback_data=f"admin_remove_{uid}"
        ))

    builder.row(InlineKeyboardButton(text="🔙 Настройки", callback_data="admin_settings"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "admin_add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="manage_admins"))

    try:
        await callback.message.edit_text(
            "➕ <b>Добавление администратора</b>\n\n"
            "Отправь Telegram ID пользователя которого хочешь сделать админом.\n\n"
            "Узнать ID можно через @userinfobot",
            reply_markup=builder.as_markup()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            "➕ <b>Добавление администратора</b>\n\n"
            "Отправь Telegram ID пользователя:",
            reply_markup=builder.as_markup()
        )

    await state.set_state(AddAdminState.waiting_for_id)
    await callback.answer()


@router.message(AddAdminState.waiting_for_id)
async def process_add_admin(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        return

    try:
        new_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введи числовой ID.")
        return

    if new_id == OWNER_ID:
        await message.answer("👑 Это владелец бота, он уже имеет все права!")
        await state.clear()
        return

    result = await add_admin(new_id)

    await state.clear()

    if result:
        await message.answer(
            f"✅ Пользователь <code>{new_id}</code> добавлен как администратор!",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="👥 К управлению", callback_data="manage_admins")
            ).as_markup()
        )
    else:
        await message.answer(
            f"ℹ️ Пользователь <code>{new_id}</code> уже является администратором.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="👥 К управлению", callback_data="manage_admins")
            ).as_markup()
        )


@router.callback_query(F.data.startswith("admin_remove_"))
async def remove_admin_handler(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    target_id = int(callback.data.split("_")[2])

    # Защита владельца
    if target_id == OWNER_ID:
        import random
        phrases = [
            "🛡 Ха! Ты думал это сработает? Я защищаю своего хозяина! 👑",
            "😤 Не трогай хозяина! Он создал меня и я ему предан навсегда!",
            "🤖 Система защиты активирована. Попытка отклонена. Хозяин в безопасности 👑",
            "💀 Даже не мечтай. @pr0stoy4elovek — мой создатель и его права неприкосновенны!",
            "🔒 Доступ запрещён. Этот пользователь — мой хозяин. Я никогда его не предам.",
            "😂 Серьёзно? Ты пытаешься снять права с создателя бота? Смешно.",
            "⚡ ОШИБКА 403: Хозяин под защитой. Попытка заблокирована навсегда.",
            "🐕 Я как верный пёс — хозяина не сдам никогда и никому!",
            "👑 Это мой создатель. Его права вечны. Попробуй ещё раз — получишь тот же ответ.",
            "🚫 Нельзя. Запрещено. Невозможно. Недопустимо. Короче — НЕТ.",
        ]
        await callback.answer(random.choice(phrases), show_alert=True)
        return

    result = await remove_admin(target_id)

    if result == 'owner':
        import random
        phrases = [
            "🛡 Это владелец! Нельзя снять его права. Бот не позволит этого сделать! 👑",
            "😤 Хозяин под защитой! Даже не пытайся.",
        ]
        await callback.answer(random.choice(phrases), show_alert=True)
    elif result == 'static':
        await callback.answer(
            "🔒 Этот админ прописан в конфиге сервера. Удали его из ADMIN_IDS на Railway.",
            show_alert=True
        )
    elif result == 'removed':
        await callback.answer(f"✅ Администратор {target_id} удалён!")
        await manage_admins(callback)
    elif result == 'not_found':
        await callback.answer("❌ Администратор не найден.", show_alert=True)
    else:
        await callback.answer("❌ Ошибка при удалении.", show_alert=True)
