from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    subscription_active = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name

class Video(models.Model):
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='videos/')
    description = models.TextField()
    is_free = models.BooleanField(default=False)

    def __str__(self):
        return self.title

