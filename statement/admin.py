from django.contrib import admin

# Register your models here.
from .models import AppConfig, Device, Notification


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
