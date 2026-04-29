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
            
            # Добавляем дефолтные настройки
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
            
            return {
                'total_cars': total_cars,
                'total_views': total_views
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


db = Database()
