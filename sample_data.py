"""
Скрипт для добавления тестовых данных в базу
ВНИМАНИЕ: Используй только для тестирования!
"""
import asyncio
from database import db

# Примеры JDM машин
SAMPLE_CARS = [
    {
        'brand': 'Toyota',
        'model': 'Supra MK4',
        'year': 1998,
        'description': 'Легендарная Toyota Supra четвертого поколения с двигателем 2JZ-GTE. Установлен турбо кит Garrett, выхлоп HKS, занижена на койловерах BC Racing.',
        'locations': 'Центр города по выходным, парковка ТЦ Мега',
        'photo_id': 'DEMO_PHOTO_1'  # В реальности нужен настоящий file_id
    },
    {
        'brand': 'Nissan',
        'model': 'Skyline R34 GT-R',
        'year': 2001,
        'description': 'Nissan Skyline R34 GT-R в оригинальном состоянии. Редкий экземпляр в цвете Bayside Blue. Двигатель RB26DETT.',
        'locations': 'Район Автозавода, встречи JDM клуба',
        'photo_id': 'DEMO_PHOTO_2'
    },
    {
        'brand': 'Honda',
        'model': 'NSX NA1',
        'year': 1992,
        'description': 'Honda NSX первого поколения. Алюминиевый кузов, двигатель V6 3.0L. Состояние близкое к идеальному.',
        'locations': 'Редко появляется в центре города',
        'photo_id': 'DEMO_PHOTO_3'
    },
    {
        'brand': 'Mazda',
        'model': 'RX-7 FD3S',
        'year': 1995,
        'description': 'Mazda RX-7 третьего поколения с роторным двигателем 13B-REW. Установлен одиночный турбо, интеркулер Trust.',
        'locations': 'Парковка у торгового центра, дрифт-встречи',
        'photo_id': 'DEMO_PHOTO_4'
    },
    {
        'brand': 'Nissan',
        'model': 'Silvia S15',
        'year': 2000,
        'description': 'Nissan Silvia S15 Spec-R. Двигатель SR20DET, полный дрифт-сетап. Аэродинамический обвес Vertex.',
        'locations': 'Дрифт-треки, автомобильные встречи',
        'photo_id': 'DEMO_PHOTO_5'
    },
    {
        'brand': 'Mitsubishi',
        'model': 'Lancer Evolution IX',
        'year': 2006,
        'description': 'Mitsubishi Lancer Evolution IX. Полный привод, турбированный 4G63. Тюнинг от HKS, мощность около 400 л.с.',
        'locations': 'Гоночные треки, городские улицы',
        'photo_id': 'DEMO_PHOTO_6'
    },
    {
        'brand': 'Subaru',
        'model': 'Impreza WRX STI',
        'year': 2004,
        'description': 'Subaru Impreza WRX STI в легендарной синей расцветке. Двигатель EJ257, полный привод.',
        'locations': 'Горные дороги, ралли-встречи',
        'photo_id': 'DEMO_PHOTO_7'
    },
    {
        'brand': 'Toyota',
        'model': 'AE86 Trueno',
        'year': 1986,
        'description': 'Toyota Corolla AE86 Trueno. Классика дрифта, задний привод, двигатель 4A-GE. Культовая машина из Initial D.',
        'locations': 'Горные серпантины, дрифт-события',
        'photo_id': 'DEMO_PHOTO_8'
    },
    {
        'brand': 'Nissan',
        'model': '350Z',
        'year': 2005,
        'description': 'Nissan 350Z (Z33) с двигателем VQ35DE V6. Задний привод, отличная база для дрифта и трека.',
        'locations': 'Городские улицы, автомобильные встречи',
        'photo_id': 'DEMO_PHOTO_9'
    },
    {
        'brand': 'Honda',
        'model': 'Civic Type R EK9',
        'year': 1998,
        'description': 'Honda Civic Type R первого поколения. Двигатель B16B с VTEC, передний привод. Легендарный хот-хэтч.',
        'locations': 'Кольцевые гонки, городские улицы',
        'photo_id': 'DEMO_PHOTO_10'
    }
]


async def add_sample_data():
    """Добавить тестовые данные"""
    print("\n" + "="*50)
    print("⚠️  ДОБАВЛЕНИЕ ТЕСТОВЫХ ДАННЫХ")
    print("="*50)
    print("\nВНИМАНИЕ: Этот скрипт добавит 10 тестовых машин в базу.")
    print("Фото будут заглушками (DEMO_PHOTO_X).")
    print("\nДля реального использования нужно:")
    print("1. Запустить бота")
    print("2. Добавить машины через админ-панель с настоящими фото")
    print("\nПродолжить? (y/n): ", end='')
    
    choice = input().strip().lower()
    
    if choice != 'y':
        print("\n❌ Отменено")
        return
    
    await db.init_db()
    
    print("\n[*] Добавляю тестовые данные...\n")
    
    added = 0
    for car_data in SAMPLE_CARS:
        try:
            car_id = await db.add_car(**car_data)
            print(f"✅ Добавлена: {car_data['brand']} {car_data['model']} (ID: {car_id})")
            added += 1
        except Exception as e:
            print(f"❌ Ошибка при добавлении {car_data['brand']} {car_data['model']}: {e}")
    
    print(f"\n[+] Успешно добавлено: {added} машин")
    print("\n" + "="*50)
    print("\n💡 Теперь можешь:")
    print("1. Запустить бота: python bot.py")
    print("2. Посмотреть статистику: python tools.py")
    print("3. Удалить тестовые данные и добавить реальные через бота")
    print("\n" + "="*50 + "\n")


async def clear_database():
    """Очистить базу данных"""
    print("\n" + "="*50)
    print("⚠️  ОЧИСТКА БАЗЫ ДАННЫХ")
    print("="*50)
    print("\nВНИМАНИЕ: Это удалит ВСЕ данные из базы!")
    print("Это действие нельзя отменить!")
    print("\nПродолжить? (yes/no): ", end='')
    
    choice = input().strip().lower()
    
    if choice != 'yes':
        print("\n❌ Отменено")
        return
    
    await db.init_db()
    
    import aiosqlite
    from config import DB_PATH
    
    async with aiosqlite.connect(DB_PATH) as database:
        await database.execute('DELETE FROM favorites')
        await database.execute('DELETE FROM cars')
        await database.commit()
    
    print("\n✅ База данных очищена")
    print("\n" + "="*50 + "\n")


async def main():
    """Главное меню"""
    while True:
        print("\n" + "="*50)
        print("🗄️  УПРАВЛЕНИЕ ТЕСТОВЫМИ ДАННЫМИ")
        print("="*50)
        print("\n1. ➕ Добавить тестовые данные (10 машин)")
        print("2. 🗑️  Очистить базу данных")
        print("3. ❌ Выход")
        print("\nВыбери действие (1-3): ", end='')
        
        choice = input().strip()
        
        if choice == '1':
            await add_sample_data()
        elif choice == '2':
            await clear_database()
        elif choice == '3':
            print("\n👋 До встречи!")
            break
        else:
            print("\n❌ Неверный выбор")


if __name__ == "__main__":
    asyncio.run(main())
