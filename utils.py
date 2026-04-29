from typing import Optional, Dict
from config import ADMIN_IDS, OWNER_ID

MAX_CAPTION_LENGTH = 1024


def is_owner(user_id: int) -> bool:
    """Проверка — владелец бота"""
    return user_id == OWNER_ID


def is_admin_static(user_id: int) -> bool:
    """Проверка по статичному списку из .env"""
    return user_id == OWNER_ID or user_id in ADMIN_IDS


async def is_admin(user_id: int) -> bool:
    """Проверка с учётом динамических админов из БД"""
    if user_id == OWNER_ID or user_id in ADMIN_IDS:
        return True
    # Проверяем в БД
    try:
        from db_adapter import db
        extra = await db.get_setting('extra_admins')
        if extra:
            extra_ids = [int(x.strip()) for x in extra.split(',') if x.strip()]
            return user_id in extra_ids
    except:
        pass
    return False


async def get_all_admin_ids() -> list:
    """Получить все ID админов (статичные + динамические)"""
    ids = set(ADMIN_IDS)
    ids.add(OWNER_ID)
    try:
        from db_adapter import db
        extra = await db.get_setting('extra_admins')
        if extra:
            for x in extra.split(','):
                x = x.strip()
                if x:
                    ids.add(int(x))
    except:
        pass
    return list(ids)


async def add_admin(user_id: int) -> bool:
    """Добавить динамического админа"""
    if user_id == OWNER_ID or user_id in ADMIN_IDS:
        return False  # уже есть
    try:
        from db_adapter import db
        extra = await db.get_setting('extra_admins') or ''
        ids = [x.strip() for x in extra.split(',') if x.strip()]
        if str(user_id) not in ids:
            ids.append(str(user_id))
            await db.set_setting('extra_admins', ','.join(ids))
        return True
    except:
        return False


async def remove_admin(user_id: int) -> str:
    """Удалить динамического админа. Возвращает статус."""
    if user_id == OWNER_ID:
        return 'owner'  # нельзя удалить владельца
    if user_id in ADMIN_IDS:
        return 'static'  # нельзя удалить из .env через бота
    try:
        from db_adapter import db
        extra = await db.get_setting('extra_admins') or ''
        ids = [x.strip() for x in extra.split(',') if x.strip()]
        if str(user_id) in ids:
            ids.remove(str(user_id))
            await db.set_setting('extra_admins', ','.join(ids))
            return 'removed'
        return 'not_found'
    except:
        return 'error'


def format_car_info(car: Dict, views: bool = True) -> str:
    text = f"🚗 <b>{car['brand']} {car['model']}</b>\n\n"

    if car.get('year'):
        text += f"📅 Год: {car['year']}\n"

    if car.get('description'):
        desc = car['description']
        if len(text) + len(desc) > MAX_CAPTION_LENGTH - 200:
            desc = desc[:200] + "..."
        text += f"\n📝 {desc}\n"

    if car.get('locations'):
        loc = car['locations']
        if len(text) + len(loc) > MAX_CAPTION_LENGTH - 100:
            loc = loc[:100] + "..."
        text += f"\n📍 {loc}\n"

    if views and car.get('views'):
        text += f"\n👁 Просмотров: {car['views']}"

    if len(text) > MAX_CAPTION_LENGTH:
        text = text[:MAX_CAPTION_LENGTH - 3] + "..."

    return text


def format_stats(stats: Dict) -> str:
    text = "📊 <b>Статистика бота</b>\n\n"
    text += f"🚗 Всего машин в базе: {stats['total_cars']}\n"
    text += f"👁 Всего просмотров: {stats['total_views']}\n"

    if stats['total_cars'] > 0:
        avg_views = stats['total_views'] / stats['total_cars']
        text += f"📈 Среднее просмотров на машину: {avg_views:.1f}"

    return text


def truncate_text(text: str, max_length: int = 50) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
