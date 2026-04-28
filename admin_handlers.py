from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from db_adapter import db
from keyboards import admin_menu_kb, catalog_kb, confirm_delete_kb, cancel_kb, back_to_main_kb, search_results_kb, search_results_kb
from states import AddCarStates
from utils import is_admin, format_car_info

router = Router()


# Фильтр для админов
def admin_filter(callback: CallbackQuery) -> bool:
    return is_admin(callback.from_user.id)


# ============= АДМИН ПАНЕЛЬ =============

@router.callback_query(F.data == "admin_panel")
async def show_admin_panel(callback: CallbackQuery):
    """Показать админ-панель"""
    if not is_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id):
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


# ============= СПИСОК МАШИН =============

@router.callback_query(F.data == "admin_list")
async def show_admin_list(callback: CallbackQuery):
    """Показать список машин для админа"""
    if not is_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id):
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
    
    await callback.message.edit_caption(
        caption=text,
        reply_markup=confirm_delete_kb(car_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def delete_car(callback: CallbackQuery):
    """Удаление машины"""
    if not is_admin(callback.from_user.id):
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
