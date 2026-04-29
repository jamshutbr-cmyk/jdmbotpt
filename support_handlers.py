from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db_adapter import db
from states import SupportStates, AdminSupportStates
from utils import is_admin
from config import ADMIN_IDS

router = Router()

TICKET_STATUS = {
    'open': '🟡 Открыт',
    'in_progress': '🔵 В работе',
    'closed': '🔴 Закрыт'
}


def back_to_support_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 К поддержке", callback_data="support_menu"))
    return builder.as_markup()


def ticket_user_kb(ticket_id: int, status: str):
    builder = InlineKeyboardBuilder()
    if status != 'closed':
        builder.row(InlineKeyboardButton(text="✉️ Написать", callback_data=f"ticket_reply_{ticket_id}"))
        builder.row(InlineKeyboardButton(text="❌ Закрыть тикет", callback_data=f"ticket_close_user_{ticket_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Мои тикеты", callback_data="my_tickets"))
    return builder.as_markup()


def ticket_admin_kb(ticket_id: int, status: str):
    builder = InlineKeyboardBuilder()
    if status != 'closed':
        builder.row(InlineKeyboardButton(text="✉️ Ответить", callback_data=f"admin_ticket_reply_{ticket_id}"))
        if status == 'open':
            builder.row(InlineKeyboardButton(text="🔵 Взять в работу", callback_data=f"ticket_inprogress_{ticket_id}"))
        builder.row(InlineKeyboardButton(text="✅ Закрыть тикет", callback_data=f"ticket_close_admin_{ticket_id}"))
    builder.row(InlineKeyboardButton(text="🔙 Все тикеты", callback_data="admin_tickets"))
    return builder.as_markup()


def format_ticket_info(ticket: dict, messages: list) -> str:
    status = TICKET_STATUS.get(ticket['status'], ticket['status'])
    text = (
        f"🎫 <b>Тикет #{ticket['id']}</b>\n"
        f"📌 Тема: {ticket['subject']}\n"
        f"📊 Статус: {status}\n"
        f"📅 Создан: {str(ticket['created_at'])[:16]}\n"
    )
    if ticket.get('close_reason'):
        text += f"💬 Причина закрытия: {ticket['close_reason']}\n"
    
    if messages:
        text += "\n─────────────────\n💬 <b>Переписка:</b>\n\n"
        for msg in messages[-10:]:  # последние 10 сообщений
            prefix = "👨‍💼 Поддержка" if msg['is_admin'] else "👤 Вы"
            time = str(msg['created_at'])[:16]
            text += f"<b>{prefix}</b> [{time}]:\n{msg['text']}\n\n"
    
    return text


# ============= МЕНЮ ПОДДЕРЖКИ =============

