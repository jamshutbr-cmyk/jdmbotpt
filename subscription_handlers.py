from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db_adapter import db
from utils import is_admin
from subscription_check import check_all_subscriptions, build_subscribe_message

router = Router()


class AddChannelStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_url = State()
    waiting_for_channel_name = State()


def subscription_settings_kb(enabled: bool):
    builder = InlineKeyboardBuilder()
    status = "✅ Включена" if enabled else "❌ Выключена"
    toggle_text = "🔴 Выключить" if enabled else "🟢 Включить"
    builder.row(InlineKeyboardButton(text=f"Статус: {status}", callback_data="sub_status_info"))
    builder.row(InlineKeyboardButton(text=toggle_text, callback_data="sub_toggle"))
    builder.row(InlineKeyboardButton(text="➕ Добавить канал", callback_data="sub_add_channel"))
    builder.row(InlineKeyboardButton(text="📋 Список каналов", callback_data="sub_list_channels"))
    builder.row(InlineKeyboardButton(text="ℹ️ Инструкция", callback_data="sub_instruction"))
    builder.row(InlineKeyboardButton(text="🔙 Настройки", callback_data="admin_settings"))
    return builder.as_markup()


# ============= МЕНЮ ПОДПИСКИ =============

@router.callback_query(F.data == "subscription_settings")
async def subscription_settings(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    enabled_str = await db.get_setting('subscription_enabled') or '0'
    enabled = enabled_str == '1'
    channels = await db.get_required_channels()

    text = (
        "📢 <b>Система обязательной подписки</b>\n\n"
        f"Статус: {'✅ Включена' if enabled else '❌ Выключена'}\n"
        f"Каналов в списке: {len(channels)}\n\n"
        "Когда включена — пользователи должны подписаться на все активные каналы."
    )

    try:
        await callback.message.edit_text(text, reply_markup=subscription_settings_kb(enabled))
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=subscription_settings_kb(enabled))
    await callback.answer()


# ============= ВКЛЮЧИТЬ/ВЫКЛЮЧИТЬ =============

