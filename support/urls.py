from django.urls import path

from . import views

urlpatterns = [
    path('', views.support_list, name='support_list'),
    path('new/', views.support_create, name='support_create'),
    path('<int:ticket_id>/', views.support_detail, name='support_detail'),
]
