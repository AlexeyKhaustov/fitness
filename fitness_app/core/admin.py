from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse

from .models import (UserProfile,
                     Video,
                     Category,
                     Banner,
                     SeoBlock,
                     MarathonAccess,
                     Marathon,
                     VideoComment,
                     MarathonVideo,
                     ServiceRequest,
                     Service,
                     Document,
                     DocumentVersion,
                     UserConsent,
                     )


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
    list_display = ['name', 'slug', 'icon', 'color', 'has_image_display', 'is_featured', 'is_visible', 'videos_count']
    list_editable = ['icon', 'color', 'is_featured', 'is_visible']
    list_filter = ['is_featured', 'is_visible']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'description', 'tags']

    def videos_count(self, obj):
        return obj.videos.count()

    videos_count.short_description = 'Видео'

    def has_image_display(self, obj):
        if obj.has_image:
            return '✅ Есть картинка'
        return '📁 Только иконка'

    has_image_display.short_description = 'Картинка'

    def image_preview(self, obj):
        if obj.has_image:
            return format_html(
                '<img src="{}" style="max-height: 40px; max-width: 40px; border-radius: 5px;" />',
                obj.image.url
            )
        return '—'

    image_preview.short_description = 'Превью'

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'color', 'description', 'is_featured', 'is_visible'),
            'description': 'Основные настройки категории'
        }),
        ('Визуальное оформление', {
            'fields': ('image', 'icon', 'tags'),
            'description': '''
                <strong>🎨 Оформление категории</strong><br>
                • <strong>Картинка</strong>: приоритетный вариант (200×200px)<br>
                • <strong>Иконка</strong>: используется если нет картинки (например: dumbbell, running)<br>
                • <strong>Теги</strong>: через запятую, показываются на планшетах и ПК
            '''
        }),
    )

    actions = ['clear_images', 'make_featured', 'remove_featured']

    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)
        self.message_user(request, f'{queryset.count()} категорий отмечены как рекомендуемые')

    make_featured.short_description = "⭐ Отметить как рекомендуемые"

    def remove_featured(self, request, queryset):
        queryset.update(is_featured=False)
        self.message_user(request, f'{queryset.count()} категорий убраны из рекомендуемых')

    remove_featured.short_description = "📌 Убрать из рекомендуемых"

    def clear_images(self, request, queryset):
        count = 0
        for category in queryset:
            if category.image:
                category.image.delete(save=False)
                category.image = None
                category.save()
                count += 1
        self.message_user(request, f'Картинки удалены у {count} категорий')

    clear_images.short_description = "🗑️ Удалить картинки"


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'display_type', 'priority', 'text_position', 'created_at')
    list_filter = ('is_active', 'is_clickable', 'show_button', 'button_on_hover', 'text_position')
    list_editable = ('is_active', 'priority')
    search_fields = ('title', 'subtitle', 'button_text')
    readonly_fields = ('preview_desktop', 'preview_mobile', 'created_at', 'updated_at', 'display_type_info')

    # Новое поле для отображения типа
    def display_type(self, obj):
        if not obj.is_clickable and not obj.show_button:
            return "📷 Статичный"
        elif obj.is_clickable and not obj.show_button:
            return "🔗 Кликабельный"
        elif obj.is_clickable and obj.show_button and not obj.button_on_hover:
            return "🔼 Кнопка всегда"
        elif obj.is_clickable and obj.show_button and obj.button_on_hover:
            return "✨ Кнопка при наведении"
        return "—"

    display_type.short_description = "Тип баннера"

    # Новое поле для отображения типа в админке
    def display_type_info(self, obj):
        return format_html('''
            <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; border-left: 5px solid #10b981; margin: 10px 0;">
                <strong style="color: #065f46;">📋 Текущий тип баннера:</strong><br>
                <span style="font-size: 16px; font-weight: bold;">{}</span>
            </div>
        ''', self.display_type(obj))

    display_type_info.short_description = ""

    # Превью десктоп
    def preview_desktop(self, obj):
        if obj.image:
            return format_html(
                '<div style="border: 2px solid #ddd; border-radius: 8px; padding: 10px; margin: 10px 0; background: #f5f5f5;">'
                '<strong>📺 Десктоп версия:</strong><br>'
                '<img src="{}" style="max-width: 100%; height: auto; border-radius: 5px; margin-top: 10px; border: 1px solid #ccc;" />'
                '</div>',
                obj.image.url
            )
        return "—"

    preview_desktop.short_description = "Превью (десктоп)"

    # Превью мобильное
    def preview_mobile(self, obj):
        if obj.image_mobile:
            return format_html(
                '<div style="border: 2px solid #ddd; border-radius: 8px; padding: 10px; margin: 10px 0; background: #f5f5f5; max-width: 300px;">'
                '<strong>📱 Мобильная версия:</strong><br>'
                '<img src="{}" style="width: 100%; height: auto; border-radius: 5px; margin-top: 10px; border: 1px solid #ccc;" />'
                '</div>',
                obj.image_mobile.url
            )
        elif obj.image:
            return format_html(
                '<div style="border: 2px solid #ddd; border-radius: 8px; padding: 10px; margin: 10px 0; background: #f5f5f5; max-width: 300px;">'
                '<strong>📱 Будет использоваться десктопное:</strong><br>'
                '<img src="{}" style="width: 100%; height: auto; border-radius: 5px; margin-top: 10px; border: 1px solid #ccc;" />'
                '</div>',
                obj.image.url
            )
        return "—"

    preview_mobile.short_description = "Превью (мобильный)"

    fieldsets = (
        ('📝 Основное содержание', {
            'fields': ('title', 'subtitle'),
            'description': '''
                <div class="help-tip info" style="margin: 10px 0; padding: 15px; background: #eff6ff; border-radius: 8px; border-left: 5px solid #3b82f6;">
                <strong style="color: #1e40af;">Текстовое содержание баннера</strong><br>
                • Заголовок - основной текст баннера<br>
                • Подзаголовок - дополнительная информация
                </div>
            '''
        }),

        ('🖼️ Изображения баннера', {
            'fields': ('image', 'image_mobile'),
            'description': '''
                <div class="help-tip info" style="margin: 10px 0; padding: 15px; background: #eff6ff; border-radius: 8px; border-left: 5px solid #3b82f6;">
                <strong style="color: #1e40af;">Рекомендации по изображениям:</strong><br>
                • <strong>Десктоп:</strong> 1920×600px (рекомендуется)<br>
                • <strong>Мобильные:</strong> 800×650px (если не указано, используется десктопное)<br>
                • <strong>Формат:</strong> JPG или PNG<br>
                • <strong>Вес:</strong> ≤ 500KB для быстрой загрузки
                </div>
            '''
        }),

        ('👁️ Видимость элементов', {
            'fields': ('show_title', 'show_subtitle'),
            'description': '''
                <div class="help-tip warning" style="margin: 10px 0; padding: 15px; background: #fffbeb; border-radius: 8px; border-left: 5px solid #f59e0b;">
                <strong style="color: #92400e;">Управление видимостью текста</strong><br>
                • Можно скрыть заголовок<br>
                • Можно скрыть подзаголовок<br>
                • Полезно для чисто визуальных баннеров
                </div>
            '''
        }),

        ('🔗 Кнопка и ссылки', {
            'fields': ('button_text', 'button_link', 'click_link'),
            'description': '''
                <div class="help-tip success" style="margin: 10px 0; padding: 15px; background: #f0fdf4; border-radius: 8px; border-left: 5px solid #10b981;">
                <strong style="color: #065f46;">Настройки ссылок и кнопки</strong><br>
                • <strong>Текст кнопки</strong>: Оставьте пустым, если кнопка не нужна<br>
                • <strong>Ссылка кнопки</strong>: Куда ведет кнопка<br>
                • <strong>Ссылка баннера</strong>: Куда ведет клик по всему баннеру
                </div>
            '''
        }),

        ('🎯 Тип баннера и поведение', {
            'fields': ('display_type_info', 'is_clickable', 'show_button', 'button_on_hover'),
            'description': '''
                <div class="help-tip danger" style="margin: 10px 0; padding: 15px; background: #fef2f2; border-radius: 8px; border-left: 5px solid #ef4444;">
                <strong style="color: #991b1b;">Выберите тип баннера:</strong><br>

                <div style="display: grid; grid-template-columns: 1fr; gap: 12px; margin-top: 15px;">
                    <div style="padding: 15px; background: #dcfce7; border-radius: 8px; border: 2px solid #86efac; cursor: pointer;" 
                         onclick="document.getElementById('id_is_clickable').checked = true; document.getElementById('id_show_button').checked = true; document.getElementById('id_button_on_hover').checked = false;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                            <span style="font-size: 20px;">🔼</span>
                            <strong>Кнопка всегда видна</strong>
                        </div>
                        <div style="font-size: 13px; color: #065f46;">
                            • Баннер кликабельный<br>
                            • Кнопка отображается всегда<br>
                            • <em>Идеально для призывов к действию</em>
                        </div>
                    </div>

                    <div style="padding: 15px; background: #fef3c7; border-radius: 8px; border: 2px solid #fcd34d; cursor: pointer;" 
                         onclick="document.getElementById('id_is_clickable').checked = true; document.getElementById('id_show_button').checked = true; document.getElementById('id_button_on_hover').checked = true;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                            <span style="font-size: 20px;">✨</span>
                            <strong>Кнопка при наведении</strong>
                        </div>
                        <div style="font-size: 13px; color: #92400e;">
                            • Баннер кликабельный<br>
                            • Кнопка появляется при наведении мыши<br>
                            • <em>Чистый дизайн + функциональность</em>
                        </div>
                    </div>

                    <div style="padding: 15px; background: #e0e7ff; border-radius: 8px; border: 2px solid #a5b4fc; cursor: pointer;" 
                         onclick="document.getElementById('id_is_clickable').checked = true; document.getElementById('id_show_button').checked = false;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                            <span style="font-size: 20px;">🔗</span>
                            <strong>Весь баннер кликабелен</strong>
                        </div>
                        <div style="font-size: 13px; color: #1e40af;">
                            • Весь баннер - одна большая ссылка<br>
                            • Без кнопки<br>
                            • <em>Идеально для промо-баннеров</em>
                        </div>
                    </div>

                    <div style="padding: 15px; background: #f3f4f6; border-radius: 8px; border: 2px solid #d1d5db; cursor: pointer;" 
                         onclick="document.getElementById('id_is_clickable').checked = false; document.getElementById('id_show_button').checked = false;">
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
                            <span style="font-size: 20px;">📷</span>
                            <strong>Статичное изображение</strong>
                        </div>
                        <div style="font-size: 13px; color: #4b5563;">
                            • Не кликабельный<br>
                            • Без кнопки<br>
                            • <em>Для декоративных баннеров</em>
                        </div>
                    </div>
                </div>

                <div style="margin-top: 15px; font-size: 12px; color: #991b1b; padding: 8px; background: #fee2e2; border-radius: 6px;">
                    <strong>💡 Подсказка:</strong> Нажмите на любой блок выше для автоматической настройки
                </div>
                </div>
            '''
        }),

        ('🎨 Стилизация', {
            'fields': ('text_color', 'overlay_color', 'text_position'),
            'classes': ('wide', 'collapse'),
            'description': '''
                <div class="help-tip info" style="margin: 10px 0; padding: 15px; background: #eff6ff; border-radius: 8px; border-left: 5px solid #3b82f6;">
                <strong style="color: #1e40af;">Визуальное оформление</strong><br>
                • <strong>Цвет текста:</strong> Белый (#FFFFFF) по умолчанию<br>
                • <strong>Цвет оверлея:</strong> Затемнение поверх изображения<br>
                • <strong>Позиция текста:</strong> Слева, по центру или справа<br><br>

                <strong>Популярные цвета оверлея:</strong><br>
                • <code>rgba(0,0,0,0.4)</code> - стандартное затемнение<br>
                • <code>rgba(147,51,234,0.6)</code> - фиолетовый<br>
                • <code>rgba(59,130,246,0.5)</code> - синий<br>
                • <code>#00000000</code> - без затемнения
                </div>
            '''
        }),

        ('⚙️ Управление показом', {
            'fields': ('is_active', 'priority', 'show_on_mobile', 'show_on_desktop', 'start_date', 'end_date'),
            'description': '''
                <div class="help-tip warning" style="margin: 10px 0; padding: 15px; background: #fffbeb; border-radius: 8px; border-left: 5px solid #f59e0b;">
                <strong style="color: #92400e;">Настройки отображения</strong><br>
                • <strong>Активен:</strong> Включить/выключить баннер<br>
                • <strong>Приоритет:</strong> Чем выше число, тем выше баннер<br>
                • <strong>Показывать на мобильных:</strong> Отображение на телефонах<br>
                • <strong>Показывать на ПК:</strong> Отображение на компьютерах<br>
                • <strong>Дата начала/окончания:</strong> Автоматическое управление
                </div>
            '''
        }),

        ('👁️‍🗨️ Предпросмотр', {
            'fields': ('preview_desktop', 'preview_mobile'),
            'classes': ('wide', 'collapse'),
            'description': '''
                <div class="help-tip info" style="margin: 10px 0; padding: 15px; background: #eff6ff; border-radius: 8px; border-left: 5px solid #3b82f6;">
                <strong style="color: #1e40af;">Как будет выглядеть баннер</strong><br>
                • Здесь вы увидите предпросмотр баннера<br>
                • Убедитесь что изображения загружены правильно<br>
                • Проверьте читаемость текста
                </div>
            '''
        }),

        ('📊 Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_banners', 'deactivate_banners', 'make_clickable', 'make_static']

    def activate_banners(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'✅ Активировано {updated} баннеров')

    activate_banners.short_description = "✅ Активировать выбранные"

    def deactivate_banners(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'🚫 Деактивировано {updated} баннеров')

    deactivate_banners.short_description = "🚫 Деактивировать выбранные"

    def make_clickable(self, request, queryset):
        updated = queryset.update(is_clickable=True, show_button=True)
        self.message_user(request, f'🔗 Сделано кликабельными с кнопкой: {updated} баннеров')

    make_clickable.short_description = "🔗 Сделать с кнопкой"

    def make_static(self, request, queryset):
        updated = queryset.update(is_clickable=False, show_button=False)
        self.message_user(request, f'📷 Сделано статичными: {updated} баннеров')

    make_static.short_description = "📷 Сделать статичными"

    # Улучшаем форму
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # Улучшенные подсказки для полей
        form.base_fields['button_text'].help_text = 'Оставьте пустым, если кнопка не нужна'
        form.base_fields['click_link'].help_text = 'Куда ведет клик по всему баннеру (если кнопка скрыта)'
        form.base_fields['priority'].help_text = 'Чем выше число, тем выше приоритет. Баннеры сортируются по убыванию приоритета.'
        form.base_fields['overlay_color'].help_text = 'Например: rgba(0,0,0,0.4) для стандартного затемнения'

        return form

    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
                'admin/css/banner_admin.css',
            )
        }
        js = (
            'admin/js/banner_admin.js',
        )


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


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'order', 'is_active', 'image_preview']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'short_description', 'full_description']

    fieldsets = (
        ('Основное', {
            'fields': ('name', 'slug', 'price', 'order', 'is_active')
        }),
        ('Описание', {
            'fields': ('short_description', 'full_description')
        }),
        ('Визуальное оформление', {
            'fields': ('image', 'icon', 'color'),
            'description': 'Если загружена картинка, она будет использоваться вместо иконки'
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 40px; max-width: 40px; border-radius: 5px;" />', obj.image.url)
        return '—'
    image_preview.short_description = 'Превью'


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'service', 'amount', 'status', 'created_at')
    list_filter = ('status', 'service', 'created_at')
    search_fields = ('full_name', 'email', 'phone')
    list_editable = ('status',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Клиент', {
            'fields': ('user', 'full_name', 'email', 'phone', 'additional_info')
        }),
        ('Услуга и оплата', {
            'fields': ('service', 'amount', 'status', 'payment_id')
        }),
        ('Результат', {
            'fields': ('result_file', 'result_text', 'result_url')
        }),
        ('Системное', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_processing', 'mark_as_invoice_sent', 'mark_as_paid', 'mark_as_completed']

    def mark_as_processing(self, request, queryset):
        queryset.update(status='processing')
    mark_as_processing.short_description = "📋 В обработку"

    def mark_as_invoice_sent(self, request, queryset):
        queryset.update(status='invoice_sent')
    mark_as_invoice_sent.short_description = "💰 Счёт выставлен"

    def mark_as_paid(self, request, queryset):
        queryset.update(status='paid')
    mark_as_paid.short_description = "✅ Отметить оплаченными"

    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
    mark_as_completed.short_description = "🏁 Завершить"


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    fields = ['version_number', 'created_at', 'is_active', 'text']
    readonly_fields = ['created_at', 'version_number']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Добавлять версии можно только через отдельную кнопку (действие)
        return False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['type', 'current_version_link', 'create_new_version_button']
    inlines = [DocumentVersionInline]

    def current_version_link(self, obj):
        if obj.current_version:
            return format_html('<a href="{}">Версия {}</a>',
                               reverse('admin:core_documentversion_change', args=[obj.current_version.id]),
                               obj.current_version.version_number)
        return '—'

    current_version_link.short_description = 'Текущая версия'

    def create_new_version_button(self, obj):
        return format_html('<a class="button" href="{}">➕ Создать новую версию</a>',
                           reverse('create_document_version', args=[obj.id]))

    create_new_version_button.short_description = 'Действие'


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ['document', 'version_number', 'created_at', 'is_active', 'set_active_button']
    list_filter = ['document', 'is_active']
    readonly_fields = ['content_hash', 'created_at']
    fields = ['document', 'version_number', 'text', 'is_active', 'created_at', 'content_hash']

    def set_active_button(self, obj):
        if not obj.is_active:
            return format_html('<a class="button" href="{}">Сделать активной</a>',
                               reverse('set_active_version', args=[obj.id]))
        return '✓ Активна'

    set_active_button.short_description = ''

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            # Новая версия: увеличиваем номер
            last_version = DocumentVersion.objects.filter(document=obj.document).order_by('-version_number').first()
            obj.version_number = (last_version.version_number + 1) if last_version else 1
        super().save_model(request, obj, form, change)


@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ['user', 'document_version', 'consented_at', 'ip_address']
    list_filter = ['document_version__document', 'consented_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['consented_at', 'ip_address', 'user_agent']