@router.callback_query(F.data == "support_menu")
async def support_menu(callback: CallbackQuery):
    text = (
        "🆘 <b>Техническая поддержка</b>\n\n"
        "Здесь ты можешь создать тикет и получить помощь.\n\n"
        "Мы отвечаем в течение 24 часов."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Создать тикет", callback_data="create_ticket"))
    builder.row(InlineKeyboardButton(text="📋 Мои тикеты", callback_data="my_tickets"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


# ============= СОЗДАНИЕ ТИКЕТА =============

@router.callback_query(F.data == "create_ticket")
async def create_ticket_start(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="support_menu"))
    
    text = (
        "➕ <b>Создание тикета</b>\n\n"
        "Шаг 1/2: Введи тему обращения\n\n"
        "Например: 'Не работает поиск' или 'Вопрос по боту'"
    )
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    
    await state.set_state(SupportStates.waiting_for_subject)
    await callback.answer()


@router.message(SupportStates.waiting_for_subject)
async def process_ticket_subject(message: Message, state: FSMContext):
    subject = message.text.strip()
    if len(subject) < 3:
        await message.answer("❌ Тема слишком короткая. Минимум 3 символа.")
        return
    if len(subject) > 100:
        await message.answer("❌ Тема слишком длинная. Максимум 100 символов.")
        return
    
    await state.update_data(subject=subject)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="support_menu"))
    
    await message.answer(
        f"✅ Тема: <b>{subject}</b>\n\n"
        "Шаг 2/2: Опиши свою проблему подробно:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(SupportStates.waiting_for_message)


@router.message(SupportStates.waiting_for_message)
async def process_ticket_message(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    if len(text) < 10:
        await message.answer("❌ Сообщение слишком короткое. Минимум 10 символов.")
        return
    
    data = await state.get_data()
    subject = data['subject']
    
    username = message.from_user.username or message.from_user.first_name
    
    # Создаём тикет
    ticket_id = await db.create_ticket(message.from_user.id, username, subject)
    
    # Добавляем первое сообщение
    await db.add_ticket_message(ticket_id, message.from_user.id, text, is_admin=False)
    
    await state.clear()
    
    # Уведомляем пользователя
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Мои тикеты", callback_data="my_tickets"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))
    
    await message.answer(
        f"✅ <b>Тикет #{ticket_id} создан!</b>\n\n"
        f"📌 Тема: {subject}\n\n"
        f"Мы ответим в ближайшее время. Ты получишь уведомление.",
        reply_markup=builder.as_markup()
    )
    
    # Уведомляем всех админов
    for admin_id in ADMIN_IDS:
        try:
            admin_builder = InlineKeyboardBuilder()
            admin_builder.row(InlineKeyboardButton(
                text=f"📂 Открыть тикет #{ticket_id}",
                callback_data=f"admin_view_ticket_{ticket_id}"
            ))
            await bot.send_message(
                admin_id,
                f"🔔 <b>Новый тикет #{ticket_id}!</b>\n\n"
                f"👤 От: @{username}\n"
                f"📌 Тема: {subject}\n\n"
                f"💬 {text[:200]}{'...' if len(text) > 200 else ''}",
                reply_markup=admin_builder.as_markup()
            )
        except:
            pass


# ============= МОИ ТИКЕТЫ =============

@router.callback_query(F.data == "my_tickets")
async def my_tickets(callback: CallbackQuery):
    tickets = await db.get_user_tickets(callback.from_user.id)
    
    if not tickets:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="➕ Создать тикет", callback_data="create_ticket"))
        builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="support_menu"))
        
        try:
            await callback.message.edit_text(
                "📋 <b>Мои тикеты</b>\n\nУ тебя пока нет тикетов.",
                reply_markup=builder.as_markup()
            )
        except:
            await callback.message.delete()
            await callback.message.answer(
                "📋 <b>Мои тикеты</b>\n\nУ тебя пока нет тикетов.",
                reply_markup=builder.as_markup()
            )
        await callback.answer()
        return
    
    builder = InlineKeyboardBuilder()
    for ticket in tickets[:10]:
        status_emoji = {'open': '🟡', 'in_progress': '🔵', 'closed': '🔴'}.get(ticket['status'], '⚪')
        builder.row(InlineKeyboardButton(
            text=f"{status_emoji} #{ticket['id']} — {ticket['subject'][:30]}",
            callback_data=f"view_ticket_{ticket['id']}"
        ))
    
    builder.row(InlineKeyboardButton(text="➕ Создать тикет", callback_data="create_ticket"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="support_menu"))
    
    text = f"📋 <b>Мои тикеты</b>\n\nВсего: {len(tickets)}\n\n🟡 открыт  🔵 в работе  🔴 закрыт"
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("view_ticket_"))
async def view_ticket(callback: CallbackQuery):
    ticket_id = int(callback.data.split("_")[2])
    ticket = await db.get_ticket(ticket_id)
    
    if not ticket or ticket['user_id'] != callback.from_user.id:
        await callback.answer("❌ Тикет не найден", show_alert=True)
        return
    
    messages = await db.get_ticket_messages(ticket_id)
    text = format_ticket_info(ticket, messages)
    
    try:
        await callback.message.edit_text(text, reply_markup=ticket_user_kb(ticket_id, ticket['status']))
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=ticket_user_kb(ticket_id, ticket['status']))
    await callback.answer()


# ============= ОТВЕТ ПОЛЬЗОВАТЕЛЯ =============

@router.callback_query(F.data.startswith("ticket_reply_"))
async def ticket_reply_start(callback: CallbackQuery, state: FSMContext):
    ticket_id = int(callback.data.split("_")[2])
    ticket = await db.get_ticket(ticket_id)
    
    if not ticket or ticket['user_id'] != callback.from_user.id:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    if ticket['status'] == 'closed':
        await callback.answer("❌ Тикет закрыт", show_alert=True)
        return
    
    await state.update_data(reply_ticket_id=ticket_id)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_ticket_{ticket_id}"))
    
    try:
        await callback.message.edit_text(
            f"✉️ <b>Ответ в тикет #{ticket_id}</b>\n\nНапиши своё сообщение:",
            reply_markup=builder.as_markup()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            f"✉️ <b>Ответ в тикет #{ticket_id}</b>\n\nНапиши своё сообщение:",
            reply_markup=builder.as_markup()
        )
    
    await state.set_state(SupportStates.waiting_for_reply)
    await callback.answer()


