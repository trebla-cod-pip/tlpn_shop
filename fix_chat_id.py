#!/usr/bin/env python
"""
Скрипт для проверки и исправления chat_id в TelegramUser
Запуск: python fix_chat_id.py
"""
import os
import sys
import django

# Добавляем проект в path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from store.models import TelegramUser

def fix_chat_ids():
    """Исправляет chat_id, сохранённые как строки"""
    print("=== Проверка TelegramUser ===")
    
    users = TelegramUser.objects.all()
    print(f"Всего пользователей: {users.count()}")
    
    fixed_count = 0
    for user in users:
        print(f"\nUser ID: {user.telegram_id}")
        print(f"  Username: @{user.username or 'N/A'}")
        print(f"  Name: {user.first_name} {user.last_name}".strip())
        print(f"  chat_id: {user.chat_id} (type: {type(user.chat_id).__name__})")
        
        needs_fix = False
        new_chat_id = None
        
        if user.chat_id is None:
            print(f"  ⚠️ chat_id не установлен!")
            needs_fix = True
            new_chat_id = user.telegram_id
        elif isinstance(user.chat_id, str):
            print(f"  ⚠️ chat_id - строка!")
            needs_fix = True
            # Проверяем, не chat_instance ли это
            if user.chat_id.startswith('-') or len(user.chat_id) > 15:
                new_chat_id = user.telegram_id
                print(f"  → chat_instance detected, using telegram_id")
            else:
                try:
                    new_chat_id = int(user.chat_id)
                    print(f"  → конвертируем в int")
                except ValueError:
                    new_chat_id = user.telegram_id
                    print(f"  → не удалось конвертировать, используем telegram_id")
        elif isinstance(user.chat_id, int):
            print(f"  ✓ chat_id корректен")
        
        if needs_fix and new_chat_id is not None:
            user.chat_id = new_chat_id
            user.save()
            fixed_count += 1
            print(f"  ✓ Исправлено на: {user.chat_id}")
    
    print(f"\n=== Итого ===")
    print(f"Исправлено записей: {fixed_count}")
    return fixed_count


if __name__ == '__main__':
    try:
        fixed = fix_chat_ids()
        print(f"\nГотово! Исправлено {fixed} записей.")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
