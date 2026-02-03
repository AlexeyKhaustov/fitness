from django.contrib import admin
from django.utils import timezone

from .models import UserProfile, Video, Category, Banner, SeoBlock, MarathonAccess, Marathon, VideoComment, \
    MarathonVideo


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'subscription_active')
    search_fields = ('full_name', 'user__username', 'phone')
    list_filter = ('subscription_active',)


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_free', 'views', 'allow_comments', 'allow_likes', 'created_at')
    list_filter = ('is_free', 'allow_comments', 'allow_likes', 'categories')
    list_editable = ('is_free', 'allow_comments', 'allow_likes')
    search_fields = ('title', 'description')
    filter_horizontal = ('categories',)
    readonly_fields = ('views', 'created_at')

    fieldsets = (
        ('Основное', {
            'fields': ('title', 'file', 'description', 'is_free', 'categories')
        }),
        ('Превью и длительность', {
            'fields': ('thumbnail', 'duration'),
            'description': 'Рекомендуемый размер превью: 1280×720px'
        }),
        ('Социальные функции', {
            'fields': ('allow_comments', 'allow_likes', 'allow_sharing'),
            'description': '⚠️ Для платных видео эти функции автоматически отключаются'
        }),
        ('Статистика', {
            'fields': ('views', 'created_at'),
            'classes': ('collapse',)
        }),
    )


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
    list_display = ('title', 'show_title', 'show_subtitle', 'is_active', 'priority', 'text_position', 'created_at')
    list_filter = ('is_active', 'show_title', 'show_subtitle', 'text_position', 'show_on_mobile', 'show_on_desktop')
    list_editable = ('is_active', 'priority', 'show_title', 'show_subtitle')
    search_fields = ('title', 'subtitle')

    fieldsets = (
        ('Основное', {
            'fields': ('title', 'subtitle', 'button_text', 'button_link', 'image', 'image_mobile')
        }),
        ('Управление отображением', {
            'fields': ('show_title', 'show_subtitle'),
            'description': 'Управление видимостью текстовых элементов баннера'
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


@admin.register(MarathonVideo)
class MarathonVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'marathon', 'order', 'views', 'created_at')
    list_filter = ('marathon',)
    search_fields = ('title', 'description')
    list_editable = ('order',)
    readonly_fields = ('views', 'created_at', 'updated_at')

    fieldsets = (
        ('Основное', {
            'fields': ('marathon', 'title', 'description', 'order')
        }),
        ('Файлы', {
            'fields': ('file', 'thumbnail'),
            'description': 'Рекомендуемый размер превью: 1280×720px'
        }),
        ('Длительность', {
            'fields': ('duration',),
            'description': 'Длительность в секундах'
        }),
        ('Статистика', {
            'fields': ('views', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Marathon)
class MarathonAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'is_active', 'is_featured',
                    'teaser_videos_count_display', 'marathon_videos_count_display',
                    'sales_count', 'created_at')
    list_filter = ('is_active', 'is_featured', 'category')
    list_editable = ('price', 'is_active', 'is_featured')
    search_fields = ('title', 'short_description', 'full_description')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('teaser_videos',)  # ← ИЗМЕНИЛИ
    readonly_fields = ('sales_count', 'created_at', 'updated_at',
                      'teaser_videos_count_display', 'marathon_videos_count_display',
                      'total_duration_display')

    def teaser_videos_count_display(self, obj):
        """Отображение количества тизерных видео"""
        return obj.teaser_videos_count()
    teaser_videos_count_display.short_description = 'Тизерных видео'

    def marathon_videos_count_display(self, obj):
        """Отображение количества эксклюзивных видео"""
        return obj.marathon_videos_count()
    marathon_videos_count_display.short_description = 'Эксклюзивных видео'

    def total_duration_display(self, obj):
        """Отображение общей длительности"""
        minutes = obj.get_duration_minutes()
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if hours > 0:
            return f"{hours} ч {remaining_minutes} мин"
        return f"{minutes} мин"
    total_duration_display.short_description = 'Общая длительность'

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'category', 'is_active', 'is_featured', 'order'),
            'description': '''
                <div style="background: #f0f7ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>📋 Основные настройки марафона</strong>
                </div>
            '''
        }),
        ('Цена и продажи', {
            'fields': ('price', 'sales_count'),
            'description': '''
                <div style="background: #fff3cd; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>💰 Цена и статистика</strong><br>
                • <strong>Цена</strong>: Стоимость разовой покупки марафона<br>
                • <strong>Продано</strong>: Количество покупок (автоматический счетчик)
                </div>
            '''
        }),
        ('Контент марафона', {
            'fields': ('short_description', 'full_description'),
            'description': '''
                <div style="background: #e7f6e7; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>📝 Описание для страницы марафона</strong><br>
                • <strong>Краткое описание</strong>: Отображается в карточках и вверху страницы<br>
                • <strong>Полное описание</strong>: Детальное описание программы марафона
                </div>
            '''
        }),
        ('Тизерные видео (бесплатные)', {
            'fields': ('teaser_videos',),
            'description': '''
                <div style="background: #d4edda; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>🎬 Тизерные видео</strong><br>
                • <strong>Бесплатные видео</strong> для ознакомления с марафоном<br>
                • Видны всем пользователям ДО покупки<br>
                • Ведут на страницы обычных видео<br>
                • Можно комментировать и ставить лайки<br>
                • <strong>Рекомендация</strong>: Добавьте 2-3 самых интересных видео
                </div>
            '''
        }),
        ('Визуальное оформление', {
            'fields': ('thumbnail', 'banner_color'),
            'classes': ('collapse',),
            'description': '''
                <div style="background: #e2e3e5; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>🎨 Визуальное оформление</strong><br>
                • <strong>Превью</strong>: Основное изображение марафона (рекомендуется 800×600px)<br>
                • <strong>Цвет баннера</strong>: HEX-код для градиента фона
                </div>
            '''
        }),
        ('Статистика и информация', {
            'fields': ('teaser_videos_count_display', 'marathon_videos_count_display',
                      'total_duration_display', 'created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': '''
                <div style="background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>📊 Статистика марафона</strong><br>
                • <strong>Тизерных видео</strong>: Бесплатные видео для ознакомления<br>
                • <strong>Эксклюзивных видео</strong>: Видео доступные после покупки<br>
                • <strong>Общая длительность</strong>: Суммарная длительность эксклюзивных видео
                </div>
            '''
        }),
    )

    actions = ['make_featured', 'make_unfeatured', 'reset_sales_count']

    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f'{queryset.count()} марафонов отмечены как рекомендуемые')

    make_featured.short_description = "⭐ Отметить как рекомендуемые"

    def make_unfeatured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f'{queryset.count()} марафонов убраны из рекомендуемых')

    make_unfeatured.short_description = "📌 Убрать из рекомендуемых"

    def reset_sales_count(self, request, queryset):
        queryset.update(sales_count=0)
        self.message_user(request, f'Счетчики продаж сброшены для {queryset.count()} марафонов')

    reset_sales_count.short_description = "🔄 Сбросить счетчики продаж"


