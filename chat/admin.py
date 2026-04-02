from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import ChatRoom, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    fields = ('user', 'text_preview', 'created_at', 'is_read')
    readonly_fields = ('user', 'text_preview', 'created_at', 'is_read')
    can_delete = False
    max_num = 10

    def text_preview(self, obj):
        return obj.text[:50] + ('…' if len(obj.text) > 50 else '')
    text_preview.short_description = 'Текст'


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'room_type_icon', 'slug', 'marathon_link', 'is_active', 'created_at', 'messages_count')
    list_filter = ('room_type', 'is_active', 'created_at')
    search_fields = ('name', 'slug', 'marathon__title')
    readonly_fields = ('slug', 'created_at', 'room_type_display', 'marathon_link', 'messages_count', 'messages_preview')
    list_editable = ('is_active',)
    list_per_page = 25

    fieldsets = (
        ('Основная информация', {
            'fields': ('room_type_display', 'name', 'slug', 'is_active'),
        }),
        ('Привязка к марафону', {
            'fields': ('marathon_link',),
        }),
        ('Статистика', {
            'fields': ('messages_count', 'messages_preview', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def room_type_icon(self, obj):
        icons = {
            'general': '<i class="fas fa-users" style="color: #3b82f6;"></i>',
            'marathon': '<i class="fas fa-fire" style="color: #f97316;"></i>',
        }
        return format_html(icons.get(obj.room_type, '<i class="fas fa-comment"></i>'))
    room_type_icon.short_description = 'Тип'

    def room_type_display(self, obj):
        return dict(ChatRoom.ROOM_TYPES).get(obj.room_type, obj.room_type)
    room_type_display.short_description = 'Тип комнаты'

    def marathon_link(self, obj):
        if obj.marathon:
            url = reverse('admin:core_marathon_change', args=[obj.marathon.id])
            return format_html('<a href="{}">{}</a>', url, obj.marathon.title)
        return '—'
    marathon_link.short_description = 'Марафон'

    def messages_count(self, obj):
        return obj.messages.count()
    messages_count.short_description = 'Сообщений'

    def messages_preview(self, obj):
        last_messages = obj.messages.order_by('-created_at')[:5]
        if not last_messages:
            return 'Нет сообщений'
        html = '<ul style="margin:0; padding-left:1rem;">'
        for msg in last_messages:
            html += f'<li><strong>{msg.user.username}</strong>: {msg.text[:50]}… <span style="color:#6b7280;">({msg.created_at.strftime("%d.%m %H:%M")})</span></li>'
        html += '</ul>'
        return format_html(html)
    messages_preview.short_description = 'Последние сообщения'

    class Media:
        css = {'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',)}


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room_link', 'user', 'text_short', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at', 'room__room_type')
    search_fields = ('text', 'user__username', 'user__email', 'room__name')
    readonly_fields = ('created_at', 'updated_at', 'room_link', 'user_link', 'full_text')  # только свои методы
    list_select_related = ('room', 'user')
    list_per_page = 50

    fieldsets = (
        ('Сообщение', {
            'fields': ('room_link', 'user_link', 'full_text', 'is_read')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def room_link(self, obj):
        url = reverse('admin:chat_chatroom_change', args=[obj.room.id])
        return format_html('<a href="{}">{}</a>', url, obj.room.name)
    room_link.short_description = 'Комната'

    def user_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'Пользователь'

    def text_short(self, obj):
        return obj.text[:70] + ('…' if len(obj.text) > 70 else '')
    text_short.short_description = 'Текст'

    def full_text(self, obj):
        return format_html('<div style="background:#f3f4f6; padding:10px; border-radius:5px;">{}</div>', obj.text)
    full_text.short_description = 'Полный текст'

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'Отмечено как прочитанные: {updated} сообщений.')
    mark_as_read.short_description = "Отметить как прочитанные"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'Отмечено как непрочитанные: {updated} сообщений.')
    mark_as_unread.short_description = "Отметить как непрочитанные"

    class Media:
        css = {'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',)}