from django.contrib import admin
from .models import UserProfile, Video

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'subscription_active')
    search_fields = ('full_name', 'user__username', 'phone')
    list_filter = ('subscription_active',)

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_free', 'description')
    search_fields = ('title', 'description')
    list_filter = ('is_free',)
    fields = ('title', 'file', 'description', 'is_free')  # Поля для редактирования