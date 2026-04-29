from aiogram import F, Router, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio

from db_adapter import db
from utils import is_admin

router = Router()


class BroadcastState(StatesGroup):
    waiting_for_message = State()


# ============= НАСТРОЙКИ ПОЛЬЗОВАТЕЛЯ =============

def user_settings_kb(show_username: bool, notify_cars: bool) -> object:
    builder = InlineKeyboardBuilder()

    status_nick = "✅ Показывать" if show_username else "❌ Скрыт"
    builder.row(InlineKeyboardButton(
        text=f"👤 Мой ник в карточках: {status_nick}",
        callback_data="toggle_show_username"
    ))

    status_notify = "🔔 Включены" if notify_cars else "🔕 Выключены"
    builder.row(InlineKeyboardButton(
        text=f"Уведомления о новых машинах: {status_notify}",
        callback_data="toggle_notify_cars"
    ))

    builder.row(InlineKeyboardButton(
        text="🔙 Назад",
        callback_data="more_menu"
    ))
    return builder.as_markup()


@router.callback_query(F.data == "user_settings")
async def user_settings(callback: CallbackQuery):
    show = await db.get_show_username(callback.from_user.id)
    notify = await db.get_notify_new_cars(callback.from_user.id)

    text = (
        "⚙️ <b>Мои настройки</b>\n\n"
        "👤 <b>Ник в карточках</b>\n"
        "Показывать твой ник как автора фото при предложении машины.\n\n"
        "🔔 <b>Уведомления о новых машинах</b>\n"
        "Получать уведомление когда в каталог добавляется новая машина."
    )

    try:
        await callback.message.edit_text(text, reply_markup=user_settings_kb(show, notify))
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=user_settings_kb(show, notify))
    await callback.answer()


@router.callback_query(F.data == "toggle_show_username")
async def toggle_show_username(callback: CallbackQuery):
    current = await db.get_show_username(callback.from_user.id)
    new_val = not current
    await db.set_show_username(callback.from_user.id, new_val)

    if new_val:
        await callback.answer("✅ Ник теперь отображается в карточках!")
    else:
        await callback.answer("❌ Ник скрыт!")

    await user_settings(callback)


@router.callback_query(F.data == "toggle_notify_cars")
async def toggle_notify_cars(callback: CallbackQuery):
    current = await db.get_notify_new_cars(callback.from_user.id)
    new_val = not current
    await db.set_notify_new_cars(callback.from_user.id, new_val)

    if new_val:
        await callback.answer("🔔 Уведомления о новых машинах включены!")
    else:
        await callback.answer("🔕 Уведомления выключены!")

    await user_settings(callback)


# ============= РАССЫЛКА (только для админов) =============

@router.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    users = await db.get_all_users()

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_panel"))

    text = (
        "📢 <b>Рассылка сообщения</b>\n\n"
        f"Получателей: <b>{len(users)}</b> пользователей\n\n"
        "Отправь текст сообщения.\n"
        "Поддерживается HTML: <b>жирный</b>, <i>курсив</i>\n\n"
        "Можно также отправить фото с подписью."
    )

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=builder.as_markup())

    await state.set_state(BroadcastState.waiting_for_message)
    await callback.answer()


@router.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return

    await state.clear()

    # Регистрируем отправителя
    await db.register_user(
        message.from_user.id,
        message.from_user.username or '',
        message.from_user.first_name or ''
    )

    users = await db.get_all_users()

    if not users:
        await message.answer(
            "⚠️ В базе нет пользователей.\n\n"
            "Пользователи появляются после того как нажмут /start в боте."
        )
        return

    sent = 0
    failed = 0

    status_msg = await message.answer(
        f"📤 Начинаю рассылку...\n"
        f"Пользователей в базе: <b>{len(users)}</b>"
    )

    for user in users:
        try:
            if message.photo:
                await bot.send_photo(
                    chat_id=user['user_id'],
                    photo=message.photo[-1].file_id,
                    caption=message.caption or ''
                )
            elif message.text:
                await bot.send_message(
                    chat_id=user['user_id'],
                    text=message.text
                )
            sent += 1
        except Exception as e:
            failed += 1
            import logging
            logging.getLogger(__name__).warning(f"Broadcast failed for {user['user_id']}: {e}")

        await asyncio.sleep(0.05)

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel"))

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}\n\n"
        f"<i>Не доставлено — пользователи заблокировали бота</i>",
        reply_markup=builder.as_markup()
    )
