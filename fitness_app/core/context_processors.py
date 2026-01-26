from django.utils import timezone
from .models import Banner, SeoBlock


def active_banners(request):
    """Добавляет активные баннеры в контекст всех шаблонов"""
    try:
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
    except Exception as e:
        # Если база данных еще не готова или произошла ошибка
        # (например, при первом запуске до миграций)
        print(f"Ошибка при получении баннеров: {e}")
        return {'active_banners': []}


def active_seo_blocks(request):
    """Добавляет активные SEO-блоки в контекст главной страницы"""
    try:
        # Проверяем, что это главная страница
        if request.path != '/':
            return {'seo_blocks': []}

        # Получаем активные SEO-блоки для главной
        seo_blocks = SeoBlock.objects.filter(
            is_active=True,
            show_on_home=True
        ).order_by('order')[:10]  # Ограничиваем 10 блоками

        return {'seo_blocks': seo_blocks}
    except Exception as e:
        # Если модель еще не создана или произошла ошибка
        print(f"Ошибка при получении SEO-блоков: {e}")
        return {'seo_blocks': []}