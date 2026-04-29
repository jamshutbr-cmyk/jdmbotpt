"""
Система проверки подписки на каналы.
"""
import logging
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

logger = logging.getLogger(__name__)


async def is_subscribed(bot: Bot, user_id: int, channel_id: str) -> bool:
    """Проверить подписан ли пользователь на канал"""
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        logger.info(f"User {user_id} in channel {channel_id}: status={member.status}")
        return member.status not in [
            ChatMemberStatus.LEFT,
            ChatMemberStatus.KICKED,
            ChatMemberStatus.BANNED,
        ]
    except Exception as e:
        err = str(e)
        logger.warning(f"Cannot check subscription for user {user_id} in {channel_id}: {err}")
        # Если пользователь забанен — точно не подписан
        if 'BANNED' in err or 'kicked' in err.lower():
            return False
        # Если бот не в канале или другая ошибка доступа — пропускаем проверку
        if 'bot is not a member' in err.lower() or 'chat not found' in err.lower():
            logger.error(f"Bot is not in channel {channel_id}! Add bot as admin.")
            return True  # пропускаем если бот не в канале
        return False


async def check_all_subscriptions(bot: Bot, user_id: int, channels: list) -> list:
    """
    Проверить подписку на все АКТИВНЫЕ каналы.
    Возвращает список каналов на которые НЕ подписан.
    """
    not_subscribed = []
    for channel in channels:
        # is_active может быть int (1/0) или bool (True/False) в зависимости от БД
        is_active = channel.get('is_active', 1)
        if is_active in (0, False):
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
