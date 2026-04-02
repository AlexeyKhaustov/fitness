from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from fitness_app.core.models import Marathon

User = get_user_model()

class ChatRoom(models.Model):
    ROOM_TYPES = (
        ('general', 'Общий чат'),
        ('marathon', 'Чат марафона'),
    )
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='general')
    name = models.CharField(max_length=100, help_text="Название комнаты")
    slug = models.SlugField(unique=True, blank=True)
    marathon = models.OneToOneField(
        Marathon,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_room',
        help_text="Для чата марафона — ссылка на марафон"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            if self.room_type == 'general':
                self.slug = 'general'
            elif self.marathon:
                self.slug = f'marathon-{self.marathon.slug}'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('room_type', 'marathon')  # один общий чат, один чат на марафон


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.text[:50]}"
