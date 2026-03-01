# Generated migration to fix chat_id stored as string
from django.db import migrations

def fix_chat_id_as_string(apps, schema_editor):
    """Исправляет chat_id, сохранённые как строки"""
    TelegramUser = apps.get_model('store', 'TelegramUser')
    
    for user in TelegramUser.objects.all():
        if user.chat_id is not None:
            # Если chat_id - строка, пробуем конвертировать в int
            if isinstance(user.chat_id, str):
                try:
                    # Проверяем, не chat_instance ли это (слишком длинный или начинается с -)
                    if user.chat_id.startswith('-') or len(user.chat_id) > 15:
                        # Используем telegram_id вместо chat_id
                        user.chat_id = user.telegram_id
                    else:
                        user.chat_id = int(user.chat_id)
                    user.save()
                    print(f"Fixed chat_id for user {user.telegram_id}: {user.chat_id}")
                except (ValueError, TypeError):
                    # Если не удалось конвертировать, используем telegram_id
                    user.chat_id = user.telegram_id
                    user.save()
                    print(f"Reset chat_id for user {user.telegram_id} to telegram_id")


def reverse_func(apps, schema_editor):
    pass  # No reverse needed


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_product_cart_image_alter_product_tags'),
    ]

    operations = [
        migrations.RunPython(fix_chat_id_as_string, reverse_func),
    ]
