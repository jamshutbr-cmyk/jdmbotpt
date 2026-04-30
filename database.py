import aiosqlite
from typing import List, Optional, Dict
from config import DB_PATH


class Database:
    def __init__(self):
        self.db_path = DB_PATH

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица автомобилей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS cars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    year INTEGER,
                    description TEXT,
                    locations TEXT,
                    photo_id TEXT,
                    views INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица избранного
            await db.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id INTEGER,
                    car_id INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, car_id),
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица просмотров (для уникальных просмотров)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS views (
                    user_id INTEGER,
                    car_id INTEGER,
                    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, car_id),
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица настроек
            await db.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Таблица каналов для обязательной подписки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS required_channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id TEXT NOT NULL UNIQUE,
                    channel_url TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица тикетов поддержки
            await db.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    subject TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    close_reason TEXT
                )
            ''')
            
            # Таблица сообщений тикетов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    is_admin INTEGER DEFAULT 0,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица предложений машин
            await db.execute('''
                CREATE TABLE IF NOT EXISTS car_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    brand TEXT NOT NULL,
                    model TEXT NOT NULL,
                    year INTEGER,
                    description TEXT,
                    locations TEXT,
                    photo_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    reject_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица пользователей (для рассылки и настроек)
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    show_username INTEGER DEFAULT 1,
                    notify_new_cars INTEGER DEFAULT 0,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица лайков/дизлайков машин
            await db.execute('''
                CREATE TABLE IF NOT EXISTS car_ratings (
                    user_id INTEGER,
                    car_id INTEGER,
                    rating INTEGER NOT NULL CHECK (rating IN (-1, 1)),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, car_id),
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
                )
            ''')

            # Таблица дополнительных медиа (фото/видео) для машин
            await db.execute('''
                CREATE TABLE IF NOT EXISTS car_media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    car_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    media_type TEXT NOT NULL DEFAULT 'photo',
                    position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
                )
            ''')

            # Таблица доп. медиа для предложений пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS suggestion_media (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    suggestion_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    media_type TEXT NOT NULL DEFAULT 'photo',
                    position INTEGER DEFAULT 0,
                    FOREIGN KEY (suggestion_id) REFERENCES car_suggestions(id) ON DELETE CASCADE
                )
            ''')
            await db.execute('''
                INSERT OR IGNORE INTO settings (key, value) 
                VALUES ('welcome_text', '🚗 <b>Добро пожаловать в JDM Cars Bot!</b>\n\nЗдесь ты найдешь крутые тачки, сфотографированные на улицах города.\n\nВыбери действие из меню ниже:')
            ''')
            await db.execute('''
                INSERT OR IGNORE INTO settings (key, value) 
                VALUES ('bot_name', 'JDM Cars Bot')
            ''')
            
            await db.commit()

    async def add_car(self, brand: str, model: str, year: Optional[int], 
                     description: Optional[str], locations: Optional[str], 
                     photo_id: str) -> int:
        """Добавить новый автомобиль"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO cars (brand, model, year, description, locations, photo_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (brand, model, year, description, locations, photo_id))
            await db.commit()
            return cursor.lastrowid

    async def get_car(self, car_id: int) -> Optional[Dict]:
        """Получить информацию об автомобиле"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM cars WHERE id = ?', (car_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_cars(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Получить список всех автомобилей"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM cars 
                ORDER BY created_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def search_cars(self, query: str) -> List[Dict]:
        """Поиск автомобилей по марке/модели"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            search_pattern = f'%{query}%'
            cursor = await db.execute('''
                SELECT * FROM cars 
                WHERE brand LIKE ? OR model LIKE ?
                ORDER BY created_at DESC
            ''', (search_pattern, search_pattern))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_car(self, car_id: int, **kwargs):
        """Обновить информацию об автомобиле"""
        fields = []
        values = []
        for key, value in kwargs.items():
            if value is not None:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return
        
        values.append(car_id)
        query = f"UPDATE cars SET {', '.join(fields)} WHERE id = ?"
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, values)
            await db.commit()

    async def delete_car(self, car_id: int):
        """Удалить автомобиль"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM cars WHERE id = ?', (car_id,))
            await db.commit()

    async def increment_views(self, car_id: int, user_id: int):
        """Увеличить счетчик просмотров (только уникальные)"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем, смотрел ли пользователь эту машину
            cursor = await db.execute(
                'SELECT 1 FROM views WHERE user_id = ? AND car_id = ?',
                (user_id, car_id)
            )
            already_viewed = await cursor.fetchone()
            
            if not already_viewed:
                # Добавляем запись о просмотре
                await db.execute(
                    'INSERT INTO views (user_id, car_id) VALUES (?, ?)',
                    (user_id, car_id)
                )
                # Увеличиваем счетчик
                await db.execute(
                    'UPDATE cars SET views = views + 1 WHERE id = ?',
                    (car_id,)
                )
                await db.commit()

    async def get_random_car(self) -> Optional[Dict]:
        """Получить случайный автомобиль"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM cars ORDER BY RANDOM() LIMIT 1')
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_stats(self) -> Dict:
        """Получить статистику"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT COUNT(*) as total FROM cars')
            row = await cursor.fetchone()
            total_cars = row[0]
            
            cursor = await db.execute('SELECT SUM(views) as total_views FROM cars')
            row = await cursor.fetchone()
            total_views = row[0] or 0
            
            # Рейтинговая статистика
            cursor = await db.execute('SELECT COUNT(CASE WHEN rating = 1 THEN 1 END) as likes FROM car_ratings')
            row = await cursor.fetchone()
            total_likes = row[0] or 0
            
            cursor = await db.execute('SELECT COUNT(CASE WHEN rating = -1 THEN 1 END) as dislikes FROM car_ratings')
            row = await cursor.fetchone()
            total_dislikes = row[0] or 0
            
            cursor = await db.execute('SELECT COUNT(DISTINCT car_id) as rated_cars FROM car_ratings')
            row = await cursor.fetchone()
            rated_cars = row[0] or 0
            
            return {
                'total_cars': total_cars,
                'total_views': total_views,
                'total_likes': total_likes,
                'total_dislikes': total_dislikes,
                'rated_cars': rated_cars
            }

    # Избранное
    async def add_to_favorites(self, user_id: int, car_id: int):
        """Добавить в избранное"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute('''
                    INSERT INTO favorites (user_id, car_id) VALUES (?, ?)
                ''', (user_id, car_id))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def remove_from_favorites(self, user_id: int, car_id: int):
        """Удалить из избранного"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                DELETE FROM favorites WHERE user_id = ? AND car_id = ?
            ''', (user_id, car_id))
            await db.commit()

    async def is_favorite(self, user_id: int, car_id: int) -> bool:
        """Проверить, в избранном ли автомобиль"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT 1 FROM favorites WHERE user_id = ? AND car_id = ?
            ''', (user_id, car_id))
            return await cursor.fetchone() is not None

    async def get_favorites(self, user_id: int) -> List[Dict]:
        """Получить избранные автомобили пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT c.* FROM cars c
                JOIN favorites f ON c.id = f.car_id
                WHERE f.user_id = ?
                ORDER BY f.added_at DESC
            ''', (user_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # Настройки
    async def get_setting(self, key: str) -> Optional[str]:
        """Получить настройку"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('SELECT value FROM settings WHERE key = ?', (key,))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_setting(self, key: str, value: str):
        """Установить настройку"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)
            ''', (key, value))
            await db.commit()

    # ============= ТИКЕТЫ =============

    async def create_ticket(self, user_id: int, username: str, subject: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO tickets (user_id, username, subject)
                VALUES (?, ?, ?)
            ''', (user_id, username, subject))
            await db.commit()
            return cursor.lastrowid

    async def get_ticket(self, ticket_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_tickets(self, user_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM tickets WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def get_all_tickets(self, status: str = None) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if status:
                cursor = await db.execute(
                    'SELECT * FROM tickets WHERE status = ? ORDER BY created_at DESC',
                    (status,)
                )
            else:
                cursor = await db.execute('SELECT * FROM tickets ORDER BY created_at DESC')
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_ticket_status(self, ticket_id: int, status: str, reason: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            if status == 'closed':
                await db.execute('''
                    UPDATE tickets SET status = ?, close_reason = ?, closed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, reason, ticket_id))
            else:
                await db.execute('UPDATE tickets SET status = ? WHERE id = ?', (status, ticket_id))
            await db.commit()

    async def add_ticket_message(self, ticket_id: int, user_id: int, text: str, is_admin: bool = False):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO ticket_messages (ticket_id, user_id, is_admin, text)
                VALUES (?, ?, ?, ?)
            ''', (ticket_id, user_id, 1 if is_admin else 0, text))
            await db.commit()

    async def get_ticket_messages(self, ticket_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM ticket_messages WHERE ticket_id = ?
                ORDER BY created_at ASC
            ''', (ticket_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ============= ПРЕДЛОЖЕНИЯ МАШИН =============

    async def create_suggestion(self, user_id: int, username: str, brand: str,
                                 model: str, year: Optional[int], description: Optional[str],
                                 locations: Optional[str], photo_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                INSERT INTO car_suggestions
                (user_id, username, brand, model, year, description, locations, photo_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, brand, model, year, description, locations, photo_id))
            await db.commit()
            return cursor.lastrowid

    async def get_suggestion(self, suggestion_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM car_suggestions WHERE id = ?', (suggestion_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_pending_suggestions(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM car_suggestions WHERE status = 'pending'
                ORDER BY created_at ASC
            ''')
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def update_suggestion_status(self, suggestion_id: int, status: str, reason: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE car_suggestions SET status = ?, reject_reason = ? WHERE id = ?
            ''', (status, reason, suggestion_id))
            await db.commit()

    async def get_user_suggestions(self, user_id: int) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM car_suggestions WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    # ============= ПОЛЬЗОВАТЕЛИ =============

    async def register_user(self, user_id: int, username: str, first_name: str):
        """Зарегистрировать/обновить пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_seen = CURRENT_TIMESTAMP
            ''', (user_id, username, first_name))
            await db.commit()

    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_users(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM users')
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def set_show_username(self, user_id: int, value: bool):
        """Установить настройку отображения ника"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO users (user_id, show_username)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET show_username = excluded.show_username
            ''', (user_id, 1 if value else 0))
            await db.commit()

    async def get_show_username(self, user_id: int) -> bool:
        """Получить настройку отображения ника"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT show_username FROM users WHERE user_id = ?', (user_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return True
            return bool(row[0])

    async def set_notify_new_cars(self, user_id: int, value: bool):
        """Установить настройку уведомлений о новых машинах"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO users (user_id, notify_new_cars)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET notify_new_cars = excluded.notify_new_cars
            ''', (user_id, 1 if value else 0))
            await db.commit()

    async def get_notify_new_cars(self, user_id: int) -> bool:
        """Получить настройку уведомлений"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT notify_new_cars FROM users WHERE user_id = ?', (user_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return False  # по умолчанию выключено
            return bool(row[0])

    async def get_users_with_notifications(self) -> List[Dict]:
        """Получить всех пользователей с включёнными уведомлениями"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM users WHERE notify_new_cars = 1'
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]    # ============= КАНАЛЫ =============

    async def get_required_channels(self) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('SELECT * FROM required_channels ORDER BY added_at ASC')
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def add_required_channel(self, channel_id: str, channel_url: str, channel_name: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute('''
                    INSERT INTO required_channels (channel_id, channel_url, channel_name)
                    VALUES (?, ?, ?)
                ''', (channel_id, channel_url, channel_name))
                await db.commit()
                return True
            except:
                return False

    async def remove_required_channel(self, channel_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM required_channels WHERE id = ?', (channel_id,))
            await db.commit()

    async def toggle_required_channel(self, channel_id: int):
        """Переключить активность канала"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                UPDATE required_channels SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
                WHERE id = ?
            ''', (channel_id,))
            await db.commit()

    # ============= РЕЙТИНГОВАЯ СИСТЕМА =============

    async def set_car_rating(self, user_id: int, car_id: int, rating: int):
        """Поставить лайк (1) или дизлайк (-1) машине"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO car_ratings (user_id, car_id, rating)
                VALUES (?, ?, ?)
            ''', (user_id, car_id, rating))
            await db.commit()

    async def get_car_rating(self, user_id: int, car_id: int) -> Optional[int]:
        """Получить рейтинг пользователя для машины"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT rating FROM car_ratings WHERE user_id = ? AND car_id = ?
            ''', (user_id, car_id))
            row = await cursor.fetchone()
            return row[0] if row else None

    async def remove_car_rating(self, user_id: int, car_id: int):
        """Убрать рейтинг (отменить лайк/дизлайк)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                DELETE FROM car_ratings WHERE user_id = ? AND car_id = ?
            ''', (user_id, car_id))
            await db.commit()

    async def get_car_rating_stats(self, car_id: int) -> Dict:
        """Получить статистику рейтинга машины"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT 
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as likes,
                    COUNT(CASE WHEN rating = -1 THEN 1 END) as dislikes,
                    COUNT(*) as total_ratings
                FROM car_ratings WHERE car_id = ?
            ''', (car_id,))
            row = await cursor.fetchone()
            if row:
                likes, dislikes, total = row
                score = likes - dislikes  # общий рейтинг
                return {
                    'likes': likes,
                    'dislikes': dislikes, 
                    'total_ratings': total,
                    'score': score
                }
            return {'likes': 0, 'dislikes': 0, 'total_ratings': 0, 'score': 0}

    async def get_top_rated_cars(self, limit: int = 10) -> List[Dict]:
        """Получить топ машин по рейтингу"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT c.*, 
                       COALESCE(r.likes, 0) as likes,
                       COALESCE(r.dislikes, 0) as dislikes,
                       COALESCE(r.score, 0) as score
                FROM cars c
                LEFT JOIN (
                    SELECT car_id,
                           COUNT(CASE WHEN rating = 1 THEN 1 END) as likes,
                           COUNT(CASE WHEN rating = -1 THEN 1 END) as dislikes,
                           COUNT(CASE WHEN rating = 1 THEN 1 END) - COUNT(CASE WHEN rating = -1 THEN 1 END) as score
                    FROM car_ratings
                    GROUP BY car_id
                ) r ON c.id = r.car_id
                ORDER BY score DESC, likes DESC
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_user_rating_stats(self, user_id: int) -> Dict:
        """Получить статистику пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            # Количество одобренных предложений
            cursor = await db.execute('''
                SELECT COUNT(*) FROM car_suggestions 
                WHERE user_id = ? AND status = 'approved'
            ''', (user_id,))
            approved_suggestions = (await cursor.fetchone())[0]
            
            # Общий рейтинг предложенных машин
            cursor = await db.execute('''
                SELECT 
                    COALESCE(SUM(CASE WHEN cr.rating = 1 THEN 1 ELSE 0 END), 0) as total_likes,
                    COALESCE(SUM(CASE WHEN cr.rating = -1 THEN 1 ELSE 0 END), 0) as total_dislikes
                FROM car_suggestions cs
                LEFT JOIN cars c ON cs.brand = c.brand AND cs.model = c.model
                LEFT JOIN car_ratings cr ON c.id = cr.car_id
                WHERE cs.user_id = ? AND cs.status = 'approved'
            ''', (user_id,))
            row = await cursor.fetchone()
            total_likes, total_dislikes = row if row else (0, 0)
            
            return {
                'approved_suggestions': approved_suggestions,
                'total_likes': total_likes,
                'total_dislikes': total_dislikes,
                'user_score': total_likes - total_dislikes
            }

    # ============= МЕДИА МАШИН =============

    async def add_car_media(self, car_id: int, file_id: str, media_type: str = 'photo') -> int:
        """Добавить медиафайл к машине"""
        async with aiosqlite.connect(self.db_path) as db:
            # Определяем следующую позицию
            cursor = await db.execute(
                'SELECT COALESCE(MAX(position), -1) + 1 FROM car_media WHERE car_id = ?',
                (car_id,)
            )
            position = (await cursor.fetchone())[0]
            cursor = await db.execute('''
                INSERT INTO car_media (car_id, file_id, media_type, position)
                VALUES (?, ?, ?, ?)
            ''', (car_id, file_id, media_type, position))
            await db.commit()
            return cursor.lastrowid

    async def get_car_media(self, car_id: int) -> List[Dict]:
        """Получить все медиафайлы машины"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute('''
                SELECT * FROM car_media WHERE car_id = ?
                ORDER BY position ASC
            ''', (car_id,))
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def count_car_media(self, car_id: int) -> int:
        """Количество доп. медиафайлов машины"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT COUNT(*) FROM car_media WHERE car_id = ?', (car_id,)
            )
            return (await cursor.fetchone())[0]

    async def delete_car_media(self, car_id: int):
        """Удалить все медиафайлы машины"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM car_media WHERE car_id = ?', (car_id,))
            await db.commit()

    # ============= МЕДИА ПРЕДЛОЖЕНИЙ =============

    async def add_suggestion_media(self, suggestion_id: int, file_id: str, media_type: str = 'photo'):
        """Добавить медиафайл к предложению"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT COALESCE(MAX(position), -1) + 1 FROM suggestion_media WHERE suggestion_id = ?',
                (suggestion_id,)
            )
            position = (await cursor.fetchone())[0]
            await db.execute('''
                INSERT INTO suggestion_media (suggestion_id, file_id, media_type, position)
                VALUES (?, ?, ?, ?)
            ''', (suggestion_id, file_id, media_type, position))
            await db.commit()

    async def get_suggestion_media(self, suggestion_id: int) -> List[Dict]:
        """Получить все медиафайлы предложения"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                'SELECT * FROM suggestion_media WHERE suggestion_id = ? ORDER BY position ASC',
                (suggestion_id,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


db = Database()
