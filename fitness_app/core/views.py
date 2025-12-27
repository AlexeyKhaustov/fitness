from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import get_object_or_404
from django.http import HttpResponseForbidden

from .models import UserProfile, Video, Category, SeoBlock


def home(request):
    categories = Category.objects.all()

    # Получаем активные SEO-блоки для главной
    seo_blocks = SeoBlock.objects.filter(
        is_active=True,
        show_on_home=True
    ).order_by('order')

    return render(request, 'core/home.html', {
        'categories': categories,
        'seo_blocks': seo_blocks,  # Добавляем в контекст
    })

@login_required
def profile(request):
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    return render(request, 'core/profile.html', {'user_profile': user_profile})

@login_required
def video_list(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if user_profile.subscription_active:
        videos = Video.objects.all()  # Платные и бесплатные для подписчиков
    else:
        videos = Video.objects.filter(is_free=True)  # Только бесплатные
    return render(request, 'core/video_list.html', {'videos': videos})


# def video_detail(request, video_id):
#     video = get_object_or_404(Video, id=video_id)
#
#     # Проверка аутентификации
#     if not request.user.is_authenticated:
#         # Используем redirect_to_login который сохраняет next параметр
#         return redirect_to_login(
#             request.get_full_path(),  # Важно: передаем текущий URL
#             login_url=reverse('account_login'),
#             redirect_field_name='next'
#         )
#
#     user_profile = UserProfile.objects.get(user=request.user)
#
#     # Проверка доступа к премиум видео
#     if not video.is_free and not user_profile.subscription_active:
#         return HttpResponseForbidden("Требуется подписка для просмотра этого видео")
#
#     # Увеличиваем просмотры
#     video.increment_views()
#
#     # Похожие видео
#     similar_videos = Video.objects.filter(
#         categories__in=video.categories.all()
#     ).exclude(id=video.id).distinct()[:6]
#
#     return render(request, 'core/video_detail.html', {
#         'video': video,
#         'similar_videos': similar_videos,
#         'user_profile': user_profile,
#     })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    videos = category.videos.all()

    # Для неавторизованных показываем только бесплатные
    if not request.user.is_authenticated:
        videos = videos.filter(is_free=True)
    else:
        # Используем get_or_create вместо get
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not user_profile.subscription_active:
            videos = videos.filter(is_free=True)

    return render(request, 'core/category_detail.html', {
        'category': category,
        'videos': videos,
    })


from django.shortcuts import get_object_or_404, render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView
from django.http import HttpResponseForbidden
from .models import UserProfile, Video


class VideoDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная страница видео.
    Простая версия без сложной обработки next параметра.
    """
    model = Video
    template_name = 'core/video_detail.html'
    context_object_name = 'video'
    pk_url_kwarg = 'video_id'

    # Базовые настройки LoginRequiredMixin
    login_url = '/accounts/login/'  # Редирект на страницу входа
    redirect_field_name = 'next'  # Параметр все равно передается стандартными средствами Django

    def dispatch(self, request, *args, **kwargs):
        """
        Проверяем доступ к видео.
        """
        # Стандартная проверка авторизации (обрабатывается LoginRequiredMixin)
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Проверяем доступ к конкретному видео
        try:
            video = Video.objects.get(id=kwargs.get('video_id'))

            # Если видео платное, проверяем подписку
            if not video.is_free:
                user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
                if not user_profile.subscription_active:
                    return HttpResponseForbidden(
                        "Для просмотра этого видео требуется активная подписка. "
                        "Вы можете оформить подписку в своем профиле."
                    )

        except Video.DoesNotExist:
            pass

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        Добавляем дополнительные данные в контекст.
        """
        context = super().get_context_data(**kwargs)
        video = self.object

        # Профиль пользователя
        user_profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        context['user_profile'] = user_profile

        # Похожие видео
        context['similar_videos'] = Video.objects.filter(
            categories__in=video.categories.all()
        ).exclude(id=video.id).distinct()[:6]

        return context

    def render_to_response(self, context, **response_kwargs):
        """
        Увеличиваем счетчик просмотров после успешного рендеринга.
        """
        response = super().render_to_response(context, **response_kwargs)

        if self.request.method == 'GET' and response.status_code == 200:
            self.object.increment_views()

        return response

    def render_to_response(self, context, **response_kwargs):
        """
        Увеличиваем счетчик просмотров после успешного рендеринга.
        """
        response = super().render_to_response(context, **response_kwargs)

        # Увеличиваем просмотры только для успешных GET запросов
        if self.request.method == 'GET' and response.status_code == 200:
            self.object.increment_views()

        return response
#
#
# class HomeView(TemplateView):
#     """Главная страница"""
#     template_name = 'core/home.html'
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#
#         # Категории
#         context['categories'] = Category.objects.all()
#
#         # SEO блоки
#         context['seo_blocks'] = SeoBlock.objects.filter(
#             is_active=True,
#             show_on_home=True
#         ).order_by('order')
#
#         # Примеры видео для неавторизованных
#         if not self.request.user.is_authenticated:
#             context['featured_videos'] = Video.objects.filter(
#                 is_free=True
#             ).order_by('-created_at')[:6]
#
#         return context
#
#
# class CategoryDetailView(ListView):
#     """Страница категории с видео"""
#     model = Video
#     template_name = 'core/category_detail.html'
#     context_object_name = 'videos'
#     paginate_by = 12
#
#     def get_queryset(self):
#         """Возвращает видео для категории с учетом подписки"""
#         self.category = get_object_or_404(Category, slug=self.kwargs['slug'])
#
#         queryset = self.category.videos.all()
#
#         # Фильтруем по доступности
#         if not self.request.user.is_authenticated:
#             queryset = queryset.filter(is_free=True)
#         else:
#             user_profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
#             if not user_profile.subscription_active:
#                 queryset = queryset.filter(is_free=True)
#
#         return queryset
#
#     def get_context_data(self, **kwargs):
#         """Добавляем категорию в контекст"""
#         context = super().get_context_data(**kwargs)
#         context['category'] = self.category
#         return context
#
#
# class ProfileView(LoginRequiredMixin, TemplateView):
#     """Страница профиля пользователя"""
#     template_name = 'core/profile.html'
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user_profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
#         context['user_profile'] = user_profile
#         return context
