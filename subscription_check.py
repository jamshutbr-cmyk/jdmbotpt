"""
Система проверки подписки на каналы.
Работает как middleware — перехватывает все апдейты и проверяет подписку.
"""
from aiogram import Bot
from aiogram.types import ChatMemberStatus
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton


async def is_subscribed(bot: Bot, user_id: int, channel_id: str) -> bool:
    """Проверить подписан ли пользователь на канал"""
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status not in [
            ChatMemberStatus.LEFT,
            ChatMemberStatus.KICKED,
            ChatMemberStatus.BANNED,
        ]
    except Exception:
        # Если бот не в канале или канал не найден — пропускаем
        return True


async def check_all_subscriptions(bot: Bot, user_id: int, channels: list) -> list:
    """
    Проверить подписку на все АКТИВНЫЕ каналы.
    Возвращает список каналов на которые НЕ подписан.
    """
    not_subscribed = []
    for channel in channels:
        if not channel.get('is_active', 1):  # пропускаем неактивные
            continue
        subscribed = await is_subscribed(bot, user_id, channel['channel_id'])
        if not subscribed:
            not_subscribed.append(channel)
    return not_subscribed


def build_subscribe_message(not_subscribed: list) -> tuple:
    """
    Создать сообщение одписки.и клавиатуру для п
    Возвращает (text, keyboard)
    """
    text = (
        "🔒 <b>Доступ ограничен</b>\n\n"
        "Для использования бота необходимо подписаться на наши каналы:\n\n"
    )

    builder = InlineKeyboardBuilder()

    for i, channel in enumerate(not_subscribed, 1):
        text += f"{i}. <b>{channel['channel_name']}</b>\n"
        builder.row(InlineKeyboardButton(
            text=f"📢 {channel['channel_name']}",
            url=channel['channel_url']
        ))

    text += "\nПосле подписки нажми кнопку ниже 👇"

    builder.row(InlineKeyboardButton(
        text="✅ Я подписался!",
        callback_data="check_subscription"
    ))

    return text, builder.as_markup()
