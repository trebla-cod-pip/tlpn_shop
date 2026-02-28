#!/usr/bin/env python
"""
Скрипт для обновления chat_id у существующих пользователей
Использует telegram_id как chat_id для отправки уведомлений
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from store.models import TelegramUser

def update_chat_ids():
    users = TelegramUser.objects.filter(chat_id__isnull=True)
    count = users.count()
    
    if count == 0:
        print("Все пользователи уже имеют chat_id")
        return
    
    print(f"Обновление {count} пользователей...")
    
    updated = 0
    for user in users:
        user.chat_id = str(user.telegram_id)
        user.save()
        updated += 1
        print(f"  ✓ {user.username or user.telegram_id}: chat_id = {user.chat_id}")
    
    print(f"\nГотово! Обновлено {updated} пользователей.")

if __name__ == '__main__':
    update_chat_ids()
