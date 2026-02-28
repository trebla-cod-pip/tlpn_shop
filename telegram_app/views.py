import hashlib
import hmac
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def validate_telegram_data(data: dict) -> bool:
    """
    Проверяет подлинность данных от Telegram WebApp
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return False

    # Получаем hash из данных
    received_hash = data.pop('hash', None)
    if not received_hash:
        return False

    # Сортируем данные и формируем строку для проверки
    data_check_string = '\n'.join(
        f'{key}={value}' for key, value in sorted(data.items())
    )

    # Создаём ключ подписи
    secret_key = hmac.new(
        b'WebAppData',
        settings.TELEGRAM_BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()

    # Вычисляем hash
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_hash, received_hash)


@csrf_exempt
def telegram_auth(request):
    """
    Эндпоинт для аутентификации через Telegram WebApp

    POST /telegram/auth/
    Body: initData (строка от Telegram)

    Returns:
        JSON с данными пользователя или ошибкой
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        init_data = data.get('initData', '')

        if not init_data:
            return JsonResponse({'error': 'No initData provided'}, status=400)

        # Парсим initData (формат: key1=value1&key2=value2...)
        from urllib.parse import parse_qs
        parsed_data = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(init_data).items()}

        # Проверяем подлинность
        if not validate_telegram_data(parsed_data.copy()):
            logger.warning("Неверная подпись Telegram данных")
            return JsonResponse({'error': 'Invalid Telegram data'}, status=401)

        # Извлекаем данные пользователя
        user_data = json.loads(parsed_data.get('user', '{}'))

        response_data = {
            'success': True,
            'user': {
                'id': user_data.get('id'),
                'first_name': user_data.get('first_name'),
                'last_name': user_data.get('last_name'),
                'username': user_data.get('username'),
                'language_code': user_data.get('language_code'),
            },
            'chat_instance': parsed_data.get('chat_instance'),
            'chat_type': parsed_data.get('chat_type'),
        }

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Ошибка аутентификации Telegram: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
def telegram_save_user(request):
    """
    Сохраняет/обновляет данные пользователя Telegram
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
        init_data = data.get('initData', '')
        user_data = data.get('user', {})

        if not user_data.get('id'):
            return JsonResponse({'error': 'User ID required'}, status=400)

        from store.models import TelegramUser

        tg_user, created = TelegramUser.objects.get_or_create(
            telegram_id=user_data['id'],
            defaults={
                'username': user_data.get('username', ''),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'language_code': user_data.get('language_code', ''),
                'is_premium': user_data.get('is_premium', False),
            }
        )

        if not created:
            tg_user.update_from_telegram(user_data)

        # Сохраняем chat_id из initData если есть
        if init_data:
            from urllib.parse import parse_qs
            parsed_data = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(init_data).items()}
            chat_instance = parsed_data.get('chat_instance')
            
            logger.info(f"chat_instance из initData: {chat_instance}")
            logger.info(f"Полный initData: {parsed_data}")
            logger.info(f"telegram_id пользователя: {user_data.get('id')}")

            if not tg_user.chat_id:
                # Используем telegram_id как chat_id для отправки сообщений
                # Это работает для личных сообщений с пользователем
                tg_user.chat_id = user_data['id']
                tg_user.save()
                logger.info(f"Сохранен chat_id {tg_user.chat_id} для пользователя {tg_user.telegram_id}")

        return JsonResponse({
            'success': True,
            'user_id': tg_user.telegram_id,
            'created': created,
            'chat_id': tg_user.chat_id,
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Ошибка сохранения пользователя Telegram: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@csrf_exempt
def webhook(request):
    """
    Webhook для Telegram бота
    
    POST /telegram/webhook/
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        update = json.loads(request.body)
        logger.info(f"Получен update от Telegram: {update.get('update_id')}")

        # Здесь будет логика обработки сообщений бота
        # Для Mini App основной функционал через WebApp

        return JsonResponse({'ok': True})

    except Exception as e:
        logger.error(f"Ошибка webhook: {e}")
        return JsonResponse({'ok': False, 'error': str(e)})
