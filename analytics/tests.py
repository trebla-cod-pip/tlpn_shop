from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase
from django.utils import timezone

from analytics.middleware import AnalyticsMiddleware
from analytics.models import TrackingSession, hash_ip


class AnalyticsMiddlewareSessionRotationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = AnalyticsMiddleware(lambda request: None)

    def _build_request(self, path='/'):
        request = self.factory.get(path, HTTP_USER_AGENT='pytest-agent')
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()
        request.user = AnonymousUser()
        return request

    def _create_tracking_session(self, session_key):
        return TrackingSession.objects.create(
            session_key=session_key,
            ip_hash=hash_ip('127.0.0.1'),
            user_agent='pytest-agent',
            device_type='desktop',
            landing_page='http://testserver/',
        )

    def test_active_session_reuses_existing_tracking_session(self):
        request = self._build_request('/')
        current_key = request.session.session_key
        tracked = self._create_tracking_session(current_key)

        resolved = self.middleware._get_or_create_session(request)

        self.assertEqual(resolved.id, tracked.id)
        self.assertEqual(resolved.session_key, current_key)
        self.assertEqual(TrackingSession.objects.count(), 1)

    def test_expired_session_rotates_key_and_creates_new_tracking_session(self):
        request = self._build_request('/')
        current_key = request.session.session_key
        tracked = self._create_tracking_session(current_key)

        stale_at = timezone.now() - timedelta(seconds=settings.ANALYTICS_SESSION_TIMEOUT + 5)
        TrackingSession.objects.filter(pk=tracked.pk).update(last_activity=stale_at)

        resolved = self.middleware._get_or_create_session(request)

        tracked.refresh_from_db()
        self.assertFalse(tracked.is_active)
        self.assertIsNotNone(tracked.ended_at)
        self.assertNotEqual(resolved.session_key, current_key)
        self.assertEqual(TrackingSession.objects.filter(session_key=current_key).count(), 1)
        self.assertEqual(TrackingSession.objects.count(), 2)
