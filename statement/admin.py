from django.contrib import admin

# Register your models here.
from .models import AppConfig


@admin.register(AppConfig)
class AppConfigAdmin(admin.ModelAdmin):
	list_display = ('enable_transaction_classifier',)
