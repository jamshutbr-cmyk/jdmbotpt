"""
Дополнительные инструменты для работы с ботом
"""
import asyncio
import json
from datetime import datetime
from database import db


async def export_catalog_json():
    """Экспорт каталога в JSON"""
    cars = await db.get_all_cars(limit=10000)
    
    export_data = {
        'export_date': datetime.now().isoformat(),
        'total_cars': len(cars),
        'cars': []
    }
    
    for car in cars:
        export_data['cars'].append({
            'id': car['id'],
            'brand': car['brand'],
            'model': car['model'],
            'year': car.get('year'),
            'description': car.get('description'),
            'locations': car.get('locations'),
            'views': car.get('views', 0),
            'created_at': car.get('created_at')
        })
    
    filename = f"catalog_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Каталог экспортирован в {filename}")
    print(f"📊 Всего машин: {len(cars)}")
    return filename


async def show_statistics():
    """Показать детальную статистику"""
    stats = await db.get_stats()
    cars = await db.get_all_cars(limit=10000)
    
    print("\n" + "="*50)
    print("📊 СТАТИСТИКА БОТА")
    print("="*50)
    print(f"\n🚗 Всего машин: {stats['total_cars']}")
    print(f"👁  Всего просмотров: {stats['total_views']}")
    
    if stats['total_cars'] > 0:
        avg_views = stats['total_views'] / stats['total_cars']
        print(f"📈 Среднее просмотров: {avg_views:.1f}")
    
    # Топ-5 самых просматриваемых
    if cars:
        sorted_cars = sorted(cars, key=lambda x: x.get('views', 0), reverse=True)
        print("\n🏆 ТОП-5 САМЫХ ПОПУЛЯРНЫХ:")
        for i, car in enumerate(sorted_cars[:5], 1):
            print(f"  {i}. {car['brand']} {car['model']} - {car.get('views', 0)} просмотров")
    
    # Статистика по маркам
    brands = {}
    for car in cars:
        brand = car['brand']
        brands[brand] = brands.get(brand, 0) + 1
    
    if brands:
        print("\n🏭 СТАТИСТИКА ПО МАРКАМ:")
        sorted_brands = sorted(brands.items(), key=lambda x: x[1], reverse=True)
        for brand, count in sorted_brands[:10]:
            print(f"  {brand}: {count} машин")
    
    print("\n" + "="*50 + "\n")


async def backup_database():
    """Создать бэкап базы данных"""
    import shutil
    from config import DB_PATH
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"backup_{timestamp}.db"
    
    try:
        shutil.copy2(DB_PATH, backup_name)
        print(f"✅ Бэкап создан: {backup_name}")
        return backup_name
    except Exception as e:
        print(f"❌ Ошибка создания бэкапа: {e}")
        return None


async def main_menu():
    """Главное меню инструментов"""
    await db.init_db()
    
    while True:
        print("\n" + "="*50)
        print("🔧 ИНСТРУМЕНТЫ JDM CARS BOT")
        print("="*50)
        print("\n1. 📊 Показать статистику")
        print("2. 💾 Экспортировать каталог в JSON")
        print("3. 🔄 Создать бэкап базы данных")
        print("4. ❌ Выход")
        print("\nВыбери действие (1-4): ", end='')
        
        choice = input().strip()
        
        if choice == '1':
            await show_statistics()
        elif choice == '2':
            await export_catalog_json()
        elif choice == '3':
            await backup_database()
        elif choice == '4':
            print("\n👋 До встречи!")
            break
        else:
            print("\n❌ Неверный выбор. Попробуй снова.")
        
        input("\nНажми Enter для продолжения...")


if __name__ == "__main__":
    asyncio.run(main_menu())
