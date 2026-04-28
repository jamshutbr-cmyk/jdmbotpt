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
            
            # Добавляем дефолтные настройки
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
            
            return {
                'total_cars': total_cars,
                'total_views': total_views
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

    async def close(self):
        """Закрыть пул соединений"""
        if self.pool:
            await self.pool.close()


pg_db = PostgresDatabase()
