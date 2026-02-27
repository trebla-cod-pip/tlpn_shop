"""Создание суперпользователя"""
from django.contrib.auth import get_user_model

User = get_user_model()

if not User.objects.filter(username='trebla').exists():
    User.objects.create_superuser('trebla', 'trebla@example.com', 'KFCone1ove!12')
    print('✓ Суперпользователь создан: trebla / KFCone1ove!12')
else:
    print('ℹ Суперпользователь уже существует')
