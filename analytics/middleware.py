"""
Middleware для трекинга пользовательских сессий и событий
Захватывает UTM-метки, referer, user agent
"""
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from analytics.models import TrackingSession, hash_ip, detect_device_type, parse_user_agent


class AnalyticsMiddleware:
    """
    Middleware для автоматического трекинга сессий
    
    Добавляет в settings.py:
    MIDDLEWARE = [
        ...
        'analytics.middleware.AnalyticsMiddleware',
    ]
    """
    
    # URL-паттерны для определения шагов воронки
    FUNNEL_PATTERNS = {
        1: ['/', '/home'],  # Главная
        2: ['/catalog', '/category', '/products'],  # Каталог
        3: ['/item/', '/product/'],  # Карточка товара
        4: ['/bag/', '/cart/'],  # Корзина
        5: ['/checkout'],  # Начало оформления
        6: ['/checkout/delivery'],  # Доставка
        7: ['/checkout/payment'],  # Оплата
        8: ['/checkout/complete', '/order/complete'],  # Заказ создан
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.session_timeout = getattr(settings, 'ANALYTICS_SESSION_TIMEOUT', 30 * 60)  # 30 мин
        
    def __call__(self, request):
        # Пропускаем если пользователь opt-out
        if request.COOKIES.get('analytics_optout'):
            return self.get_response(request)
        
        # Получаем или создаём сессию
        session = self._get_or_create_session(request)
        
        # Сохраняем session_id в request для доступа в views
        request.analytics_session = session
        
        # Определяем шаг воронки (только если сессия создана)
        if session:
            funnel_step = self._detect_funnel_step(request.path)
            if funnel_step:
                self._track_funnel_step(request, session, funnel_step)
            
            # Трекаем page view
            self._track_page_view(request, session)
        
        response = self.get_response(request)
        
        # Обновляем last_activity
        if session:
            TrackingSession.objects.filter(id=session.id).update(
                last_activity=timezone.now()
            )
        
        return response
    
    def _get_client_ip(self, request):
        """Получает IP адрес клиента"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    def _get_or_create_session(self, request):
        """Получает или создаёт сессию трекинга"""
        session_key = request.session.session_key

        # Если нет session_key, создаём сессию Django
        if not session_key:
            # Сохраняем что-то в сессию чтобы она создалась
            request.session['analytics_init'] = '1'
            session_key = request.session.session_key

        # Если всё ещё нет session_key, пробуем из cookie
        if not session_key:
            session_key = request.COOKIES.get('analytics_session_id')

        if not session_key:
            return None
        
        # Используем get_or_create для избежания гонки
        session, created = TrackingSession.objects.get_or_create(
            session_key=session_key,
            defaults={
                'user': request.user if request.user.is_authenticated else None,
                'ip_hash': hash_ip(self._get_client_ip(request)),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'device_type': detect_device_type(request.META.get('HTTP_USER_AGENT', '')),
                **parse_user_agent(request.META.get('HTTP_USER_AGENT', '')),
                **self._extract_utm_params(request),
                'landing_page': request.build_absolute_uri(),
            }
        )
        
        if not created:
            # Проверяем не истекла ли сессия
            if timezone.now() - session.last_activity > timedelta(seconds=self.session_timeout):
                # Сессия истекла, создаём новую
                session.is_active = False
                session.ended_at = timezone.now()
                session.save()
                
                # Создаём новую сессию
                session = TrackingSession.objects.create(
                    session_key=session_key,
                    user=request.user if request.user.is_authenticated else None,
                    ip_hash=hash_ip(self._get_client_ip(request)),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    device_type=detect_device_type(request.META.get('HTTP_USER_AGENT', '')),
                    **parse_user_agent(request.META.get('HTTP_USER_AGENT', '')),
                    **self._extract_utm_params(request),
                    landing_page=request.build_absolute_uri(),
                )
        
        return session
    
    def _extract_utm_params(self, request):
        """Извлекает UTM-параметры из запроса"""
        return {
            'utm_source': request.GET.get('utm_source', ''),
            'utm_medium': request.GET.get('utm_medium', ''),
            'utm_campaign': request.GET.get('utm_campaign', ''),
            'utm_term': request.GET.get('utm_term', ''),
            'utm_content': request.GET.get('utm_content', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
        }
    
    def _detect_funnel_step(self, path):
        """Определяет шаг воронки по URL"""
        path_lower = path.lower()
        for step, patterns in self.FUNNEL_PATTERNS.items():
            if any(pattern in path_lower for pattern in patterns):
                return step
        return None
    
    def _track_funnel_step(self, request, session, step):
        """Трекает шаг воронки"""
        from analytics.models import FunnelStep
        
        # Проверяем не был ли уже этот шаг
        existing = FunnelStep.objects.filter(
            session=session,
            step=step
        ).exists()
        
        if not existing:
            FunnelStep.objects.create(
                session=session,
                step=step,
                meta={'url': request.build_absolute_uri()}
            )
    
    def _track_page_view(self, request, session):
        """Трекает просмотр страницы"""
        from analytics.models import TrackingEvent
        
        # Не трекаем админку и статику
        if (request.path.startswith('/admin/') or 
            request.path.startswith('/static/') or
            request.path.startswith('/media/')):
            return
        
        TrackingEvent.objects.create(
            session=session,
            user=request.user if request.user.is_authenticated else None,
            event_type='page_view',
            event_name='page_view',
            url=request.build_absolute_uri(),
            page_title=getattr(request, 'page_title', ''),
            meta={
                'path': request.path,
                'method': request.method,
            }
        )
