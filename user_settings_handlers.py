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

def user_settings_kb(show_username: bool) -> object:
    builder = InlineKeyboardBuilder()
    status = "✅ Показывать" if show_username else "❌ Скрыть"
    builder.row(InlineKeyboardButton(
        text=f"👤 Мой ник в карточках: {status}",
        callback_data="toggle_show_username"
    ))
    builder.row(InlineKeyboardButton(
        text="🔙 Главное меню",
        callback_data="back_to_main"
    ))
    return builder.as_markup()


@router.callback_query(F.data == "user_settings")
async def user_settings(callback: CallbackQuery):
    show = await db.get_show_username(callback.from_user.id)

    text = (
        "⚙️ <b>Мои настройки</b>\n\n"
        "👤 <b>Отображение ника</b>\n"
        "Когда ты предлагаешь машину — твой ник может отображаться "
        "в карточке как автор фото.\n\n"
        f"Текущий статус: {'✅ Показывается' if show else '❌ Скрыт'}"
    )

    try:
        await callback.message.edit_text(text, reply_markup=user_settings_kb(show))
    except:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=user_settings_kb(show))
    await callback.answer()


@router.callback_query(F.data == "toggle_show_username")
async def toggle_show_username(callback: CallbackQuery):
    current = await db.get_show_username(callback.from_user.id)
    new_val = not current
    await db.set_show_username(callback.from_user.id, new_val)

    if new_val:
        await callback.answer("✅ Ник теперь отображается в карточках!")
    else:
        await callback.answer("❌ Ник скрыт — не будет отображаться!")

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

    users = await db.get_all_users()

    # Регистрируем отправителя если нет
    await db.register_user(
        message.from_user.id,
        message.from_user.username or '',
        message.from_user.first_name or ''
    )

    sent = 0
    failed = 0

    status_msg = await message.answer(f"📤 Начинаю рассылку для {len(users)} пользователей...")

    for user in users:
        try:
            if message.photo:
                # Фото с подписью
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
            await asyncio.sleep(0.05)  # защита от флуда
        except Exception as e:
            failed += 1

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel"))

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}",
        reply_markup=builder.as_markup()
    )