@router.message(SupportStates.waiting_for_reply)
async def process_user_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ticket_id = data['reply_ticket_id']
    
    await db.add_ticket_message(ticket_id, message.from_user.id, message.text, is_admin=False)
    await state.clear()
    
    username = message.from_user.username or message.from_user.first_name
    
    # Уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            builder = InlineKeyboardBuilder()
            builder.row(InlineKeyboardButton(
                text=f"📂 Открыть тикет #{ticket_id}",
                callback_data=f"admin_view_ticket_{ticket_id}"
            ))
            await bot.send_message(
                admin_id,
                f"💬 <b>Новое сообщение в тикете #{ticket_id}</b>\n\n"
                f"👤 От: @{username}\n\n"
                f"{message.text[:300]}{'...' if len(message.text) > 300 else ''}",
                reply_markup=builder.as_markup()
            )
        except:
            pass
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📂 Открыть тикет", callback_data=f"view_ticket_{ticket_id}"))
    
    await message.answer(
        f"✅ Сообщение отправлено в тикет #{ticket_id}!",
        reply_markup=builder.as_markup()
    )


# ============= ЗАКРЫТИЕ ТИКЕТА ПОЛЬЗОВАТЕЛЕМ =============

@router.callback_query(F.data.startswith("ticket_close_user_"))
async def close_ticket_user(callback: CallbackQuery, bot: Bot):
    ticket_id = int(callback.data.split("_")[3])
    ticket = await db.get_ticket(ticket_id)
    
    if not ticket or ticket['user_id'] != callback.from_user.id:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await db.update_ticket_status(ticket_id, 'closed', 'Закрыт пользователем')
    
    # Уведомляем админов
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🔴 <b>Тикет #{ticket_id} закрыт пользователем</b>"
            )
        except:
            pass
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Мои тикеты", callback_data="my_tickets"))
    
    try:
        await callback.message.edit_text(
            f"✅ <b>Тикет #{ticket_id} закрыт.</b>\n\nСпасибо за обращение!",
            reply_markup=builder.as_markup()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            f"✅ <b>Тикет #{ticket_id} закрыт.</b>\n\nСпасибо за обращение!",
            reply_markup=builder.as_markup()
        )
    await callback.answer()


# ============= АДМИН: ПРОСМОТР ТИКЕТОВ =============

