from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem

admin.site.site_header = "Createch Hobbies — Orders"
admin.site.site_title  = "Createch Admin"
admin.site.index_title = "Order Management"


class OrderItemInline(admin.TabularInline):
    model         = OrderItem
    extra         = 0
    readonly_fields = ('product_id', 'product_name', 'product_slug', 'quantity', 'unit_price', 'subtotal')
    fields        = ('product_name', 'quantity', 'unit_price', 'subtotal')
    can_delete    = False

    def subtotal(self, obj):
        return f"KES {obj.subtotal:,.0f}"
    subtotal.short_description = "Subtotal"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display  = ('short_id', 'customer_name', 'customer_phone', 'total_fmt',
                     'status_badge', 'mpesa_receipt_number', 'created_at')
    list_filter   = ('status', 'created_at')
    search_fields = ('customer_name', 'customer_phone', 'mpesa_receipt_number',
                     'mpesa_checkout_request_id')
    readonly_fields = ('id', 'mpesa_checkout_request_id', 'mpesa_merchant_request_id',
                       'mpesa_receipt_number', 'mpesa_failure_reason', 'created_at', 'updated_at')
    inlines       = [OrderItemInline]
    ordering      = ('-created_at',)

    fieldsets = (
        ('Customer', {
            'fields': ('customer_name', 'customer_phone', 'delivery_address')
        }),
        ('Order', {
            'fields': ('id', 'status', 'total_amount', 'created_at', 'updated_at')
        }),
        ('M-Pesa', {
            'fields': ('mpesa_checkout_request_id', 'mpesa_merchant_request_id',
                       'mpesa_receipt_number', 'mpesa_failure_reason'),
            'classes': ('collapse',),
        }),
    )

    def short_id(self, obj):
        return str(obj.id)[:8].upper()
    short_id.short_description = "Order ID"

    def total_fmt(self, obj):
        return f"KES {obj.total_amount:,.0f}"
    total_fmt.short_description = "Total"

    def status_badge(self, obj):
        colours = {
            'pending':    '#f5be4d',
            'paid':       '#22c55e',
            'failed':     '#ef4444',
            'processing': '#3b82f6',
            'shipped':    '#8b5cf6',
            'delivered':  '#10b981',
            'cancelled':  '#6b7280',
        }
        colour = colours.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#000;padding:2px 10px;border-radius:999px;'
            'font-size:11px;font-weight:600;">{}</span>',
            colour, obj.get_status_display()
        )
    status_badge.short_description = "Status"
