from django.utils import timezone
from .models import Banner


def active_banners(request):
    """Добавляет активные баннеры в контекст всех шаблонов"""
    banners = Banner.objects.filter(
        is_active=True,
        show_on_desktop=True
    )

    # Фильтруем по датам
    now = timezone.now()
    banners = [b for b in banners if b.is_currently_active]

    # Сортируем по приоритету
    banners.sort(key=lambda x: x.priority, reverse=True)

    return {'active_banners': banners[:3]}  # Максимум 3 баннера