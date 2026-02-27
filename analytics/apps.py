from django.contrib.admin import AdminSite
from django.utils.html import format_html


# Добавляем ссылку на дашборд в навигацию админки
original_header = AdminSite.each_context

def custom_each_context(self, request):
    context = original_header(self, request)
    context['analytics_dashboard_url'] = '/analytics/dashboard-ui/'
    return context

AdminSite.each_context = custom_each_context

# Добавляем кнопку в template
from django.conf import settings

ANALYTICS_DASHBOARD_LINK = format_html(
    '<a href="/analytics/dashboard-ui/" style="background:#417690;color:white;padding:10px 15px;border-radius:4px;text-decoration:none;margin-left:10px;">📊 Дашборд</a>'
)
