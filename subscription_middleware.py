import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from subscription_check import check_all_subscriptions, build_subscribe_message

logger = logging.getLogger(__name__)

# Callback data разрешённые без подписки
ALLOWED_CALLBACKS = {'check_subscription'}


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable,
        event,
        data: Dict[str, Any]
    ) -> Any:
        bot = data.get('bot')
        if not bot:
            return await handler(event, data)

        user_id = None
        is_callback = False
        callback_data_val = None

        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
            is_callback = True
            callback_data_val = event.data

        if not user_id:
            return await handler(event, data)

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

            # Разрешённые callback без подписки
            if is_callback and callback_data_val in ALLOWED_CALLBACKS:
                return await handler(event, data)

            # Проверяем подписку
            channels = await db.get_required_channels()
            if not channels:
                return await handler(event, data)

            not_subscribed = await check_all_subscriptions(bot, user_id, channels)
            logger.info(f"Middleware check user {user_id}: not_subscribed={len(not_subscribed)}")

            if not_subscribed:
                text, keyboard = build_subscribe_message(not_subscribed)

                if is_callback:
                    try:
                        await event.answer("❌ Необходима подписка!", show_alert=True)
                    except:
                        pass
                    try:
                        await event.message.edit_text(text, reply_markup=keyboard)
                    except:
                        try:
                            await event.message.delete()
                        except:
                            pass
                        await event.message.answer(text, reply_markup=keyboard)
                else:
                    await event.answer(text, reply_markup=keyboard)

                return  # Блокируем

        except Exception as e:
            logger.error(f"Subscription middleware error: {e}", exc_info=True)

        return await handler(event, data)
