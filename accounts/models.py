from django.db import models
from django.contrib.auth.models import User


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=15)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, default='Jaunpur')
    pincode = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.user.username