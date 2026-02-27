from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from analytics.models import (
    TrackingSession, TrackingEvent, AggregatedStat,
    RFMSegment, CustomerCohort, ProductMarginStat,
    ChannelPerformance, FunnelStep
)


# Ссылка на дашборд в админке
@admin.register(TrackingSession)
class TrackingSessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'user', 'traffic_source', 'started_at', 'last_activity', 'is_active')
    list_filter = ('is_active', 'device_type', 'utm_source', 'started_at')
    search_fields = ('session_key', 'user__username', 'user__email')
    readonly_fields = (
        'session_key', 'user', 'ip_hash', 'user_agent', 'device_type',
        'browser', 'os', 'utm_source', 'utm_medium', 'utm_campaign',
        'referer', 'landing_page', 'started_at', 'last_activity', 'ended_at'
    )
    date_hierarchy = 'started_at'
    
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_title'] = False
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(TrackingEvent)
class TrackingEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'event_name', 'session', 'url', 'created_at')
    list_filter = ('event_type', 'event_name', 'created_at')
    search_fields = ('url', 'page_title', 'event_name')
    readonly_fields = ('session', 'user', 'event_type', 'event_name', 'url', 'page_title', 'meta', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(AggregatedStat)
class AggregatedStatAdmin(admin.ModelAdmin):
    list_display = ('date', 'stat_type', 'granularity', 'value', 'count')
    list_filter = ('stat_type', 'granularity', 'date')
    search_fields = ('stat_type',)
    readonly_fields = ('date', 'granularity', 'stat_type', 'value', 'value_prev', 'count', 'dimensions')
    date_hierarchy = 'date'


@admin.register(RFMSegment)
class RFMSegmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'segment', 'rfm_score', 'recency', 'frequency', 'monetary', 'calculated_at')
    list_filter = ('segment', 'calculated_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = (
        'user', 'recency', 'frequency', 'monetary',
        'r_score', 'f_score', 'm_score', 'rfm_score',
        'segment', 'calculated_at', 'cohort_month'
    )
    date_hierarchy = 'calculated_at'


@admin.register(CustomerCohort)
class CustomerCohortAdmin(admin.ModelAdmin):
    list_display = ('cohort_month', 'customer_count', 'total_revenue')
    readonly_fields = ('cohort_month', 'customer_count', 'total_revenue', 'retention_rates')
    date_hierarchy = 'cohort_month'


@admin.register(ProductMarginStat)
class ProductMarginStatAdmin(admin.ModelAdmin):
    list_display = ('product', 'date', 'quantity_sold', 'revenue', 'margin', 'margin_percent', 'abc_category')
    list_filter = ('date', 'abc_category', 'xyz_category')
    search_fields = ('product__name',)
    readonly_fields = (
        'product', 'date', 'quantity_sold', 'revenue', 'cogs',
        'margin', 'margin_percent', 'abc_category', 'xyz_category'
    )
    date_hierarchy = 'date'


@admin.register(ChannelPerformance)
class ChannelPerformanceAdmin(admin.ModelAdmin):
    list_display = ('channel', 'date', 'sessions', 'orders', 'revenue', 'cost', 'romi', 'roas')
    list_filter = ('channel', 'date')
    search_fields = ('channel',)
    readonly_fields = (
        'channel', 'date', 'sessions', 'visitors', 'orders', 'revenue',
        'cost', 'romi', 'roas', 'cpa', 'conversion_rate'
    )
    date_hierarchy = 'date'


@admin.register(FunnelStep)
class FunnelStepAdmin(admin.ModelAdmin):
    list_display = ('session', 'step', 'reached_at')
    list_filter = ('step', 'reached_at')
    readonly_fields = ('session', 'step', 'reached_at', 'meta')
    date_hierarchy = 'reached_at'
