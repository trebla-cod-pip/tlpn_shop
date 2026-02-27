from django.contrib import admin
from orders.models import Order, OrderItem, OrderStatus


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'price', 'total')
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_first_name', 'telegram_username', 'phone', 'total_amount', 'status', 'delivery_date', 'created_at')
    list_filter = ('status', 'delivery_date', 'created_at')
    search_fields = ('telegram_first_name', 'telegram_last_name', 'telegram_username', 'phone', 'email', 'delivery_address')
    readonly_fields = (
        'telegram_user_id', 'telegram_username', 'telegram_first_name', 'telegram_last_name',
        'total_amount', 'created_at', 'updated_at'
    )
    ordering = ('-created_at',)
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Клиент', {
            'fields': (
                'telegram_user_id', 'telegram_username', 
                'telegram_first_name', 'telegram_last_name',
                'phone', 'email'
            )
        }),
        ('Доставка', {
            'fields': ('delivery_address', 'delivery_date', 'delivery_time', 'comment')
        }),
        ('Заказ', {
            'fields': ('status', 'total_amount')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_confirmed', 'mark_as_delivered', 'mark_as_cancelled']
    
    @admin.action(description='Отметить как подтверждённый')
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status=OrderStatus.CONFIRMED)
    
    @admin.action(description='Отметить как доставленный')
    def mark_as_delivered(self, request, queryset):
        queryset.update(status=OrderStatus.DELIVERED)
    
    @admin.action(description='Отметить как отменённый')
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status=OrderStatus.CANCELLED)
