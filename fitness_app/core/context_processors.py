from django.utils import timezone
from .models import Banner, SeoBlock, MarathonAccess, Marathon, UserProfile, Category


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


# Упрощенная версия marathon_stats
def marathon_stats(request):
    context = {}

    if request.user.is_authenticated:
        try:
            # ТОЛЬКО купленные марафоны
            purchased_count = MarathonAccess.objects.filter(
                user=request.user,
                is_active=True
            ).count()

            # Всего активных марафонов
            total_marathons = Marathon.objects.filter(is_active=True).count()

            context.update({
                'total_marathons': total_marathons,
                'user_accessible_marathons': purchased_count,  # Только купленные
                'purchased_marathons_count': purchased_count,
                'subscribed_marathons_count': 0,  # Всегда 0, т.к. марафоны не по подписке
            })

        except Exception as e:
            # Молча игнорируем ошибки при инициализации
            pass

    return context


def user_marathon_access(request):
    """ID марафонов, к которым есть доступ (для быстрой проверки)"""
    if not request.user.is_authenticated:
        return {'user_marathon_ids': []}

    # Из кэша или сессии можно брать
    marathon_ids = MarathonAccess.objects.filter(
        user=request.user,
        is_active=True
    ).values_list('marathon_id', flat=True)

    return {'user_marathon_ids': list(marathon_ids)}


def categories_processor(request):
    """Добавляет все категории в контекст всех шаблонов"""
    try:
        categories = Category.objects.all().order_by('name')
        return {'categories': categories}
    except Exception as e:
        # Если база данных еще не готова
        print(f"Ошибка при получении категорий: {e}")
        return {'categories': []}
