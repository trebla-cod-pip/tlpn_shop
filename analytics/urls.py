from django.urls import path, include
from rest_framework.routers import DefaultRouter
from analytics import views
from analytics import dashboard_views

# REST API роутер
router = DefaultRouter()

urlpatterns = [
    # API для приёма событий от трекера
    path('track/', views.TrackingAPIView.as_view(), name='analytics-track'),
    
    # API для дашборда
    path('dashboard/', views.DashboardMetricsAPIView.as_view(), name='analytics-dashboard'),
    path('revenue-per-channel/', views.RevenuePerChannelAPIView.as_view(), name='analytics-revenue-channel'),
    path('funnel/', views.FunnelAPIView.as_view(), name='analytics-funnel'),
    path('top-products-margin/', views.TopProductsByMarginAPIView.as_view(), name='analytics-top-products'),
    path('rfm-segments/', views.RFMSegmentsAPIView.as_view(), name='analytics-rfm'),
    path('cohort-retention/', views.CohortRetentionAPIView.as_view(), name='analytics-cohort'),
    path('channel-romi/', views.ChannelROMIAPIView.as_view(), name='analytics-channel-romi'),
    
    # Dashboard Views (визуализация)
    path('dashboard-ui/', dashboard_views.analytics_dashboard, name='analytics-dashboard-ui'),
    path('chart/traffic/', dashboard_views.analytics_traffic_chart, name='analytics-traffic-chart'),
    path('chart/revenue/', dashboard_views.analytics_revenue_chart, name='analytics-revenue-chart'),
    path('chart/channels/', dashboard_views.analytics_channels_chart, name='analytics-channels-chart'),
    path('chart/funnel/', dashboard_views.analytics_funnel_chart, name='analytics-funnel-chart'),
    path('chart/rfm/', dashboard_views.analytics_rfm_chart, name='analytics-rfm-chart'),
    path('chart/products/', dashboard_views.analytics_products_chart, name='analytics-products-chart'),
]

urlpatterns += router.urls
