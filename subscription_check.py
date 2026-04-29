import logging
import time
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

logger = logging.getLogger(__name__)

# Кэш результатов проверки: {(user_id, channel_id): (result, timestamp)}
_cache: dict = {}
CACHE_TTL = 30  # секунд


async def is_subscribed(bot: Bot, user_id: int, channel_id: str) -> bool:
    """Проверить подписан ли пользователь на канал (с кэшем)"""
    cache_key = (user_id, channel_id)
    now = time.time()

    # Проверяем кэш
    if cache_key in _cache:
        result, ts = _cache[cache_key]
        if now - ts < CACHE_TTL:
            logger.info(f"Cache hit: user {user_id} in {channel_id} = {result}")
            return result

    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        logger.info(f"User {user_id} in channel {channel_id}: status={member.status}")
        result = member.status not in [
            ChatMemberStatus.LEFT,
            ChatMemberStatus.KICKED,
            ChatMemberStatus.BANNED,
        ]
        # Сохраняем в кэш только если результат True, или кэша нет
        if result or cache_key not in _cache:
            _cache[cache_key] = (result, now)
        return result

    except Exception as e:
        err = str(e).upper()
        logger.warning(f"get_chat_member error for user {user_id} in {channel_id}: {e}")

        if 'CHAT_NOT_FOUND' in err or 'BOT IS NOT A MEMBER' in err:
            logger.error(f"Bot is not in channel {channel_id}!")
            _cache[cache_key] = (True, now)
            return True

        # Если в кэше есть результат True — доверяем ему
        if cache_key in _cache:
            old_result, _ = _cache[cache_key]
            logger.info(f"Using cache for user {user_id}: {old_result}")
            return old_result

        _cache[cache_key] = (False, now)
        return False


def invalidate_cache(user_id: int = None, channel_id: str = None):
    """Сбросить кэш для пользователя или канала"""
    global _cache
    if user_id is None and channel_id is None:
        _cache = {}
        return
    keys_to_delete = [
        k for k in _cache
        if (user_id and k[0] == user_id) or (channel_id and k[1] == channel_id)
    ]
    for k in keys_to_delete:
        del _cache[k]


async def check_all_subscriptions(bot: Bot, user_id: int, channels: list) -> list:
    """
    Проверить подписку на все АКТИВНЫЕ каналы.
    Возвращает список каналов на которые НЕ подписан.
    """
    not_subscribed = []
    seen_channel_ids = set()  # защита от дубликатов

    for channel in channels:
        is_active = channel.get('is_active', 1)
        if is_active in (0, False):
            continue

        channel_id = channel['channel_id']
        if channel_id in seen_channel_ids:
            continue  # пропускаем дубликат
        seen_channel_ids.add(channel_id)

        subscribed = await is_subscribed(bot, user_id, channel_id)
        if not subscribed:
            not_subscribed.append(channel)

    return not_subscribed


def build_subscribe_message(not_subscribed: list) -> tuple:
    """Создать сообщение и клавиатуру для подписки"""
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
