import logging
import time
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

logger = logging.getLogger(__name__)

# {(user_id, channel_id): (result, timestamp)}
_cache = {}
CACHE_TTL = 30  # секунд


def _get_cache(user_id: int, channel_id: str):
    key = (user_id, channel_id)
    if key in _cache:
        result, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            logger.info(f"[CACHE HIT] {user_id} -> {channel_id} = {result}")
            return result
    return None


def _set_cache(user_id: int, channel_id: str, result: bool):
    _cache[(user_id, channel_id)] = (result, time.time())


async def is_subscribed(bot: Bot, user_id: int, channel_id: str) -> bool:
    """Проверка подписки (без ложных срабатываний)"""
    cached = _get_cache(user_id, channel_id)
    if cached is not None:
        return cached

    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        logger.info(f"[CHECK] user={user_id} channel={channel_id} status={member.status}")

        result = member.status in (
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR,
        )
        _set_cache(user_id, channel_id, result)
        return result

    except Exception as e:
        err = str(e).upper()
        logger.warning(f"[ERROR] get_chat_member: {e}")

        if "BOT IS NOT A MEMBER" in err or "CHAT_NOT_FOUND" in err:
            logger.error(f"[CRITICAL] Bot not in channel {channel_id}")
            return True  # пропускаем

        # НЕ кэшируем False при ошибке
        return False


def invalidate_cache(user_id: int = None, channel_id: str = None):
    """Сброс кэша"""
    global _cache
    if user_id is None and channel_id is None:
        _cache = {}
        return
    _cache = {
        k: v for k, v in _cache.items()
        if not (
            (user_id and k[0] == user_id) or
            (channel_id and k[1] == channel_id)
        )
    }


async def check_all_subscriptions(bot: Bot, user_id: int, channels: list) -> list:
    """Вернёт список каналов, на которые пользователь НЕ подписан"""
    not_subscribed = []
    seen = set()

    for channel in channels:
        if not channel.get("is_active", 1):
            continue

        channel_id = channel["channel_id"]
        if channel_id in seen:
            continue
        seen.add(channel_id)

        if not await is_subscribed(bot, user_id, channel_id):
            not_subscribed.append(channel)

    return not_subscribed


def build_subscribe_message(not_subscribed: list):
    """Сообщение + кнопки"""
    text = (
        "🔒 <b>Доступ ограничен</b>\n\n"
        "Подпишись на каналы ниже, чтобы пользоваться ботом:\n\n"
    )
    builder = InlineKeyboardBuilder()

    for i, channel in enumerate(not_subscribed, 1):
        text += f"{i}. <b>{channel['channel_name']}</b>\n"
        builder.row(InlineKeyboardButton(
            text=f"📢 {channel['channel_name']}",
            url=channel["channel_url"]
        ))

    text += "\nПосле подписки нажми кнопку ниже 👇"
    builder.row(InlineKeyboardButton(
        text="✅ Я подписался",
        callback_data="check_subscription"
    ))

    return text, builder.as_markup()
