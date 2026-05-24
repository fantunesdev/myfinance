from django.contrib import admin

from investments.models import Asset, Broker, Investment, InvestmentTransaction


admin.site.register(Broker)
admin.site.register(Asset)
admin.site.register(Investment)
admin.site.register(InvestmentTransaction)
