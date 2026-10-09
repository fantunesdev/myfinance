from django.contrib import admin

# Register your models here.
from .models import AppConfig, Device, Notification, SubcategoryChartConfig


@admin.register(AppConfig)
class AppConfigAdmin(admin.ModelAdmin):
    list_display = ('enable_transaction_classifier',)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'token')
    readonly_fields = ('token',)
    search_fields = ('name', 'user__username')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('app', 'title', 'user', 'created_at')


@admin.register(SubcategoryChartConfig)
class SubcategoryChartConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'subcategory')
    list_filter = ('user', 'subcategory__category')
    search_fields = ('user__username', 'subcategory__description')
