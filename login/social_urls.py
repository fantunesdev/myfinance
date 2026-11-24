from django.urls import path

from login import social_views

app_name = 'social'
urlpatterns = [
    path('preference/', social_views.update_preference, name='preference'),
    path('login/<str:backend>/', social_views.begin, name='begin'),
    path('complete/<str:backend>/', social_views.complete, name='complete'),
    path('disconnect/<str:backend>/<int:association_id>/', social_views.disconnect, name='disconnect_individual'),
]
