from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db_adapter import db
from states import SuggestCarStates, AdminRejectStates
from utils import is_admin, format_car_info
from config import ADMIN_IDS

router = Router()


# ============= МЕНЮ ПРЕДЛОЖЕНИЙ =============

@router.callback_query(F.data == "suggest_menu")
async def suggest_menu(callback: CallbackQuery):
    text = (
        "📸 <b>Предложить машину</b>\n\n"
        "Видел крутую тачку на улице? Поделись с нами!\n\n"
        "Твоё фото пройдёт модерацию и появится в каталоге.\n\n"
        "📋 Что нужно:\n"
        "• Фото машины\n"
        "• Марка и модель\n"
        "• Год (по желанию)\n"
        "• Описание (по желанию)\n"
        "• Место где видел"
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📸 Предложить машину", callback_data="suggest_start"))
    builder.row(InlineKeyboardButton(text="📋 Мои предложения", callback_data="my_suggestions"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ============= СОЗДАНИЕ ПРЕДЛОЖЕНИЯ =============

@router.callback_query(F.data == "suggest_start")
async def suggest_start(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="suggest_menu"))

    text = "📸 <b>Предложение машины</b>\n\nШаг 1/6: Отправь фото автомобиля"
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())

    await state.set_state(SuggestCarStates.waiting_for_photo)
    await callback.answer()


@router.message(SuggestCarStates.waiting_for_photo, F.photo)
async def suggest_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="suggest_menu"))

    await message.answer(
        "✅ Фото получено!\n\nШаг 2/6: Введи марку автомобиля\n(например: Toyota, Nissan)",
        reply_markup=builder.as_markup()
    )
    await state.set_state(SuggestCarStates.waiting_for_brand)


@router.message(SuggestCarStates.waiting_for_photo)
async def suggest_photo_invalid(message: Message):
    await message.answer("❌ Пожалуйста, отправь фото!")


@router.message(SuggestCarStates.waiting_for_brand)
async def suggest_brand(message: Message, state: FSMContext):
    brand = message.text.strip()
    if len(brand) < 2:
        await message.answer("❌ Слишком короткое название.")
        return
    await state.update_data(brand=brand)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="suggest_menu"))

    await message.answer(
        f"✅ Марка: <b>{brand}</b>\n\nШаг 3/6: Введи модель автомобиля",
        reply_markup=builder.as_markup()
    )
    await state.set_state(SuggestCarStates.waiting_for_model)


@router.message(SuggestCarStates.waiting_for_model)
async def suggest_model(message: Message, state: FSMContext):
    model = message.text.strip()
    if len(model) < 1:
        await message.answer("❌ Слишком короткое название.")
        return
    await state.update_data(model=model)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="suggest_menu"))

    await message.answer(
        f"✅ Модель: <b>{model}</b>\n\nШаг 4/6: Введи год выпуска\n(или '-' чтобы пропустить)",
        reply_markup=builder.as_markup()
    )
    await state.set_state(SuggestCarStates.waiting_for_year)


@router.message(SuggestCarStates.waiting_for_year)
async def suggest_year(message: Message, state: FSMContext):
    year_text = message.text.strip()
    year = None
    if year_text != '-':
        try:
            year = int(year_text)
            if year < 1900 or year > 2030:
                await message.answer("❌ Некорректный год.")
                return
        except ValueError:
            await message.answer("❌ Введи год числом или '-'.")
            return
    await state.update_data(year=year)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="suggest_menu"))

    await message.answer(
        "Шаг 5/6: Опиши машину\n(тюнинг, особенности, или '-' чтобы пропустить)",
        reply_markup=builder.as_markup()
    )
    await state.set_state(SuggestCarStates.waiting_for_description)


@router.message(SuggestCarStates.waiting_for_description)
async def suggest_description(message: Message, state: FSMContext):
    desc = message.text.strip()
    if desc == '-':
        desc = None
    await state.update_data(description=desc)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="suggest_menu"))

    await message.answer(
        "Шаг 6/6: Где видел эту машину?\n(адрес, район, или '-' чтобы пропустить)",
        reply_markup=builder.as_markup()
    )
    await state.set_state(SuggestCarStates.waiting_for_locations)


