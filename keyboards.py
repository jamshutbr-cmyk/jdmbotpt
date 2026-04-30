from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Dict


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню — основные функции"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚗 Каталог", callback_data="catalog"),
        InlineKeyboardButton(text="🔍 Поиск", callback_data="search")
    )
    builder.row(
        InlineKeyboardButton(text="⭐ Избранное", callback_data="favorites"),
        InlineKeyboardButton(text="🏆 Топ машин", callback_data="top_cars")
    )
    builder.row(
        InlineKeyboardButton(text="🎲 Случайная", callback_data="random")
    )
    builder.row(
        InlineKeyboardButton(text="📸 Предложить машину", callback_data="suggest_menu")
    )
    builder.row(
        InlineKeyboardButton(text="☰ Ещё", callback_data="more_menu")
    )
    return builder.as_markup()


def more_menu_kb() -> InlineKeyboardMarkup:
    """Вспомогательное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🆘 Поддержка", callback_data="support_menu"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="👤 Мой рейтинг", callback_data="my_rating"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="user_settings")
    )
    builder.row(
        InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def admin_menu_kb() -> InlineKeyboardMarkup:
    """Админ меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить машину", callback_data="admin_add"),
        InlineKeyboardButton(text="📋 Список машин", callback_data="admin_list")
    )
    builder.row(
        InlineKeyboardButton(text="🎫 Тикеты", callback_data="admin_tickets"),
        InlineKeyboardButton(text="📸 Предложения", callback_data="admin_suggestions")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
    )
    return builder.as_markup()


def settings_menu_kb() -> InlineKeyboardMarkup:
    """Меню настроек"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💬 Приветствие", callback_data="settings_welcome")
    )
    builder.row(
        InlineKeyboardButton(text="🏷 Название бота", callback_data="settings_bot_name")
    )
    builder.row(
        InlineKeyboardButton(text="🖼 Фото приветствия", callback_data="settings_welcome_photo")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Управление админами", callback_data="manage_admins")
    )
    builder.row(
        InlineKeyboardButton(text="📢 Обязательная подписка", callback_data="subscription_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Сбросить всё", callback_data="settings_reset")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Админ-панель", callback_data="admin_panel")
    )
    return builder.as_markup()


def car_navigation_kb(current_index: int, total_cars: int, car_id: int, is_favorite: bool = False, is_admin: bool = False, user_rating: int = None, rating_stats: Dict = None) -> InlineKeyboardMarkup:
    """Клавиатура навигации по машинам"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки рейтинга
    likes = rating_stats.get('likes', 0) if rating_stats else 0
    dislikes = rating_stats.get('dislikes', 0) if rating_stats else 0
    
    like_text = "👍" if user_rating != 1 else "👍✅"
    dislike_text = "👎" if user_rating != -1 else "👎✅"
    
    if likes > 0:
        like_text += f" {likes}"
    if dislikes > 0:
        dislike_text += f" {dislikes}"
    
    builder.row(
        InlineKeyboardButton(text=like_text, callback_data=f"rate_like_{car_id}"),
        InlineKeyboardButton(text=dislike_text, callback_data=f"rate_dislike_{car_id}")
    )
    
    # Кнопка избранного
    fav_text = "💔 Убрать из избранного" if is_favorite else "❤️ В избранное"
    builder.row(
        InlineKeyboardButton(text=fav_text, callback_data=f"fav_{car_id}")
    )
    
    # Навигация
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️ Пред.", callback_data=f"nav_{current_index-1}")
        )
    
    nav_buttons.append(
        InlineKeyboardButton(text=f"{current_index+1}/{total_cars}", callback_data="current_pos")
    )
    
    if current_index < total_cars - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="След. ➡️", callback_data=f"nav_{current_index+1}")
        )
    
    builder.row(*nav_buttons)
    
    # Админские кнопки
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{car_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{car_id}")
        )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def catalog_kb(cars: list, page: int = 0, total_pages: int = 1) -> InlineKeyboardMarkup:
    """Клавиатура каталога с пагинацией"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки машин (по 2 в ряд)
    for i in range(0, len(cars), 2):
        row_buttons = []
        for car in cars[i:i+2]:
            text = f"{car['brand']} {car['model']}"
            if car.get('year'):
                text += f" ({car['year']})"
            row_buttons.append(
                InlineKeyboardButton(text=text, callback_data=f"car_{car['id']}")
            )
        builder.row(*row_buttons)
    
    # Пагинация
    if total_pages > 1:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"page_{page-1}")
            )
        nav_buttons.append(
            InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="current_page")
        )
        if page < total_pages - 1:
            nav_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"page_{page+1}")
            )
        builder.row(*nav_buttons)
    
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )
    
    return builder.as_markup()


def top_cars_list_kb(top_cars: list) -> InlineKeyboardMarkup:
    """Клавиатура списка топ машин"""
    builder = InlineKeyboardBuilder()
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    for i, car in enumerate(top_cars, 1):
        medal = medals.get(i, f"{i}.")
        year = f" ({car['year']})" if car.get('year') else ""
        score = car.get('score', 0)
        label = f"{medal} {car['brand']} {car['model']}{year}  ⭐{score:+d}"
        builder.row(
            InlineKeyboardButton(
                text=label,
                callback_data=f"top_car_{i}_{car['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))
    return builder.as_markup()


def top_car_detail_kb(car_id: int, is_favorite: bool = False, is_admin: bool = False,
                      user_rating: int = None, rating_stats: Dict = None) -> InlineKeyboardMarkup:
    """Клавиатура карточки машины из топа"""
    builder = InlineKeyboardBuilder()

    likes = rating_stats.get('likes', 0) if rating_stats else 0
    dislikes = rating_stats.get('dislikes', 0) if rating_stats else 0

    like_text = "👍✅" if user_rating == 1 else "👍"
    dislike_text = "👎✅" if user_rating == -1 else "👎"

    if likes > 0:
        like_text += f" {likes}"
    if dislikes > 0:
        dislike_text += f" {dislikes}"

    builder.row(
        InlineKeyboardButton(text=like_text, callback_data=f"rate_like_{car_id}"),
        InlineKeyboardButton(text=dislike_text, callback_data=f"rate_dislike_{car_id}")
    )

    fav_text = "💔 Убрать из избранного" if is_favorite else "❤️ В избранное"
    builder.row(InlineKeyboardButton(text=fav_text, callback_data=f"fav_{car_id}"))

    if is_admin:
        builder.row(
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{car_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{car_id}")
        )

    builder.row(InlineKeyboardButton(text="🏆 Назад к топу", callback_data="top_cars"))
    builder.row(InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main"))

    return builder.as_markup()


def search_results_kb() -> InlineKeyboardMarkup:
    """Клавиатура для результатов поиска"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )
    return builder.as_markup()


def confirm_delete_kb(car_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{car_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"car_{car_id}")
    )
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")
    )
    return builder.as_markup()


def back_to_more_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню 'Ещё'"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="more_menu")
    )
    return builder.as_markup()
