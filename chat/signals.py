from django.db.models.signals import post_save
from django.dispatch import receiver
from fitness_app.core.models import Marathon
from .models import ChatRoom

@receiver(post_save, sender=Marathon)
def create_marathon_chat_room(sender, instance, created, **kwargs):
    if created:
        ChatRoom.objects.get_or_create(
            room_type='marathon',
            marathon=instance,
            defaults={
                'name': f'Чат марафона: {instance.title}',
                'slug': f'marathon-{instance.slug}',
            }
        )