@router.message(SuggestCarStates.waiting_for_locations)
async def suggest_locations(message: Message, state: FSMContext, bot: Bot):
    locations = message.text.strip()
    if locations == '-':
        locations = None

    data = await state.get_data()
    username = message.from_user.username or message.from_user.first_name

    suggestion_id = await db.create_suggestion(
        user_id=message.from_user.id,
        username=username,
        brand=data['brand'],
        model=data['model'],
        year=data.get('year'),
        description=data.get('description'),
        locations=locations,
        photo_id=data['photo_id']
    )

    await state.clear()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Мои предложения", callback_data="my_suggestions"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))

    await message.answer(
        f"✅ <b>Предложение #{suggestion_id} отправлено!</b>\n\n"
        f"🚗 {data['brand']} {data['model']}\n\n"
        f"Мы рассмотрим его в ближайшее время и уведомим тебя о решении.",
        reply_markup=builder.as_markup()
    )

    # Уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            admin_builder = InlineKeyboardBuilder()
            admin_builder.row(InlineKeyboardButton(
                text=f"📂 Рассмотреть #{suggestion_id}",
                callback_data=f"admin_review_{suggestion_id}"
            ))
            year_str = f" ({data['year']})" if data.get('year') else ""
            await bot.send_photo(
                admin_id,
                photo=data['photo_id'],
                caption=(
                    f"🔔 <b>Новое предложение #{suggestion_id}!</b>\n\n"
                    f"👤 От: @{username}\n"
                    f"🚗 {data['brand']} {data['model']}{year_str}\n"
                    f"📝 {data.get('description') or '—'}\n"
                    f"📍 {locations or '—'}"
                ),
                reply_markup=admin_builder.as_markup()
            )
        except:
            pass


# ============= МОИ ПРЕДЛОЖЕНИЯ =============

@router.callback_query(F.data == "my_suggestions")
async def my_suggestions(callback: CallbackQuery):
    suggestions = await db.get_user_suggestions(callback.from_user.id)

    if not suggestions:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📸 Предложить машину", callback_data="suggest_start"))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="suggest_menu"))
        try:
            await callback.message.edit_text(
                "📋 <b>Мои предложения</b>\n\nУ тебя пока нет предложений.",
                reply_markup=builder.as_markup()
            )
        except:
            await callback.message.delete()
            await callback.message.answer(
                "📋 <b>Мои предложения</b>\n\nУ тебя пока нет предложений.",
                reply_markup=builder.as_markup()
            )
        await callback.answer()
        return

    status_map = {
        'pending': '⏳ На рассмотрении',
        'approved': '✅ Одобрено',
        'rejected': '❌ Отклонено'
    }

    text = "📋 <b>Мои предложения</b>\n\n"
    for s in suggestions[:10]:
        status = status_map.get(s['status'], s['status'])
        year = f" ({s['year']})" if s.get('year') else ""
        text += f"#{s['id']} {s['brand']} {s['model']}{year} — {status}\n"
        if s['status'] == 'rejected' and s.get('reject_reason'):
            text += f"   💬 Причина: {s['reject_reason']}\n"
        text += "\n"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📸 Предложить ещё", callback_data="suggest_start"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="suggest_menu"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ============= АДМИН: МОДЕРАЦИЯ =============

