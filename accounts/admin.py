from django.contrib import admin
from .models import CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'mobile', 'city', 'pincode']
    search_fields = ['user__username', 'mobile']