@admin.register(MarathonAccess)
class MarathonAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'marathon', 'amount_paid', 'purchased_at',
                    'is_active', 'valid_until')
    list_filter = ('is_active', 'marathon', 'purchased_at')
    search_fields = ('user__username', 'user__email', 'marathon__title', 'payment_id')
    readonly_fields = ('purchased_at',)
    list_select_related = ('user', 'marathon')

    fieldsets = (
        ('Основное', {
            'fields': ('user', 'marathon', 'is_active')
        }),
        ('Платежная информация', {
            'fields': ('amount_paid', 'payment_id', 'valid_until')
        }),
        ('Системное', {
            'fields': ('purchased_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(VideoComment)
class VideoCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'is_like', 'text_preview', 'is_approved', 'created_at')
    list_filter = ('is_like', 'is_approved', 'video', 'created_at')
    search_fields = ('user__username', 'video__title', 'text')
    list_editable = ('is_approved',)
    actions = ['approve_comments', 'disapprove_comments', 'convert_to_like', 'convert_to_comment']

    def text_preview(self, obj):
        if obj.is_like:
            return '❤️ Лайк'
        return obj.text[:50] + ('...' if len(obj.text) > 50 else '')

    text_preview.short_description = 'Текст'

    def approve_comments(self, request, queryset):
        queryset.update(is_approved=True)
        self.message_user(request, f'{queryset.count()} комментариев одобрено')

    approve_comments.short_description = "✅ Одобрить выбранные"

    def disapprove_comments(self, request, queryset):
        queryset.update(is_approved=False)
        self.message_user(request, f'{queryset.count()} комментариев отклонено')

    disapprove_comments.short_description = "❌ Отклонить выбранные"

    def convert_to_like(self, request, queryset):
        for comment in queryset:
            if not comment.is_like:
                comment.is_like = True
                comment.text = ''
                comment.save()
        self.message_user(request, f'{queryset.count()} комментариев преобразованы в лайки')

    convert_to_like.short_description = "❤️ Преобразовать в лайки"

    def convert_to_comment(self, request, queryset):
        for comment in queryset:
            if comment.is_like:
                comment.is_like = False
                comment.text = 'Пользователь поставил лайк'
                comment.save()
        self.message_user(request, f'{queryset.count()} лайков преобразованы в комментарии')

    convert_to_comment.short_description = "💬 Преобразовать в комментарии"

    fieldsets = (
        ('Основное', {
            'fields': ('video', 'user', 'is_like', 'text', 'is_approved')
        }),
        ('Системное', {
            'fields': ('created_at', 'updated_at', 'is_edited'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'is_edited')
