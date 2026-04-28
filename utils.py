from typing import Optional, Dict
from config import ADMIN_IDS


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id in ADMIN_IDS


def format_car_info(car: Dict, views: bool = True) -> str:
    """Форматирование информации об автомобиле"""
    text = f"🚗 <b>{car['brand']} {car['model']}</b>\n\n"
    
    if car.get('year'):
        text += f"📅 Год: {car['year']}\n"
    
    if car.get('description'):
        text += f"\n📝 Описание:\n{car['description']}\n"
    
    if car.get('locations'):
        text += f"\n📍 Где можно встретить:\n{car['locations']}\n"
    
    if views and car.get('views'):
        text += f"\n👁 Просмотров: {car['views']}"
    
    return text


def format_stats(stats: Dict) -> str:
    """Форматирование статистики"""
    text = "📊 <b>Статистика бота</b>\n\n"
    text += f"🚗 Всего машин в базе: {stats['total_cars']}\n"
    text += f"👁 Всего просмотров: {stats['total_views']}\n"
    
    if stats['total_cars'] > 0:
        avg_views = stats['total_views'] / stats['total_cars']
        text += f"📈 Среднее просмотров на машину: {avg_views:.1f}"
    
    return text


def truncate_text(text: str, max_length: int = 50) -> str:
    """Обрезать текст до указанной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."
