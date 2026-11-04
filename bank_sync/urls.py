from django.urls import path

from . import views

urlpatterns = [
    path("prepare/", views.prepare, name="pluggy_prepare"),
    path("faturas/", views.bills_page, name="pluggy_bills"),
    path("ledger/", views.ledger, name="pluggy_ledger"),
    path("state/", views.state, name="pluggy_state"),
    path("sync/", views.sync, name="pluggy_sync"),
    path("map/", views.map_cards, name="pluggy_map"),
    path("review/", views.review, name="pluggy_review"),
    path("predict/", views.predict, name="pluggy_predict"),
    path("preference/", views.preference, name="pluggy_preference"),
    path("details/<int:row_id>/", views.details, name="pluggy_details"),
]
