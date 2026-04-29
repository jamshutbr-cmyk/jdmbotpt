"""
Middleware для проверки подписки при каждом действии пользователя.
"""
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update

from subscription_check import check_all_subscriptions, build_subscribe_message

logger = logging.getLogger(__name__)

# Callback data которые разрешены без подписки
ALLOWED_CALLBACKS = {
    'check_subscription',
    'back_to_main',
}

# Команды которые разрешены без подписки
ALLOWED_COMMANDS = {'/start', '/help'}


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        bot = data.get('bot')
        if not bot:
            return await handler(event, data)

        # Определяем пользователя и тип события
        user_id = None
        is_callback = False
        callback_data = None
        is_command = False
        command_text = None

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
            if event.text and event.text.startswith('/'):
                is_command = True
                command_text = event.text.split()[0]
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            is_callback = True
            callback_data = event.data

        if not user_id:
            return await handler(event, data)

        # Проверяем нужна ли проверка подписки
        try:
            from db_adapter import db
            from utils import is_admin

            # Админов не проверяем
            if await is_admin(user_id):
                return await handler(event, data)

            # Проверяем включена ли система
            enabled_str = await db.get_setting('subscription_enabled') or '0'
            if enabled_str != '1':
                return await handler(event, data)

            # Разрешённые действия без подписки
            if is_callback and callback_data in ALLOWED_CALLBACKS:
                return await handler(event, data)

            if is_command and command_text in ALLOWED_COMMANDS:
                return await handler(event, data)

            # Проверяем подписку
            channels = await db.get_required_channels()
            if not channels:
                return await handler(event, data)

            not_subscribed = await check_all_subscriptions(bot, user_id, channels)

            if not_subscribed:
                text, keyboard = build_subscribe_message(not_subscribed)

                if is_callback:
                    try:
                        await event.answer("❌ Необходима подписка на каналы!", show_alert=True)
                        await event.message.edit_text(text, reply_markup=keyboard)
                    except:
                        try:
                            await event.message.delete()
                        except:
                            pass
                        await event.message.answer(text, reply_markup=keyboard)
                elif isinstance(event, Message):
                    await event.answer(text, reply_markup=keyboard)

                return  # Блокируем обработку

        except Exception as e:
            logger.error(f"Subscription middleware error: {e}")

        return await handler(event, data)