@router.callback_query(F.data == "admin_tickets")
async def admin_tickets(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    open_tickets = await db.get_all_tickets('open')
    inprog_tickets = await db.get_all_tickets('in_progress')
    closed_tickets = await db.get_all_tickets('closed')
    
    builder = InlineKeyboardBuilder()
    
    if open_tickets or inprog_tickets:
        builder.row(InlineKeyboardButton(
            text=f"🟡 Открытые ({len(open_tickets)})",
            callback_data="admin_tickets_open"
        ))
        builder.row(InlineKeyboardButton(
            text=f"🔵 В работе ({len(inprog_tickets)})",
            callback_data="admin_tickets_inprog"
        ))
    
    builder.row(InlineKeyboardButton(
        text=f"🔴 Закрытые ({len(closed_tickets)})",
        callback_data="admin_tickets_closed"
    ))
    builder.row(InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel"))
    
    text = (
        f"🎫 <b>Тикеты поддержки</b>\n\n"
        f"🟡 Открытых: {len(open_tickets)}\n"
        f"🔵 В работе: {len(inprog_tickets)}\n"
        f"🔴 Закрытых: {len(closed_tickets)}"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_tickets_"))
async def admin_tickets_list(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    status_map = {'open': 'open', 'inprog': 'in_progress', 'closed': 'closed'}
    key = callback.data.split("_")[2]
    status = status_map.get(key)
    
    tickets = await db.get_all_tickets(status)
    
    if not tickets:
        await callback.answer("Нет тикетов", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    for ticket in tickets[:15]:
        status_emoji = {'open': '🟡', 'in_progress': '🔵', 'closed': '🔴'}.get(ticket['status'], '⚪')
        builder.row(InlineKeyboardButton(
            text=f"{status_emoji} #{ticket['id']} @{ticket['username']} — {ticket['subject'][:25]}",
            callback_data=f"admin_view_ticket_{ticket['id']}"
        ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_tickets"))
    
    try:
        await callback.message.edit_text(
            f"🎫 Тикеты ({len(tickets)}):",
            reply_markup=builder.as_markup()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(f"🎫 Тикеты ({len(tickets)}):", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("admin_view_ticket_"))
async def admin_view_ticket(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    ticket_id = int(callback.data.split("_")[3])
    ticket = await db.get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("❌ Тикет не найден", show_alert=True)
        return
    
    messages = await db.get_ticket_messages(ticket_id)
    text = f"👤 Пользователь: @{ticket['username']} (ID: {ticket['user_id']})\n\n"
    text += format_ticket_info(ticket, messages)
    
    if len(text) > 4096:
        text = text[:4090] + "..."
    
    try:
        await callback.message.edit_text(text, reply_markup=ticket_admin_kb(ticket_id, ticket['status']))
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=ticket_admin_kb(ticket_id, ticket['status']))
    await callback.answer()


# ============= АДМИН: ОТВЕТ В ТИКЕТ =============

@router.callback_query(F.data.startswith("admin_ticket_reply_"))
async def admin_ticket_reply_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    ticket_id = int(callback.data.split("_")[3])
    await state.update_data(admin_reply_ticket_id=ticket_id)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_view_ticket_{ticket_id}"))
    
    try:
        await callback.message.edit_text(
            f"✉️ <b>Ответ в тикет #{ticket_id}</b>\n\nНапиши ответ пользователю:",
            reply_markup=builder.as_markup()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            f"✉️ <b>Ответ в тикет #{ticket_id}</b>\n\nНапиши ответ пользователю:",
            reply_markup=builder.as_markup()
        )
    
    await state.set_state(AdminSupportStates.waiting_for_reply)
    await callback.answer()


@router.message(AdminSupportStates.waiting_for_reply)
async def process_admin_reply(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ticket_id = data['admin_reply_ticket_id']
    ticket = await db.get_ticket(ticket_id)
    
    await db.add_ticket_message(ticket_id, message.from_user.id, message.text, is_admin=True)
    
    # Переводим в статус "в работе" если был открыт
    if ticket['status'] == 'open':
        await db.update_ticket_status(ticket_id, 'in_progress')
    
    await state.clear()
    
    # Уведомляем пользователя
    try:
        user_builder = InlineKeyboardBuilder()
        user_builder.row(InlineKeyboardButton(
            text=f"📂 Открыть тикет #{ticket_id}",
            callback_data=f"view_ticket_{ticket_id}"
        ))
        await bot.send_message(
            ticket['user_id'],
            f"💬 <b>Ответ по тикету #{ticket_id}</b>\n\n"
            f"👨‍💼 Поддержка:\n{message.text}",
            reply_markup=user_builder.as_markup()
        )
    except:
        pass
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📂 Открыть тикет", callback_data=f"admin_view_ticket_{ticket_id}"))
    
    await message.answer(
        f"✅ Ответ отправлен в тикет #{ticket_id}!",
        reply_markup=builder.as_markup()
    )


# ============= АДМИН: ВЗЯТЬ В РАБОТУ =============

@router.callback_query(F.data.startswith("ticket_inprogress_"))
async def ticket_inprogress(callback: CallbackQuery, bot: Bot):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    ticket_id = int(callback.data.split("_")[2])
    ticket = await db.get_ticket(ticket_id)
    
    await db.update_ticket_status(ticket_id, 'in_progress')
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            ticket['user_id'],
            f"🔵 <b>Тикет #{ticket_id} взят в работу!</b>\n\nМы занимаемся вашим вопросом."
        )
    except:
        pass
    
    await callback.answer("✅ Тикет взят в работу!")
    
    # Обновляем сообщение
    messages = await db.get_ticket_messages(ticket_id)
    ticket = await db.get_ticket(ticket_id)
    text = f"👤 Пользователь: @{ticket['username']}\n\n" + format_ticket_info(ticket, messages)
    
    try:
        await callback.message.edit_text(text, reply_markup=ticket_admin_kb(ticket_id, ticket['status']))
    except:
        pass


# ============= АДМИН: ЗАКРЫТИЕ ТИКЕТА =============

@router.callback_query(F.data.startswith("ticket_close_admin_"))
async def close_ticket_admin_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    ticket_id = int(callback.data.split("_")[3])
    await state.update_data(close_ticket_id=ticket_id)
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_view_ticket_{ticket_id}"))
    
    try:
        await callback.message.edit_text(
            f"✅ <b>Закрытие тикета #{ticket_id}</b>\n\nНапиши причину закрытия:",
            reply_markup=builder.as_markup()
        )
    except:
        await callback.message.delete()
        await callback.message.answer(
            f"✅ <b>Закрытие тикета #{ticket_id}</b>\n\nНапиши причину закрытия:",
            reply_markup=builder.as_markup()
        )
    
    await state.set_state(SupportStates.waiting_for_close_reason)
    await callback.answer()


@router.message(SupportStates.waiting_for_close_reason)
async def process_close_reason(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ticket_id = data['close_ticket_id']
    ticket = await db.get_ticket(ticket_id)
    
    reason = message.text.strip()
    await db.update_ticket_status(ticket_id, 'closed', reason)
    await state.clear()
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            ticket['user_id'],
            f"🔴 <b>Тикет #{ticket_id} закрыт</b>\n\n"
            f"💬 Причина: {reason}\n\n"
            f"Спасибо за обращение! Если вопрос не решён — создай новый тикет."
        )
    except:
        pass
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🎫 Все тикеты", callback_data="admin_tickets"))
    
    await message.answer(
        f"✅ <b>Тикет #{ticket_id} закрыт!</b>\n\nПричина: {reason}",
        reply_markup=builder.as_markup()
    )
