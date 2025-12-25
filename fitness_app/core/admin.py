from django.contrib import admin
from django.utils import timezone

from .models import UserProfile, Video, Category, Banner, SeoBlock


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



@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'priority', 'text_position', 'created_at')
    list_filter = ('is_active', 'text_position', 'show_on_mobile', 'show_on_desktop')
    list_editable = ('is_active', 'priority')
    search_fields = ('title', 'subtitle')

    fieldsets = (
        ('Основное', {
            'fields': ('title', 'subtitle', 'button_text', 'button_link', 'image', 'image_mobile')
        }),
        ('Стилизация', {
            'fields': ('text_color', 'overlay_color', 'text_position'),
            'classes': ('collapse',)
        }),
        ('Управление показом', {
            'fields': ('is_active', 'priority', 'show_on_mobile', 'show_on_desktop', 'start_date', 'end_date'),
            'description': '<strong>Рекомендации по размерам:</strong><br>'
                           '• Десктоп: 1920×600px (рекомендуется)<br>'
                           '• Мобильные: 800×650px (если не указано, используется основное изображение)<br>'
                           '• Формат: JPG или PNG, оптимизировано для web'
        }),
    )

    class Media:
        css = {
            'all': ('admin/css/banner_admin.css',)
        }


@admin.register(SeoBlock)
class SeoBlockAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order', 'style', 'header_tag', 'show_on_home', 'created_at')
    list_editable = ('is_active', 'order', 'show_on_home', 'header_tag')
    list_filter = ('is_active', 'style', 'header_tag', 'show_on_home', 'show_on_category')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 20

    fieldsets = (
        ('Основное содержание', {
            'fields': ('title', 'slug', 'content'),
            'description': '''
                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>💡 Советы по контенту:</strong><br>
                • Используйте ключевые слова естественным образом<br>
                • Разбивайте текст на абзацы для читаемости<br>
                • Добавляйте списки для структурирования информации<br>
                • Допустимые HTML-теги: &lt;strong&gt;, &lt;em&gt;, &lt;a&gt;, &lt;ul&gt;, &lt;li&gt;, &lt;p&gt;, &lt;h3&gt;, &lt;h4&gt;
                </div>
            '''
        }),
        ('Визуальное оформление', {
            'fields': ('style', 'header_tag', 'background_color', 'text_color', 'image'),
            'classes': ('wide', 'collapse'),
            'description': '''
                <div style="background: #f0f7ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>🎨 Стили блоков:</strong><br>
                • <strong>default</strong>: темный фон, текст слева<br>
                • <strong>light</strong>: светлый фон, контрастный текст<br>
                • <strong>image_left</strong>: изображение слева, текст справа<br>
                • <strong>image_right</strong>: изображение справа, текст слева<br>
                • <strong>centered</strong>: текст по центру без изображения<br>
                • <strong>gradient</strong>: градиентный фон
                </div>

                <div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin-top: 10px;">
                <strong>📸 Рекомендации по изображениям:</strong><br>
                • Размер: 800×600px (оптимально)<br>
                • Формат: JPG или PNG<br>
                • Вес: ≤ 500KB для быстрой загрузки<br>
                • Соотношение сторон: 4:3 или 16:9
                </div>
            '''
        }),
        ('Управление показом', {
            'fields': ('is_active', 'order', 'show_on_home', 'show_on_category'),
            'classes': ('wide',),
            'description': '''
                <div style="background: #e7f6e7; padding: 10px; border-radius: 5px;">
                <strong>⚙️ Настройки отображения:</strong><br>
                • <strong>Порядок</strong>: чем меньше число, тем выше блок<br>
                • <strong>Активный</strong>: показывать/скрыть блок<br>
                • <strong>На главной</strong>: показывать на главной странице<br>
                • <strong>В категориях</strong>: показывать на страницах категорий
                </div>

                <div style="background: #fff; border-left: 4px solid #6f42c1; padding: 8px; margin-top: 10px;">
                <strong>Примеры порядка:</strong><br>
                • 0 - самый верхний блок<br>
                • 1 - второй блок<br>
                • 5 - средний приоритет<br>
                • 10 - самый нижний блок<br>
                • -1 - можно использовать отрицательные значения
                </div>
            '''
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['make_active', 'make_inactive', 'duplicate_seo_block']

    def make_active(self, request, queryset):
        """Активировать выбранные SEO-блоки"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} SEO-блоков активировано')

    make_active.short_description = "✅ Активировать выбранные блоки"

    def make_inactive(self, request, queryset):
        """Деактивировать выбранные SEO-блоки"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} SEO-блоков деактивировано')

    make_inactive.short_description = "🚫 Деактивировать выбранные блоки"

    def duplicate_seo_block(self, request, queryset):
        """Дублировать выбранные SEO-блоки"""
        for obj in queryset:
            obj.pk = None
            obj.slug = f"{obj.slug}-copy-{timezone.now().strftime('%Y%m%d')}"
            obj.title = f"{obj.title} (копия)"
            obj.order = obj.order + 1  # ставим после оригинала
            obj.save()
        self.message_user(request, f'Создано {queryset.count()} копий SEO-блоков')

    duplicate_seo_block.short_description = "📋 Дублировать выбранные блоки"

    def get_form(self, request, obj=None, **kwargs):
        """Кастомизация формы"""
        form = super().get_form(request, obj, **kwargs)

        # Добавляем подсказки для полей
        form.base_fields['header_tag'].help_text = 'Выберите HTML-тег для заголовка (H2 рекомендуется для SEO)'
        form.base_fields['background_color'].help_text = 'HEX-код цвета (#1f2937 - темно-серый по умолчанию)'
        form.base_fields['text_color'].help_text = 'HEX-код цвета текста (#ffffff - белый по умолчанию)'
        form.base_fields['order'].help_text = 'Блоки сортируются по возрастанию этого поля'

        # Валидатор для HEX цвета
        from django.core.validators import RegexValidator
        hex_validator = RegexValidator(
            regex='^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
            message='Введите корректный HEX-код цвета (например: #1f2937 или #fff)'
        )
        form.base_fields['background_color'].validators.append(hex_validator)
        form.base_fields['text_color'].validators.append(hex_validator)

        return form

    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
                'admin/css/seoblock_admin.css',
            )
        }
        js = (
            'admin/js/color_picker.js',  # Можно добавить пипетку для цветов
        )

