from aiogram.fsm.state import State, StatesGroup


class AddCarStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_description = State()
    waiting_for_locations = State()


class SearchStates(StatesGroup):
    waiting_for_query = State()


class EditCarStates(StatesGroup):
    waiting_for_field = State()
    waiting_for_value = State()


class SettingsStates(StatesGroup):
    waiting_for_welcome_text = State()
    waiting_for_bot_name = State()
    waiting_for_welcome_photo = State()


# ============= ТИКЕТЫ ПОДДЕРЖКИ =============

class SupportStates(StatesGroup):
    waiting_for_subject = State()       # тема тикета
    waiting_for_message = State()       # первое сообщение
    waiting_for_reply = State()         # ответ пользователя в тикете
    waiting_for_close_reason = State()  # причина закрытия (для админа)


class AdminSupportStates(StatesGroup):
    waiting_for_reply = State()         # ответ админа в тикете


# ============= ПРЕДЛОЖЕНИЕ МАШИН =============

class SuggestCarStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_brand = State()
    waiting_for_model = State()
    waiting_for_year = State()
    waiting_for_description = State()
    waiting_for_locations = State()


class AdminRejectStates(StatesGroup):
    waiting_for_reason = State()        # причина отказа

