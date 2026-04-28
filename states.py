from aiogram.fsm.state import State, StatesGroup


class AddCarStates(StatesGroup):
    """Состояния для добавления автомобиля"""
    waiting_for_photo = State()
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_description = State()
    waiting_for_locations = State()


class SearchStates(StatesGroup):
    """Состояния для поиска"""
    waiting_for_query = State()


class EditCarStates(StatesGroup):
    """Состояния для редактирования"""
    waiting_for_field = State()
    waiting_for_value = State()