@router.callback_query(F.data == "sub_toggle")
async def toggle_subscription(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    enabled_str = await db.get_setting('subscription_enabled') or '0'
    enabled = enabled_str == '1'
    new_state = '0' if enabled else '1'

    if new_state == '1':
        channels = await db.get_required_channels()
        active = [c for c in channels if c.get('is_active', 1) not in (0, False)]
        if not active:
            await callback.answer("⚠️ Сначала добавь хотя бы один активный канал!", show_alert=True)
            return
        await callback.answer("✅ Проверка подписки включена!")
    else:
        await callback.answer("❌ Проверка подписки выключена!")

    await db.set_setting('subscription_enabled', new_state)
    await subscription_settings(callback)


@router.callback_query(F.data == "sub_status_info")
async def sub_status_info(callback: CallbackQuery):
    await callback.answer()


# ============= СПИСОК КАНАЛОВ =============

@router.callback_query(F.data == "sub_list_channels")
async def list_channels(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    channels = await db.get_required_channels()

    if not channels:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Добавить канал", callback_data="sub_add_channel"))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="subscription_settings"))
        try:
            await callback.message.edit_text("📋 <b>Список каналов</b>\n\nКаналов пока нет.", reply_markup=builder.as_markup())
        except:
            await callback.message.delete()
            await callback.message.answer("📋 <b>Список каналов</b>\n\nКаналов пока нет.", reply_markup=builder.as_markup())
        await callback.answer()
        return

    text = f"📋 <b>Список каналов ({len(channels)})</b>\n\n"
    builder = InlineKeyboardBuilder()

    for ch in channels:
        active = ch.get('is_active', 1)
        is_on = active not in (0, False)
        status_emoji = "✅" if is_on else "❌"
        toggle_text = "🔴 Выкл" if is_on else "🟢 Вкл"
        text += f"{status_emoji} <b>{ch['channel_name']}</b>\n   ID: <code>{ch['channel_id']}</code>\n\n"
        builder.row(
            InlineKeyboardButton(text=f"{status_emoji} {ch['channel_name']}", callback_data="sub_noop"),
            InlineKeyboardButton(text=toggle_text, callback_data=f"sub_toggle_ch_{ch['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"sub_remove_{ch['id']}")
        )

    builder.row(InlineKeyboardButton(text="➕ Добавить канал", callback_data="sub_add_channel"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="subscription_settings"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "sub_noop")
async def sub_noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("sub_toggle_ch_"))
async def toggle_channel(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    channel_db_id = int(callback.data.split("_")[3])
    await db.toggle_required_channel(channel_db_id)

    channels = await db.get_required_channels()
    ch = next((c for c in channels if c['id'] == channel_db_id), None)
    if ch:
        is_on = ch.get('is_active', 1) not in (0, False)
        status = "включён ✅" if is_on else "выключен ❌"
        await callback.answer(f"{ch['channel_name']} {status}!")
    else:
        await callback.answer("Готово!")

    await list_channels(callback)


# ============= УДАЛИТЬ КАНАЛ =============

@router.callback_query(F.data.startswith("sub_remove_"))
async def remove_channel(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    channel_db_id = int(callback.data.split("_")[2])
    await db.remove_required_channel(channel_db_id)
    await callback.answer("✅ Канал удалён!")

    channels = await db.get_required_channels()
    if not channels:
        await db.set_setting('subscription_enabled', '0')

    await list_channels(callback)


# ============= ДОБАВИТЬ КАНАЛ =============

@router.callback_query(F.data == "sub_add_channel")
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="subscription_settings"))

    text = (
        "➕ <b>Добавление канала</b>\n\n"
        "Шаг 1/3: Введи ID канала\n\n"
        "Как получить ID:\n"
        "1. Добавь @userinfobot в канал\n"
        "2. Перешли любое сообщение из канала боту\n"
        "3. Скопируй Chat ID\n\n"
        "Пример: <code>-1001234567890</code>"
    )

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())

    await state.set_state(AddChannelStates.waiting_for_channel_id)
    await callback.answer()


@router.message(AddChannelStates.waiting_for_channel_id)
async def process_channel_id(message: Message, state: FSMContext):
    channel_id = message.text.strip()

    if not (channel_id.startswith('-100') and channel_id[1:].isdigit()):
        await message.answer(
            "❌ Неверный формат ID.\n\n"
            "ID должен начинаться с <code>-100</code>\n"
            "Пример: <code>-1001234567890</code>"
        )
        return

    await state.update_data(channel_id=channel_id)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="subscription_settings"))

    await message.answer(
        f"✅ ID: <code>{channel_id}</code>\n\n"
        "Шаг 2/3: Введи ссылку на канал\n\n"
        "Пример: <code>https://t.me/your_channel</code>",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AddChannelStates.waiting_for_channel_url)


@router.message(AddChannelStates.waiting_for_channel_url)
async def process_channel_url(message: Message, state: FSMContext):
    url = message.text.strip()

    if not url.startswith('https://t.me/'):
        await message.answer(
            "❌ Неверный формат ссылки.\n\n"
            "Ссылка должна начинаться с <code>https://t.me/</code>"
        )
        return

    await state.update_data(channel_url=url)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="subscription_settings"))

    await message.answer(
        f"✅ Ссылка: {url}\n\n"
        "Шаг 3/3: Введи название канала\n\n"
        "Пример: <code>Тачки Симферополя</code>",
        reply_markup=builder.as_markup()
    )
    await state.set_state(AddChannelStates.waiting_for_channel_name)


