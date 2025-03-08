from django.urls import path

from statement.views.portfolio.variable_income.sector import SectorView

sector_view = SectorView()

urlpatterns = [
    path('cadastrar/', sector_view.create, name='create_sector'),
    path('editar/<int:id>/', sector_view.update, name='update_sector'),
    path('remover/<int:id>/', sector_view.delete, name='delete_sector'),
]
