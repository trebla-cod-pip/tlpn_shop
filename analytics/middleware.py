"""
Middleware РґР»СЏ С‚СЂРµРєРёРЅРіР° РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёС… СЃРµСЃСЃРёР№ Рё СЃРѕР±С‹С‚РёР№
Р—Р°С…РІР°С‚С‹РІР°РµС‚ UTM-РјРµС‚РєРё, referer, user agent
"""
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from analytics.models import TrackingSession, hash_ip, detect_device_type, parse_user_agent


class AnalyticsMiddleware:
    """
    Middleware РґР»СЏ Р°РІС‚РѕРјР°С‚РёС‡РµСЃРєРѕРіРѕ С‚СЂРµРєРёРЅРіР° СЃРµСЃСЃРёР№
    
    Р”РѕР±Р°РІР»СЏРµС‚ РІ settings.py:
    MIDDLEWARE = [
        ...
        'analytics.middleware.AnalyticsMiddleware',
    ]
    """
    
    # URL-РїР°С‚С‚РµСЂРЅС‹ РґР»СЏ РѕРїСЂРµРґРµР»РµРЅРёСЏ С€Р°РіРѕРІ РІРѕСЂРѕРЅРєРё
    FUNNEL_PATTERNS = {
        1: ['/', '/home'],  # Р“Р»Р°РІРЅР°СЏ
        2: ['/catalog', '/category', '/products'],  # РљР°С‚Р°Р»РѕРі
        3: ['/item/', '/product/'],  # РљР°СЂС‚РѕС‡РєР° С‚РѕРІР°СЂР°
        4: ['/bag/', '/cart/'],  # РљРѕСЂР·РёРЅР°
        5: ['/checkout'],  # РќР°С‡Р°Р»Рѕ РѕС„РѕСЂРјР»РµРЅРёСЏ
        6: ['/checkout/delivery'],  # Р”РѕСЃС‚Р°РІРєР°
        7: ['/checkout/payment'],  # РћРїР»Р°С‚Р°
        8: ['/checkout/complete', '/order/complete'],  # Р—Р°РєР°Р· СЃРѕР·РґР°РЅ
    }
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.session_timeout = getattr(settings, 'ANALYTICS_SESSION_TIMEOUT', 30 * 60)  # 30 РјРёРЅ
        
    def __call__(self, request):
        # РџСЂРѕРїСѓСЃРєР°РµРј РµСЃР»Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ opt-out
        if request.COOKIES.get('analytics_optout'):
            return self.get_response(request)

        # Do not track analytics ingestion endpoint itself
        if request.path.startswith('/analytics/track'):
            return self.get_response(request)

        # Получаем или создаём сессию трекинга
        session = self._get_or_create_session(request)
        
        # РЎРѕС…СЂР°РЅСЏРµРј session_id РІ request РґР»СЏ РґРѕСЃС‚СѓРїР° РІ views
        request.analytics_session = session
        
        # РћРїСЂРµРґРµР»СЏРµРј С€Р°Рі РІРѕСЂРѕРЅРєРё (С‚РѕР»СЊРєРѕ РµСЃР»Рё СЃРµСЃСЃРёСЏ СЃРѕР·РґР°РЅР°)
        if session:
            funnel_step = self._detect_funnel_step(request.path)
            if funnel_step:
                self._track_funnel_step(request, session, funnel_step)
            
            # РўСЂРµРєР°РµРј page view
            self._track_page_view(request, session)
        
        response = self.get_response(request)
        
        # РћР±РЅРѕРІР»СЏРµРј last_activity
        if session:
            TrackingSession.objects.filter(id=session.id).update(
                last_activity=timezone.now()
            )
        
        return response
    
    def _get_client_ip(self, request):
        """РџРѕР»СѓС‡Р°РµС‚ IP Р°РґСЂРµСЃ РєР»РёРµРЅС‚Р°"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '0.0.0.0')
        return ip
    
    def _get_or_create_session(self, request):
        """РџРѕР»СѓС‡Р°РµС‚ РёР»Рё СЃРѕР·РґР°С‘С‚ СЃРµСЃСЃРёСЋ С‚СЂРµРєРёРЅРіР°"""
        session_key = request.session.session_key

        # Р•СЃР»Рё РЅРµС‚ session_key, СЃРѕР·РґР°С‘Рј СЃРµСЃСЃРёСЋ Django
        if not session_key:
            # РЎРѕС…СЂР°РЅСЏРµРј С‡С‚Рѕ-С‚Рѕ РІ СЃРµСЃСЃРёСЋ С‡С‚РѕР±С‹ РѕРЅР° СЃРѕР·РґР°Р»Р°СЃСЊ
            request.session['analytics_init'] = '1'
            session_key = request.session.session_key

        # Р•СЃР»Рё РІСЃС‘ РµС‰С‘ РЅРµС‚ session_key, РїСЂРѕР±СѓРµРј РёР· cookie
        if not session_key:
            session_key = request.COOKIES.get('analytics_session_id')

        if not session_key:
            return None
        
        # РСЃРїРѕР»СЊР·СѓРµРј get_or_create РґР»СЏ РёР·Р±РµР¶Р°РЅРёСЏ РіРѕРЅРєРё
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
            # РџСЂРѕРІРµСЂСЏРµРј РЅРµ РёСЃС‚РµРєР»Р° Р»Рё СЃРµСЃСЃРёСЏ
            if timezone.now() - session.last_activity > timedelta(seconds=self.session_timeout):
                # РЎРµСЃСЃРёСЏ РёСЃС‚РµРєР»Р°, СЃРѕР·РґР°С‘Рј РЅРѕРІСѓСЋ
                session.is_active = False
                session.ended_at = timezone.now()
                session.save()
                
                # РЎРѕР·РґР°С‘Рј РЅРѕРІСѓСЋ СЃРµСЃСЃРёСЋ
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
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Определяем если пользователь из Telegram Mini App
        is_telegram = 'Telegram' in user_agent
        
        return {
            'utm_source': request.GET.get('utm_source', '') or ('telegram' if is_telegram else ''),
            'utm_medium': request.GET.get('utm_medium', '') or ('mini_app' if is_telegram else ''),
            'utm_campaign': request.GET.get('utm_campaign', ''),
            'utm_term': request.GET.get('utm_term', ''),
            'utm_content': request.GET.get('utm_content', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
        }
    
    def _detect_funnel_step(self, path):
        """РћРїСЂРµРґРµР»СЏРµС‚ С€Р°Рі РІРѕСЂРѕРЅРєРё РїРѕ URL"""
        path_lower = path.lower()
        for step, patterns in self.FUNNEL_PATTERNS.items():
            if any(pattern in path_lower for pattern in patterns):
                return step
        return None
    
    def _track_funnel_step(self, request, session, step):
        """РўСЂРµРєР°РµС‚ С€Р°Рі РІРѕСЂРѕРЅРєРё"""
        from analytics.models import FunnelStep
        
        # РџСЂРѕРІРµСЂСЏРµРј РЅРµ Р±С‹Р» Р»Рё СѓР¶Рµ СЌС‚РѕС‚ С€Р°Рі
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
        """РўСЂРµРєР°РµС‚ РїСЂРѕСЃРјРѕС‚СЂ СЃС‚СЂР°РЅРёС†С‹"""
        from analytics.models import TrackingEvent
        
        # РќРµ С‚СЂРµРєР°РµРј Р°РґРјРёРЅРєСѓ Рё СЃС‚Р°С‚РёРєСѓ
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