@router.callback_query(F.data == "admin_suggestions")
async def admin_suggestions(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    pending = await db.get_pending_suggestions()

    if not pending:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel"))
        try:
            await callback.message.edit_text(
                "📸 <b>Предложения машин</b>\n\n✅ Нет новых предложений на рассмотрении.",
                reply_markup=builder.as_markup()
            )
        except:
            await callback.message.delete()
            await callback.message.answer(
                "📸 <b>Предложения машин</b>\n\n✅ Нет новых предложений на рассмотрении.",
                reply_markup=builder.as_markup()
            )
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    for s in pending[:15]:
        year = f" ({s['year']})" if s.get('year') else ""
        builder.row(InlineKeyboardButton(
            text=f"⏳ #{s['id']} @{s['username']} — {s['brand']} {s['model']}{year}",
            callback_data=f"admin_review_{s['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel"))

    try:
        await callback.message.edit_text(
            f"📸 <b>Предложения на рассмотрении: {len(pending)}</b>",
            reply_markup=builder.as_markup()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            f"📸 <b>Предложения на рассмотрении: {len(pending)}</b>",
            reply_markup=builder.as_markup()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_review_"))
async def admin_review_suggestion(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    suggestion_id = int(callback.data.split("_")[2])
    s = await db.get_suggestion(suggestion_id)

    if not s:
        await callback.answer("❌ Предложение не найдено", show_alert=True)
        return

    year = f" ({s['year']})" if s.get('year') else ""
    caption = (
        f"📸 <b>Предложение #{s['id']}</b>\n\n"
        f"👤 От: @{s['username']} (ID: {s['user_id']})\n"
        f"🚗 {s['brand']} {s['model']}{year}\n"
        f"📝 {s.get('description') or '—'}\n"
        f"📍 {s.get('locations') or '—'}\n"
        f"📅 {str(s['created_at'])[:16]}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"suggest_approve_{suggestion_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"suggest_reject_{suggestion_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 К списку", callback_data="admin_suggestions"))

    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer_photo(
        photo=s['photo_id'],
        caption=caption,
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("suggest_approve_"))
async def approve_suggestion(callback: CallbackQuery, bot: Bot):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    suggestion_id = int(callback.data.split("_")[2])
    s = await db.get_suggestion(suggestion_id)

    if not s:
        await callback.answer("❌ Предложение не найдено", show_alert=True)
        return

    # Добавляем машину в каталог
    car_id = await db.add_car(
        brand=s['brand'],
        model=s['model'],
        year=s.get('year'),
        description=s.get('description'),
        locations=s.get('locations'),
        photo_id=s['photo_id']
    )

    # Если пользователь разрешил показывать ник — добавляем в описание
    show_username = await db.get_show_username(s['user_id'])
    if show_username and s.get('username'):
        current_desc = s.get('description') or ''
        author_line = f"\n\n📸 Фото: @{s['username']}"
        new_desc = current_desc + author_line
        await db.update_car(car_id, description=new_desc)

    # Обновляем статус предложения
    await db.update_suggestion_status(suggestion_id, 'approved')

    # Уведомляем пользователя
    try:
        user_builder = InlineKeyboardBuilder()
        user_builder.row(InlineKeyboardButton(text="🚗 Посмотреть в каталоге", callback_data="catalog"))
        year = f" ({s['year']})" if s.get('year') else ""
        await bot.send_message(
            s['user_id'],
            f"✅ <b>Твоё предложение одобрено!</b>\n\n"
            f"🚗 {s['brand']} {s['model']}{year} добавлена в каталог!\n\n"
            f"Спасибо за вклад в наш каталог! 🔥",
            reply_markup=user_builder.as_markup()
        )
    except:
        pass

    try:
        await callback.message.delete()
    except:
        pass

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📸 К предложениям", callback_data="admin_suggestions"))
    builder.row(InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel"))

    await callback.message.answer(
        f"✅ <b>Предложение #{suggestion_id} одобрено!</b>\n\n"
        f"🚗 {s['brand']} {s['model']} добавлена в каталог (ID: {car_id})",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("suggest_reject_"))
async def reject_suggestion_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    suggestion_id = int(callback.data.split("_")[2])
    await state.update_data(reject_suggestion_id=suggestion_id)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="❌ Отмена",
        callback_data=f"admin_review_{suggestion_id}"
    ))

    try:
        await callback.message.edit_caption(
            caption=f"❌ <b>Отклонение предложения #{suggestion_id}</b>\n\nНапиши причину отказа:",
            reply_markup=builder.as_markup()
        )
    except:
        try:
            await callback.message.edit_text(
                f"❌ <b>Отклонение предложения #{suggestion_id}</b>\n\nНапиши причину отказа:",
                reply_markup=builder.as_markup()
            )
        except:
            await callback.message.delete()
            await callback.message.answer(
                f"❌ <b>Отклонение предложения #{suggestion_id}</b>\n\nНапиши причину отказа:",
                reply_markup=builder.as_markup()
            )

    await state.set_state(AdminRejectStates.waiting_for_reason)
    await callback.answer()


@router.message(AdminRejectStates.waiting_for_reason)
async def process_reject_reason(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    suggestion_id = data['reject_suggestion_id']
    s = await db.get_suggestion(suggestion_id)

    reason = message.text.strip()
    await db.update_suggestion_status(suggestion_id, 'rejected', reason)
    await state.clear()

    # Уведомляем пользователя
    try:
        year = f" ({s['year']})" if s.get('year') else ""
        await bot.send_message(
            s['user_id'],
            f"❌ <b>Предложение отклонено</b>\n\n"
            f"🚗 {s['brand']} {s['model']}{year}\n\n"
            f"💬 Причина: {reason}\n\n"
            f"Попробуй предложить другую машину!"
        )
    except:
        pass

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📸 К предложениям", callback_data="admin_suggestions"))

    await message.answer(
        f"✅ Предложение #{suggestion_id} отклонено.\nПричина отправлена пользователю.",
        reply_markup=builder.as_markup()
    )
