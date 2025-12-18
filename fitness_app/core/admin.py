from django.contrib import admin
from .models import UserProfile, Video, Category

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'subscription_active')
    search_fields = ('full_name', 'user__username', 'phone')
    list_filter = ('subscription_active',)

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_free', 'get_categories')
    search_fields = ('title', 'description')
    list_filter = ('is_free', 'categories')
    fields = ('title', 'file', 'description', 'is_free', 'categories')

    def get_categories(self, obj):
        return ", ".join([c.name for c in obj.categories.all()])
    get_categories.short_description = 'Категории'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'color']
    prepopulated_fields = {'slug': ('name',)}  # авто-заполнение slug
    search_fields = ['name']
    list_editable = ['icon', 'color']  # можно менять прямо в списке

    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',)
        }

    def get_form(self, request, obj=None, **kwargs):
        help_texts = {
            'name': 'Название категории (например: Силовые тренировки)',
            'slug': 'Оставь пустым — заполнится автоматически',
            'icon': 'Иконка из Font Awesome 6 (например: dumbbell, running, heart-pulse, fire, lotus). Список: https://fontawesome.com/icons',
            'color': 'Градиент Tailwind (примеры: from-red-600 to-orange-600, from-green-600 to-teal-600)',
        }
        kwargs.update({'help_texts': help_texts})
        return super().get_form(request, obj, **kwargs)
