from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('referrals/', views.referrals_view, name='referrals'),
    path('preferences/', views.customer_preferences, name='customer_preferences'),
    path('addresses/', views.address_book, name='address_book'),
]