@router.message(AddChannelStates.waiting_for_channel_name)
async def process_channel_name(message: Message, state: FSMContext, bot: Bot):
    name = message.text.strip()

    if len(name) < 2 or len(name) > 50:
        await message.answer("❌ Название должно быть от 2 до 50 символов.")
        return

    data = await state.get_data()
    channel_id = data['channel_id']
    channel_url = data['channel_url']

    # Проверяем что бот есть в канале
    try:
        bot_me = await bot.get_me()
        bot_member = await bot.get_chat_member(channel_id, bot_me.id)
        if bot_member.status not in ['administrator', 'creator']:
            await message.answer(
                "⚠️ <b>Внимание!</b>\n\n"
                "Бот не является администратором этого канала.\n"
                "Добавь бота как администратора, иначе проверка не будет работать!\n\n"
                "Канал всё равно добавлен."
            )
    except:
        await message.answer(
            "⚠️ <b>Внимание!</b>\n\n"
            "Не удалось проверить доступ бота к каналу.\n"
            "Убедись что бот добавлен в канал как администратор!"
        )

    result = await db.add_required_channel(channel_id, channel_url, name)
    await state.clear()

    if result:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="📋 Список каналов", callback_data="sub_list_channels"))
        builder.row(InlineKeyboardButton(text="🔙 К настройкам", callback_data="subscription_settings"))
        await message.answer(
            f"✅ <b>Канал добавлен!</b>\n\n"
            f"📢 {name}\n"
            f"🆔 <code>{channel_id}</code>\n"
            f"🔗 {channel_url}",
            reply_markup=builder.as_markup()
        )
    else:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="subscription_settings"))
        await message.answer("❌ Этот канал уже добавлен.", reply_markup=builder.as_markup())


# ============= ИНСТРУКЦИЯ =============

@router.callback_query(F.data == "sub_instruction")
async def show_instruction(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    text = (
        "📖 <b>Инструкция по настройке подписки</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Шаг 1: Добавь бота в канал</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "1. Открой свой канал\n"
        "2. Управление каналом → Администраторы\n"
        "3. Добавить администратора → найди бота\n"
        "4. Выдай права: минимум <b>Добавление участников</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Шаг 2: Получи ID канала</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "• Перешли сообщение из канала боту @userinfobot\n"
        "• Скопируй Chat ID (начинается с -100)\n\n"
        "Пример: <code>-1001234567890</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Шаг 3: Добавь канал в бота</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "• Нажми «➕ Добавить канал»\n"
        "• Введи ID, ссылку и название\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "<b>Шаг 4: Включи проверку</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "• Нажми «🟢 Включить»\n\n"
        "⚠️ Бот должен быть администратором канала!"
    )

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="subscription_settings"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ============= ПРОВЕРКА ПОДПИСКИ ПОЛЬЗОВАТЕЛЕМ =============

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, bot: Bot):
    enabled_str = await db.get_setting('subscription_enabled') or '0'
    if enabled_str != '1':
        await callback.answer()
        return

    channels = await db.get_required_channels()
    not_subscribed = await check_all_subscriptions(bot, callback.from_user.id, channels)

    if not_subscribed:
        text, keyboard = build_subscribe_message(not_subscribed)
        await callback.answer("❌ Ты ещё не подписался на все каналы!", show_alert=True)
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except:
            pass
    else:
        await callback.answer("✅ Отлично! Добро пожаловать!")
        try:
            await callback.message.delete()
        except:
            pass

        from keyboards import main_menu_kb
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        bot_name = await db.get_setting('bot_name') or 'JDM Cars Bot'
        welcome_text = await db.get_setting('welcome_text') or f"🚗 <b>{bot_name}</b>\n\nВыбери действие из меню:"

        keyboard = main_menu_kb()
        if await is_admin(callback.from_user.id):
            builder = InlineKeyboardBuilder()
            for row in keyboard.inline_keyboard:
                builder.row(*row)
            builder.row(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel"))
            keyboard = builder.as_markup()

        welcome_photo = await db.get_setting('welcome_photo')
        if welcome_photo:
            await callback.message.answer_photo(photo=welcome_photo, caption=welcome_text, reply_markup=keyboard)
        else:
            await callback.message.answer(welcome_text, reply_markup=keyboard)
