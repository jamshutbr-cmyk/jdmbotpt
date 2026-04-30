"""
PostgreSQL database adapter
"""
import asyncpg
from typing import List, Optional, Dict
from config import DATABASE_URL


class PostgresDatabase:
    def __init__(self):
        self.database_url = DATABASE_URL
        self.pool = None

    async def init_db(self):
        """Инициализация базы данных PostgreSQL"""
        self.pool = await asyncpg.create_pool(self.database_url)
        
        async with self.pool.acquire() as conn:
            # Таблица автомобилей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS cars (
                    id SERIAL PRIMARY KEY,
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
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id BIGINT,
                    car_id INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, car_id),
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица просмотров
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS views (
                    user_id BIGINT,
                    car_id INTEGER,
                    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, car_id),
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
                )
            ''')
            
            # Таблица настроек
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Таблица пользователей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    show_username INTEGER DEFAULT 1,
                    notify_new_cars INTEGER DEFAULT 0,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Миграция: добавляем колонки если их нет
            try:
                await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_new_cars INTEGER DEFAULT 0')
            except:
                pass
            try:
                await conn.execute('ALTER TABLE users ADD COLUMN IF NOT EXISTS show_username INTEGER DEFAULT 1')
            except:
                pass
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS required_channels (
                    id SERIAL PRIMARY KEY,
                    channel_id TEXT NOT NULL UNIQUE,
                    channel_url TEXT NOT NULL,
                    channel_name TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username TEXT,
                    subject TEXT NOT NULL,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP,
                    close_reason TEXT
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS ticket_messages (
                    id SERIAL PRIMARY KEY,
                    ticket_id INTEGER NOT NULL,
                    user_id BIGINT NOT NULL,
                    is_admin INTEGER DEFAULT 0,
                    text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
                )
            ''')

            await conn.execute('''
                CREATE TABLE IF NOT EXISTS car_suggestions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
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
            
            # Таблица лайков/дизлайков машин
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS car_ratings (
                    user_id BIGINT,
                    car_id INTEGER,
                    rating INTEGER NOT NULL CHECK (rating IN (-1, 1)),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, car_id),
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
                )
            ''')

            # Таблица дополнительных медиа (фото/видео) для машин
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS car_media (
                    id SERIAL PRIMARY KEY,
                    car_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    media_type TEXT NOT NULL DEFAULT 'photo',
                    position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (car_id) REFERENCES cars(id) ON DELETE CASCADE
                )
            ''')

            # Таблица доп. медиа для предложений пользователей
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS suggestion_media (
                    id SERIAL PRIMARY KEY,
                    suggestion_id INTEGER NOT NULL,
                    file_id TEXT NOT NULL,
                    media_type TEXT NOT NULL DEFAULT 'photo',
                    position INTEGER DEFAULT 0,
                    FOREIGN KEY (suggestion_id) REFERENCES car_suggestions(id) ON DELETE CASCADE
                )
            ''')
            await conn.execute('''
                INSERT INTO settings (key, value) 
                VALUES ('welcome_text', '🚗 <b>Добро пожаловать в JDM Cars Bot!</b>\n\nЗдесь ты найдешь крутые тачки, сфотографированные на улицах города.\n\nВыбери действие из меню ниже:')
                ON CONFLICT (key) DO NOTHING
            ''')
            await conn.execute('''
                INSERT INTO settings (key, value) 
                VALUES ('bot_name', 'JDM Cars Bot')
                ON CONFLICT (key) DO NOTHING
            ''')

    async def add_car(self, brand: str, model: str, year: Optional[int], 
                     description: Optional[str], locations: Optional[str], 
                     photo_id: str) -> int:
        """Добавить новый автомобиль"""
        async with self.pool.acquire() as conn:
            car_id = await conn.fetchval('''
                INSERT INTO cars (brand, model, year, description, locations, photo_id)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            ''', brand, model, year, description, locations, photo_id)
            return car_id

    async def get_car(self, car_id: int) -> Optional[Dict]:
        """Получить информацию об автомобиле"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM cars WHERE id = $1', car_id)
            return dict(row) if row else None

    async def get_all_cars(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """Получить список всех автомобилей"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM cars 
                ORDER BY created_at DESC 
                LIMIT $1 OFFSET $2
            ''', limit, offset)
            return [dict(row) for row in rows]

    async def search_cars(self, query: str) -> List[Dict]:
        """Поиск автомобилей по марке/модели"""
        async with self.pool.acquire() as conn:
            search_pattern = f'%{query}%'
            rows = await conn.fetch('''
                SELECT * FROM cars 
                WHERE brand ILIKE $1 OR model ILIKE $1
                ORDER BY created_at DESC
            ''', search_pattern)
            return [dict(row) for row in rows]

    async def update_car(self, car_id: int, **kwargs):
        """Обновить информацию об автомобиле"""
        fields = []
        values = []
        for i, (key, value) in enumerate(kwargs.items(), 1):
            if value is not None:
                fields.append(f"{key} = ${i}")
                values.append(value)
        
        if not fields:
            return
        
        values.append(car_id)
        query = f"UPDATE cars SET {', '.join(fields)} WHERE id = ${len(values)}"
        
        async with self.pool.acquire() as conn:
            await conn.execute(query, *values)

    async def delete_car(self, car_id: int):
        """Удалить автомобиль"""
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM cars WHERE id = $1', car_id)

    async def increment_views(self, car_id: int, user_id: int):
        """Увеличить счетчик просмотров (только уникальные)"""
        async with self.pool.acquire() as conn:
            # Проверяем, смотрел ли пользователь эту машину
            already_viewed = await conn.fetchval(
                'SELECT 1 FROM views WHERE user_id = $1 AND car_id = $2',
                user_id, car_id
            )
            
            if not already_viewed:
                # Добавляем запись о просмотре
                await conn.execute(
                    'INSERT INTO views (user_id, car_id) VALUES ($1, $2)',
                    user_id, car_id
                )
                # Увеличиваем счетчик
                await conn.execute(
                    'UPDATE cars SET views = views + 1 WHERE id = $1',
                    car_id
                )

    async def get_random_car(self) -> Optional[Dict]:
        """Получить случайный автомобиль"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM cars ORDER BY RANDOM() LIMIT 1')
            return dict(row) if row else None

    async def get_stats(self) -> Dict:
        """Получить статистику"""
        async with self.pool.acquire() as conn:
            total_cars = await conn.fetchval('SELECT COUNT(*) FROM cars')
            total_views = await conn.fetchval('SELECT COALESCE(SUM(views), 0) FROM cars')
            
            # Рейтинговая статистика
            total_likes = await conn.fetchval('SELECT COUNT(*) FROM car_ratings WHERE rating = 1') or 0
            total_dislikes = await conn.fetchval('SELECT COUNT(*) FROM car_ratings WHERE rating = -1') or 0
            rated_cars = await conn.fetchval('SELECT COUNT(DISTINCT car_id) FROM car_ratings') or 0
            
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
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    'INSERT INTO favorites (user_id, car_id) VALUES ($1, $2)',
                    user_id, car_id
                )
                return True
            except asyncpg.UniqueViolationError:
                return False

    async def remove_from_favorites(self, user_id: int, car_id: int):
        """Удалить из избранного"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM favorites WHERE user_id = $1 AND car_id = $2',
                user_id, car_id
            )

    async def is_favorite(self, user_id: int, car_id: int) -> bool:
        """Проверить, в избранном ли автомобиль"""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                'SELECT 1 FROM favorites WHERE user_id = $1 AND car_id = $2',
                user_id, car_id
            )
            return result is not None

    async def get_favorites(self, user_id: int) -> List[Dict]:
        """Получить избранные автомобили пользователя"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT c.* FROM cars c
                JOIN favorites f ON c.id = f.car_id
                WHERE f.user_id = $1
                ORDER BY f.added_at DESC
            ''', user_id)
            return [dict(row) for row in rows]

    # Настройки
    async def get_setting(self, key: str) -> Optional[str]:
        """Получить настройку"""
        async with self.pool.acquire() as conn:
            value = await conn.fetchval('SELECT value FROM settings WHERE key = $1', key)
            return value

    async def set_setting(self, key: str, value: str):
        """Установить настройку"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO settings (key, value) VALUES ($1, $2)
                ON CONFLICT (key) DO UPDATE SET value = $2
            ''', key, value)

    # ============= ТИКЕТЫ =============

    async def create_ticket(self, user_id: int, username: str, subject: str) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval('''
                INSERT INTO tickets (user_id, username, subject)
                VALUES ($1, $2, $3) RETURNING id
            ''', user_id, username, subject)

    async def get_ticket(self, ticket_id: int) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM tickets WHERE id = $1', ticket_id)
            return dict(row) if row else None

    async def get_user_tickets(self, user_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM tickets WHERE user_id = $1 ORDER BY created_at DESC', user_id
            )
            return [dict(r) for r in rows]

    async def get_all_tickets(self, status: str = None) -> List[Dict]:
        async with self.pool.acquire() as conn:
            if status:
                rows = await conn.fetch(
                    'SELECT * FROM tickets WHERE status = $1 ORDER BY created_at DESC', status
                )
            else:
                rows = await conn.fetch('SELECT * FROM tickets ORDER BY created_at DESC')
            return [dict(r) for r in rows]

    async def update_ticket_status(self, ticket_id: int, status: str, reason: str = None):
        async with self.pool.acquire() as conn:
            if status == 'closed':
                await conn.execute('''
                    UPDATE tickets SET status = $1, close_reason = $2, closed_at = NOW()
                    WHERE id = $3
                ''', status, reason, ticket_id)
            else:
                await conn.execute('UPDATE tickets SET status = $1 WHERE id = $2', status, ticket_id)

    async def add_ticket_message(self, ticket_id: int, user_id: int, text: str, is_admin: bool = False):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO ticket_messages (ticket_id, user_id, is_admin, text)
                VALUES ($1, $2, $3, $4)
            ''', ticket_id, user_id, 1 if is_admin else 0, text)

    async def get_ticket_messages(self, ticket_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM ticket_messages WHERE ticket_id = $1 ORDER BY created_at ASC',
                ticket_id
            )
            return [dict(r) for r in rows]

    # ============= ПРЕДЛОЖЕНИЯ =============

    async def create_suggestion(self, user_id: int, username: str, brand: str,
                                 model: str, year: Optional[int], description: Optional[str],
                                 locations: Optional[str], photo_id: str) -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval('''
                INSERT INTO car_suggestions
                (user_id, username, brand, model, year, description, locations, photo_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id
            ''', user_id, username, brand, model, year, description, locations, photo_id)

    async def get_suggestion(self, suggestion_id: int) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM car_suggestions WHERE id = $1', suggestion_id)
            return dict(row) if row else None

    async def get_pending_suggestions(self) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM car_suggestions WHERE status = 'pending' ORDER BY created_at ASC"
            )
            return [dict(r) for r in rows]

    async def get_user_suggestions(self, user_id: int) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM car_suggestions WHERE user_id = $1 ORDER BY created_at DESC',
                user_id
            )
            return [dict(r) for r in rows]

    # ============= ПОЛЬЗОВАТЕЛИ =============

    async def register_user(self, user_id: int, username: str, first_name: str):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username, first_name)
                VALUES ($1, $2, $3)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_seen = NOW()
            ''', user_id, username, first_name)

    async def get_user(self, user_id: int) -> Optional[Dict]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('SELECT * FROM users WHERE user_id = $1', user_id)
            return dict(row) if row else None

    async def get_all_users(self) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM users')
            return [dict(r) for r in rows]

    async def set_show_username(self, user_id: int, value: bool):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, show_username)
                VALUES ($1, $2)
                ON CONFLICT(user_id) DO UPDATE SET show_username = EXCLUDED.show_username
            ''', user_id, 1 if value else 0)

    async def get_show_username(self, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT show_username FROM users WHERE user_id = $1', user_id
            )
            if row is None:
                return True
            return bool(row['show_username'])

    async def set_notify_new_cars(self, user_id: int, value: bool):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, notify_new_cars)
                VALUES ($1, $2)
                ON CONFLICT(user_id) DO UPDATE SET notify_new_cars = EXCLUDED.notify_new_cars
            ''', user_id, 1 if value else 0)

    async def get_notify_new_cars(self, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                'SELECT notify_new_cars FROM users WHERE user_id = $1', user_id
            )
            if row is None:
                return False
            return bool(row['notify_new_cars'])

    async def get_users_with_notifications(self) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM users WHERE notify_new_cars = 1')
            return [dict(r) for r in rows]

    async def update_suggestion_status(self, suggestion_id: int, status: str, reason: str = None):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE car_suggestions SET status = $1, reject_reason = $2 WHERE id = $3
            ''', status, reason, suggestion_id)

    # ============= КАНАЛЫ =============

    async def get_required_channels(self) -> List[Dict]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('SELECT * FROM required_channels ORDER BY added_at ASC')
            return [dict(r) for r in rows]

    async def add_required_channel(self, channel_id: str, channel_url: str, channel_name: str) -> bool:
        async with self.pool.acquire() as conn:
            try:
                await conn.execute('''
                    INSERT INTO required_channels (channel_id, channel_url, channel_name)
                    VALUES ($1, $2, $3)
                ''', channel_id, channel_url, channel_name)
                return True
            except:
                return False

    async def remove_required_channel(self, channel_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM required_channels WHERE id = $1', channel_id)

    async def toggle_required_channel(self, channel_id: int):
        """Переключить активность канала"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                UPDATE required_channels SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
                WHERE id = $1
            ''', channel_id)

    # ============= РЕЙТИНГОВАЯ СИСТЕМА =============

    async def set_car_rating(self, user_id: int, car_id: int, rating: int):
        """Поставить лайк (1) или дизлайк (-1) машине"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO car_ratings (user_id, car_id, rating)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, car_id) DO UPDATE SET rating = $3, created_at = CURRENT_TIMESTAMP
            ''', user_id, car_id, rating)

    async def get_car_rating(self, user_id: int, car_id: int) -> Optional[int]:
        """Получить рейтинг пользователя для машины"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT rating FROM car_ratings WHERE user_id = $1 AND car_id = $2
            ''', user_id, car_id)
            return row['rating'] if row else None

    async def remove_car_rating(self, user_id: int, car_id: int):
        """Убрать рейтинг (отменить лайк/дизлайк)"""
        async with self.pool.acquire() as conn:
            await conn.execute('''
                DELETE FROM car_ratings WHERE user_id = $1 AND car_id = $2
            ''', user_id, car_id)

    async def get_car_rating_stats(self, car_id: int) -> Dict:
        """Получить статистику рейтинга машины"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT 
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as likes,
                    COUNT(CASE WHEN rating = -1 THEN 1 END) as dislikes,
                    COUNT(*) as total_ratings
                FROM car_ratings WHERE car_id = $1
            ''', car_id)
            if row:
                likes, dislikes, total = row['likes'], row['dislikes'], row['total_ratings']
                score = likes - dislikes
                return {
                    'likes': likes,
                    'dislikes': dislikes,
                    'total_ratings': total,
                    'score': score
                }
            return {'likes': 0, 'dislikes': 0, 'total_ratings': 0, 'score': 0}

    async def get_top_rated_cars(self, limit: int = 10) -> List[Dict]:
        """Получить топ машин по рейтингу"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch('''
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
                LIMIT $1
            ''', limit)
            return [dict(row) for row in rows]

    async def get_user_rating_stats(self, user_id: int) -> Dict:
        """Получить статистику пользователя"""
        async with self.pool.acquire() as conn:
            # Количество одобренных предложений
            approved_suggestions = await conn.fetchval('''
                SELECT COUNT(*) FROM car_suggestions 
                WHERE user_id = $1 AND status = 'approved'
            ''', user_id)
            
            # Общий рейтинг предложенных машин
            row = await conn.fetchrow('''
                SELECT 
                    COALESCE(SUM(CASE WHEN cr.rating = 1 THEN 1 ELSE 0 END), 0) as total_likes,
                    COALESCE(SUM(CASE WHEN cr.rating = -1 THEN 1 ELSE 0 END), 0) as total_dislikes
                FROM car_suggestions cs
                LEFT JOIN cars c ON cs.brand = c.brand AND cs.model = c.model
                LEFT JOIN car_ratings cr ON c.id = cr.car_id
                WHERE cs.user_id = $1 AND cs.status = 'approved'
            ''', user_id)
            
            total_likes = row['total_likes'] if row else 0
            total_dislikes = row['total_dislikes'] if row else 0
            
            return {
                'approved_suggestions': approved_suggestions or 0,
                'total_likes': total_likes,
                'total_dislikes': total_dislikes,
                'user_score': total_likes - total_dislikes
            }

    async def close(self):
        if self.pool:
            await self.pool.close()

    # ============= МЕДИА МАШИН =============

    async def add_car_media(self, car_id: int, file_id: str, media_type: str = 'photo') -> int:
        """Добавить медиафайл к машине"""
        async with self.pool.acquire() as conn:
            position = await conn.fetchval(
                'SELECT COALESCE(MAX(position), -1) + 1 FROM car_media WHERE car_id = $1',
                car_id
            )
            return await conn.fetchval('''
                INSERT INTO car_media (car_id, file_id, media_type, position)
                VALUES ($1, $2, $3, $4) RETURNING id
            ''', car_id, file_id, media_type, position)

    async def get_car_media(self, car_id: int) -> List[Dict]:
        """Получить все медиафайлы машины"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM car_media WHERE car_id = $1 ORDER BY position ASC',
                car_id
            )
            return [dict(r) for r in rows]

    async def count_car_media(self, car_id: int) -> int:
        """Количество доп. медиафайлов машины"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                'SELECT COUNT(*) FROM car_media WHERE car_id = $1', car_id
            )

    async def delete_car_media(self, car_id: int):
        """Удалить все медиафайлы машины"""
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM car_media WHERE car_id = $1', car_id)

    # ============= МЕДИА ПРЕДЛОЖЕНИЙ =============

    async def add_suggestion_media(self, suggestion_id: int, file_id: str, media_type: str = 'photo'):
        """Добавить медиафайл к предложению"""
        async with self.pool.acquire() as conn:
            position = await conn.fetchval(
                'SELECT COALESCE(MAX(position), -1) + 1 FROM suggestion_media WHERE suggestion_id = $1',
                suggestion_id
            )
            await conn.execute('''
                INSERT INTO suggestion_media (suggestion_id, file_id, media_type, position)
                VALUES ($1, $2, $3, $4)
            ''', suggestion_id, file_id, media_type, position)

    async def get_suggestion_media(self, suggestion_id: int) -> List[Dict]:
        """Получить все медиафайлы предложения"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                'SELECT * FROM suggestion_media WHERE suggestion_id = $1 ORDER BY position ASC',
                suggestion_id
            )
            return [dict(r) for r in rows]


pg_db = PostgresDatabase()
