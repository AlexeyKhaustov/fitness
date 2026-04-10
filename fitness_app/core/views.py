import uuid
import logging
import json
from decouple import config

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse

from django.views.generic import DetailView
from django.views.decorators.http import require_POST

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden, JsonResponse, HttpResponseBadRequest, HttpResponse

from django.conf import settings
from django.core.mail import send_mail

from .decorators import full_access_required
from .forms import VideoCommentForm, ServiceRequestForm
from .models import (Category,
                     Marathon,
                     MarathonAccess,
                     MarathonVideo,
                     VideoComment,
                     UserProfile,
                     Video,
                     Service,
                     ServiceRequest,
                     DocumentVersion,
                     Document,
                     UserConsent,
                     UserSubscription,
                     Payment,
                     )

from yookassa import Configuration, Payment as YooPayment
from yookassa.domain.exceptions import BadRequestError, UnauthorizedError

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os

logger = logging.getLogger(__name__)

# Настройка ЮKassa (ключи из .env)
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY



def home(request):
    # categories = Category.objects.all()  # оставляем для других мест
    services = Service.objects.filter(is_active=True).order_by('order')
    return render(request, 'core/home.html', {
        'services': services,
        # 'categories': categories, добавлен через контекстный процессор
        # 'active_banners' и 'seo_blocks' добавлен через контекстный процессор
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


class VideoDetailView(LoginRequiredMixin, DetailView):
    """Детальная страница обычного видео (для категорий)"""
    model = Video
    template_name = 'core/video_detail.html'
    context_object_name = 'video'
    pk_url_kwarg = 'video_id'
    login_url = '/accounts/login/'
    redirect_field_name = 'next'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        video = Video.objects.get(id=kwargs.get('video_id'))

        if video.is_free:
            return super().dispatch(request, *args, **kwargs)

        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        if not user_profile.subscription_active:
            return HttpResponseForbidden(
                "Для просмотра этого видео требуется активная подписка."
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['hls_stream_url'] = self.object.hls_master_playlist if self.object.is_processed else None
        video = self.object

        user_profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        context['user_profile'] = user_profile

        # Похожие видео
        context['similar_videos'] = Video.objects.filter(
            categories__in=video.categories.all()
        ).exclude(id=video.id).distinct()[:6]

        # Комментарии и лайки (только для бесплатных видео)
        if video.is_free and video.allow_comments:
            context['comment_form'] = VideoCommentForm()

            # Получаем только корневые комментарии (без parent)
            context['comments'] = video.comments.filter(
                is_like=False,
                is_approved=True,
                parent__isnull=True  # Только корневые
            ).select_related('user').order_by('-created_at')[:20]

            # Проверяем, лайкал ли пользователь это видео
            if self.request.user.is_authenticated:
                context['user_liked'] = video.comments.filter(
                    user=self.request.user,
                    is_like=True
                ).exists()
            else:
                context['user_liked'] = False

        return context


@full_access_required
@login_required
@require_POST
def add_video_comment(request, video_id):
    """Добавить комментарий или ответ на комментарий"""
    video = get_object_or_404(Video, id=video_id)

    # Проверяем, что видео бесплатное и разрешены комментарии
    if not video.is_free or not video.allow_comments:
        return HttpResponseForbidden("Комментарии запрещены для этого видео")

    form = VideoCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.video = video
        comment.user = request.user

        # Обработка ответа на комментарий
        parent_id = form.cleaned_data.get('parent_id')
        if parent_id:
            try:
                parent_comment = VideoComment.objects.get(
                    id=parent_id,
                    video=video,
                    is_like=False
                )

                # ПРОВЕРКА: нельзя отвечать самому себе
                if parent_comment.user == request.user:
                    messages.error(request, 'Нельзя отвечать на свой собственный комментарий')
                    return redirect('video_detail', video_id=video_id)

                comment.parent = parent_comment
            except VideoComment.DoesNotExist:
                messages.error(request, 'Родительский комментарий не найден')
                return redirect('video_detail', video_id=video_id)

        comment.save()
        messages.success(request, 'Комментарий добавлен!')
    else:
        for error in form.errors.get('text', []):
            messages.error(request, error)

    return redirect('video_detail', video_id=video_id)


def get_comment_json(request, comment_id):
    """Получить комментарий в формате JSON"""
    comment = get_object_or_404(VideoComment, id=comment_id, is_approved=True)

    return JsonResponse({
        'id': comment.id,
        'username': comment.user.username,
        'user_initial': comment.user.username[:1].upper(),
        'text': comment.text,
        'text_short': comment.text[:100] + ('...' if len(comment.text) > 100 else ''),
        'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
        'replies_count': comment.replies_count()
    })


@full_access_required
@login_required
@require_POST
def toggle_video_like(request, video_id):
    """Поставить/убрать лайк видео"""
    video = get_object_or_404(Video, id=video_id)

    # Проверяем, что видео бесплатное и разрешены лайки
    if not video.is_free or not video.allow_likes:
        return JsonResponse({'error': 'Лайки запрещены для этого видео'}, status=403)

    # Проверяем, не лайкал ли уже
    existing_like = VideoComment.objects.filter(
        video=video,
        user=request.user,
        is_like=True
    ).first()

    if existing_like:
        # Удаляем лайк
        existing_like.delete()
        liked = False
    else:
        # Добавляем лайк
        VideoComment.objects.create(
            video=video,
            user=request.user,
            is_like=True,
            text=''  # Пустой текст для лайка
        )
        liked = True

    return JsonResponse({
        'liked': liked,
        'likes_count': video.likes_count(),
        'comments_count': video.comments_count()
    })


def marathon_video_detail(request, marathon_slug, video_id):
    """Детальная страница видео марафона"""
    marathon = get_object_or_404(Marathon, slug=marathon_slug, is_active=True)
    video = get_object_or_404(MarathonVideo, id=video_id, marathon=marathon)

    # Проверяем доступ к марафону
    has_access = False
    if request.user.is_authenticated:
        marathon_access = MarathonAccess.objects.filter(
            user=request.user,
            marathon=marathon,
            is_active=True
        ).first()

        if marathon_access and marathon_access.is_valid():
            has_access = True

    if not has_access:
        return HttpResponseForbidden(
            "Для просмотра этого видео требуется покупка марафона."
        )

    # Увеличиваем просмотры
    video.increment_views()

    # Похожие видео в этом марафоне
    similar_videos = MarathonVideo.objects.filter(
        marathon=marathon
    ).exclude(id=video.id).order_by('order')[:6]

    # Считаем общее количество видео в марафоне
    marathon_videos_count = marathon.marathon_videos.count()

    # Получаем порядковый номер текущего видео
    video_order = video.order if video.order else MarathonVideo.objects.filter(
        marathon=marathon,
        id__lt=video.id
    ).count() + 1

    return render(request, 'core/marathon_video_detail.html', {
        'marathon': marathon,
        'video': video,
        'similar_videos': similar_videos,
        'has_access': has_access,
        'marathon_videos_count': marathon_videos_count,  # ← ДОБАВИЛИ
        'video_order': video_order,
    })


def marathon_list(request):
    """
    Список всех марафонов
    """
    marathons = Marathon.objects.filter(is_active=True).order_by('order')

    # Получаем доступы текущего пользователя
    user_marathon_access = {}
    user_has_active_subscription = False

    if request.user.is_authenticated:
        # Доступы к марафонам
        accesses = MarathonAccess.objects.filter(
            user=request.user,
            is_active=True
        ).select_related('marathon')

        for access in accesses:
            if access.is_valid():
                user_marathon_access[access.marathon_id] = True

        # Активная подписка
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            user_has_active_subscription = user_profile.subscription_active
        except UserProfile.DoesNotExist:
            pass

    return render(request, 'core/marathon_list.html', {
        'marathons': marathons,
        'user_marathon_access': user_marathon_access,
        'user_has_active_subscription': user_has_active_subscription,
    })


def marathon_detail(request, slug):
    marathon = get_object_or_404(
        Marathon.objects.prefetch_related(
            'teaser_videos', 'teaser_videos__categories', 'marathon_videos'
        ),
        slug=slug,
        is_active=True
    )

    has_access = False
    access_obj = None
    if request.user.is_authenticated:
        access_obj = MarathonAccess.objects.filter(
            user=request.user,
            marathon=marathon,
            is_active=True
        ).first()
        has_access = access_obj and access_obj.is_valid()

    # Если доступа нет, проверяем наличие pending-платежа и его статус в YKassa
    if not has_access and request.user.is_authenticated:
        pending_payment = Payment.objects.filter(
            user=request.user,
            marathon=marathon,
            status='pending'
        ).first()
        if pending_payment and pending_payment.payment_id:
            try:
                yoo_payment = YooPayment.find_one(pending_payment.payment_id)
                if yoo_payment:
                    if yoo_payment.status == 'waiting_for_capture':
                        # Подтверждаем платёж
                        captured = YooPayment.capture(pending_payment.payment_id)
                        yoo_payment = captured
                        logger.info(f"Платёж {pending_payment.id} подтверждён, статус: {yoo_payment.status}")
                    if yoo_payment.status == 'succeeded':
                        # Открываем доступ
                        pending_payment.status = 'succeeded'
                        pending_payment.save()
                        access, _ = MarathonAccess.objects.get_or_create(
                            user=request.user,
                            marathon=marathon,
                            defaults={
                                'amount_paid': pending_payment.amount,
                                'payment_id': pending_payment.payment_id,
                                'is_active': True,
                            }
                        )
                        marathon.increment_sales()
                        messages.success(request, 'Оплата прошла успешно! Доступ открыт.')
                        has_access = True
                    elif yoo_payment.status == 'canceled':
                        pending_payment.status = 'canceled'
                        pending_payment.save()
                        messages.warning(request, 'Платёж был отменён.')
            except Exception as e:
                logger.error(f"Ошибка при проверке pending-платежа: {e}", exc_info=True)

    # Если до сих пор нет доступа и есть параметр payment_id (старый fallback)
    payment_id = request.GET.get('payment_id')
    if payment_id and not has_access and request.user.is_authenticated:
        try:
            payment = Payment.objects.get(id=payment_id, user=request.user, status='pending')
            if payment.payment_id:
                yoo_payment = YooPayment.find_one(payment.payment_id)
                logger.info(f"Fallback: checking payment {payment.payment_id}, status={yoo_payment.status if yoo_payment else 'None'}")
                if yoo_payment:
                    if yoo_payment.status == 'waiting_for_capture':
                        captured = YooPayment.capture(payment.payment_id)
                        yoo_payment = captured
                        logger.info(f"Платёж подтверждён, новый статус: {yoo_payment.status}")
                    if yoo_payment.status == 'succeeded':
                        payment.status = 'succeeded'
                        payment.save()
                        access, _ = MarathonAccess.objects.get_or_create(
                            user=request.user,
                            marathon=marathon,
                            defaults={
                                'amount_paid': payment.amount,
                                'payment_id': payment.payment_id,
                                'is_active': True,
                            }
                        )
                        marathon.increment_sales()
                        messages.success(request, 'Оплата прошла успешно! Доступ открыт.')
                        has_access = True
                    elif yoo_payment.status == 'canceled':
                        payment.status = 'canceled'
                        payment.save()
                        messages.warning(request, 'Платёж был отменён.')
            else:
                logger.warning(f"Платёж {payment.id} не имеет внешнего payment_id")
        except Payment.DoesNotExist:
            logger.warning(f"Платёж {payment_id} не найден в БД")
        except Exception as e:
            logger.error(f"Ошибка при проверке платежа: {e}", exc_info=True)

    # Получаем видео для шаблона
    teaser_videos = marathon.teaser_videos.filter(is_free=True).order_by('created_at')[:6]
    marathon_videos = marathon.marathon_videos.all().order_by('order')

    return render(request, 'core/marathon_detail.html', {
        'marathon': marathon,
        'has_access': has_access,
        'access_obj': access_obj,
        'teaser_videos': teaser_videos,
        'marathon_videos': marathon_videos if has_access else [],
        'teaser_videos_count': teaser_videos.count(),
        'marathon_videos_count': marathon_videos.count(),
        'total_videos_count': marathon_videos.count(),
        'free_videos': teaser_videos,
        'paid_videos': marathon_videos if has_access else [],
        'all_videos': marathon_videos if has_access else [],
        'free_videos_count': teaser_videos.count(),
        'paid_videos_count': marathon_videos.count() if has_access else 0,
    })


# @full_access_required
# @login_required
# def marathon_purchase(request, slug):
#     """
#     Покупка марафона (упрощенная версия)
#     """
#     marathon = get_object_or_404(Marathon, slug=slug, is_active=True)
#
#     # Проверяем, не имеет ли уже доступ
#     if MarathonAccess.objects.filter(user=request.user, marathon=marathon).exists():
#         messages.info(request, f'У вас уже есть доступ к марафону "{marathon.title}"')
#         return redirect('marathon_detail', slug=slug)
#
#     # Проверяем подписку (если марафон входит в подписку)
#     try:
#         user_profile = UserProfile.objects.get(user=request.user)
#         if (user_profile.subscription_active and
#                 marathon.included_in_subscription):
#             messages.info(request,
#                           f'Марафон "{marathon.title}" уже доступен по вашей подписке!')
#             return redirect('marathon_detail', slug=slug)
#     except UserProfile.DoesNotExist:
#         pass
#
#     # Здесь должна быть интеграция с платежной системой
#     # Пока просто создаем доступ
#
#     # Увеличиваем счетчик продаж
#     marathon.increment_sales()
#
#     # Создаем доступ
#     MarathonAccess.objects.create(
#         user=request.user,
#         marathon=marathon,
#         amount_paid=marathon.price,
#         is_active=True,
#         valid_until=timezone.now() + timedelta(days=365)  # 1 год доступа
#     )
#
#     messages.success(request,
#                      f'Марафон "{marathon.title}" успешно приобретен! Сумма: {marathon.price}₽')
#
#     # Отправляем на страницу марафона
#     return redirect('marathon_detail', slug=slug)

@full_access_required
@login_required
def marathon_purchase(request, slug):
    marathon = get_object_or_404(Marathon, slug=slug, is_active=True)

    # Проверка на уже имеющийся доступ
    if MarathonAccess.objects.filter(user=request.user, marathon=marathon).exists():
        messages.info(request, f'У вас уже есть доступ к марафону "{marathon.title}"')
        return redirect('marathon_detail', slug=slug)

    # Проверка на незавершённый платёж
    existing_payment = Payment.objects.filter(
        user=request.user,
        marathon=marathon,
        status='pending'
    ).first()
    if existing_payment and existing_payment.confirmation_url:
        # Если есть сохранённая ссылка — перенаправляем на неё
        return redirect(existing_payment.confirmation_url)

    # Создаём запись о платеже в нашей базе
    payment = Payment.objects.create(
        user=request.user,
        marathon=marathon,
        amount=marathon.price,
        status='pending'
    )

    logger.info(f"Попытка создать платёж для марафона {marathon.id}, сумма {marathon.price}")
    idempotence_key = str(uuid.uuid4())

    if settings.DEBUG:
        return_url = f"http://localhost:8080{reverse('marathon_detail', args=[marathon.slug])}?payment_id={payment.id}"
    else:
        return_url = request.build_absolute_uri(
            reverse('marathon_detail', args=[marathon.slug]) + f'?payment_id={payment.id}'
        )

    try:
        yoo_payment = YooPayment.create({
            "amount": {
                "value": str(float(marathon.price)),
                "currency": "RUB"
            },
            "payment_method_data": {
                "type": "bank_card"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "description": f"Марафон «{marathon.title}»",
            "metadata": {
                "payment_id": payment.id,
                "user_id": request.user.id,
                "marathon_id": marathon.id
            }
        }, idempotence_key)

        # Сохраняем ID платежа и confirmation_url
        payment.payment_id = yoo_payment.id
        payment.confirmation_url = yoo_payment.confirmation.confirmation_url
        payment.save()

        return redirect(payment.confirmation_url)

    except (BadRequestError, UnauthorizedError) as e:
        logger.error(f"Ошибка при создании платежа: {e}", exc_info=True)
        messages.error(request, 'Не удалось создать платёж. Попробуйте позже.')
        return redirect('marathon_detail', slug=slug)


@csrf_exempt
def payment_webhook(request):
    """Обрабатывает уведомления от ЮKassa."""
    if request.method != 'POST':
        return HttpResponseBadRequest('Only POST allowed')

    # Получаем JSON из тела запроса
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return HttpResponseBadRequest('Invalid JSON')

    event = data.get('event')
    payment_object = data.get('object', {})

    # Извлекаем наш внутренний ID из метаданных
    metadata = payment_object.get('metadata', {})
    payment_id = metadata.get('payment_id')
    if not payment_id:
        # Не наш платёж — игнорируем
        return HttpResponse('OK')

    try:
        payment = Payment.objects.get(id=payment_id)
    except Payment.DoesNotExist:
        logger.warning(f"Платёж {payment_id} не найден в БД")
        return HttpResponse('OK')

    # Обработка событий
    if event == 'payment.succeeded':
        if payment.status != 'succeeded':
            payment.status = 'succeeded'
            payment.save()

            # Создаём доступ к марафону
            access, created = MarathonAccess.objects.get_or_create(
                user=payment.user,
                marathon=payment.marathon,
                defaults={
                    'amount_paid': payment.amount,
                    'payment_id': payment.payment_id,
                    'is_active': True,
                }
            )
            if not created:
                access.amount_paid = payment.amount
                access.payment_id = payment.payment_id
                access.is_active = True
                access.save()

            # Увеличиваем счётчик продаж
            payment.marathon.increment_sales()

            logger.info(f"Платёж {payment_id} успешно завершён. Доступ открыт.")

    elif event == 'payment.canceled':
        payment.status = 'canceled'
        payment.save()
        logger.info(f"Платёж {payment_id} отменён.")

    # Всегда возвращаем OK, чтобы ЮKassa не повторяла запрос
    return HttpResponse('OK')


@login_required
def my_marathons(request):
    """
    Мои марафоны (в профиле)
    """
    # Доступы по покупке
    marathon_accesses = MarathonAccess.objects.filter(
        user=request.user,
        is_active=True
    ).select_related('marathon').order_by('-purchased_at')

    # Марафоны по подписке
    subscribed_marathons = []
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if user_profile.subscription_active:
            subscribed_marathons = Marathon.objects.filter(
                is_active=True,
                included_in_subscription=True
            ).exclude(
                id__in=[ma.marathon_id for ma in marathon_accesses]
            )
    except UserProfile.DoesNotExist:
        pass

    return render(request, 'core/my_marathons.html', {
        'marathon_accesses': marathon_accesses,
        'subscribed_marathons': subscribed_marathons,
    })


def service_detail(request, slug):
    """Детальная страница услуги"""
    service = get_object_or_404(Service, slug=slug, is_active=True)

    # Если пользователь авторизован, предзаполняем форму данными из профиля
    initial_data = {}
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            initial_data = {
                'full_name': profile.full_name,
                'phone': profile.phone,
                'email': request.user.email,
            }
        except UserProfile.DoesNotExist:
            pass

    form = ServiceRequestForm(initial=initial_data)

    return render(request, 'core/service_detail.html', {
        'service': service,
        'form': form,
    })


@full_access_required
@login_required
@require_POST
def service_request_submit(request, slug):
    """Обработка отправки заявки"""
    service = get_object_or_404(Service, slug=slug, is_active=True)

    form = ServiceRequestForm(request.POST)
    if form.is_valid():
        # Создаём заявку
        service_request = form.save(commit=False)
        service_request.user = request.user
        service_request.service = service
        service_request.amount = service.price
        service_request.status = 'new'
        service_request.save()

        # --- Уведомления ---
        # получаем список email-адресов администраторов из переменной окружения
        # Получаем список email-адресов администраторов
        admin_emails_raw: str = config('ADMIN_EMAILS', default='')
        admin_emails: list[str] = [email.strip() for email in admin_emails_raw.split(',') if email.strip()]

        # Ссылка на заявку в админке
        admin_link = request.build_absolute_uri(
            reverse('admin:core_servicerequest_change', args=[service_request.id])
        )

        if admin_emails:
            send_mail(
                subject=f'Новая заявка #{service_request.id} на услугу "{service.name}"',
                message=(
                    f'Поступила новая заявка.\n\n'
                    f'Услуга: {service.name}\n'
                    f'Клиент: {service_request.full_name}\n'
                    f'Email: {service_request.email}\n'
                    f'Телефон: {service_request.phone}\n'
                    f'Дополнительная информация: {service_request.additional_info or "не указана"}\n\n'
                    f'Ссылка на заявку в админке: {admin_link}'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=True,
            )
        else:
            # Опционально: можно залогировать предупреждение
            import logging
            logger = logging.getLogger(__name__)
            logger.warning('ADMIN_EMAILS не задан, письмо администратору не отправлено')

        # Письмо администратору (каждому из списка)
        send_mail(
            subject=f'Новая заявка #{service_request.id} на услугу "{service.name}"',
            message=(
                f'Поступила новая заявка.\n\n'
                f'Услуга: {service.name}\n'
                f'Клиент: {service_request.full_name}\n'
                f'Email: {service_request.email}\n'
                f'Телефон: {service_request.phone}\n'
                f'Дополнительная информация: {service_request.additional_info or "не указана"}\n\n'
                f'Ссылка на заявку в админке: {admin_link}'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True,
        )

        # Письмо пользователю
        send_mail(
            subject=f'Ваша заявка #{service_request.id} принята',
            message=(
                f'Здравствуйте, {service_request.full_name}!\n\n'
                f'Ваша заявка на услугу "{service.name}" принята. Номер заявки: #{service_request.id}.\n'
                f'Администратор свяжется с вами в ближайшее время для уточнения деталей и выставления счёта.\n\n'
                f'С уважением, команда FitnessVideo'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[service_request.email],
            fail_silently=True,
        )
        # -------------------

        messages.success(request, 'Заявка успешно отправлена! Администратор свяжется с вами.')
        return redirect('service_detail', slug=service.slug)
    else:
        return render(request, 'core/service_detail.html', {
            'service': service,
            'form': form,
        })


@login_required
def my_service_requests(request):
    """Список заявок пользователя (мои услуги)"""
    requests = ServiceRequest.objects.filter(user=request.user).select_related('service').order_by('-created_at')
    return render(request, 'core/my_service_requests.html', {
        'requests': requests,
    })


@full_access_required
@login_required
def edit_profile(request):
    """Редактирование профиля пользователя"""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        if full_name and phone:
            profile.full_name = full_name
            profile.phone = phone
            profile.save()
            messages.success(request, 'Профиль обновлён')
            return redirect('profile')
        else:
            messages.error(request, 'Заполните все поля')

    return render(request, 'core/edit_profile.html', {
        'profile': profile,
    })


@login_required
def accept_consent(request):
    # Получаем все активные версии, на которые у пользователя ещё нет согласия
    active_versions = DocumentVersion.objects.filter(is_active=True).select_related('document')
    consented_version_ids = UserConsent.objects.filter(
        user=request.user,
        document_version__in=active_versions
    ).values_list('document_version_id', flat=True)

    pending_versions = [v for v in active_versions if v.id not in consented_version_ids]

    if not pending_versions:
        # Если нет ожидающих версий, просто редиректим
        next_url = request.session.pop('next_url', '/')
        return redirect(next_url)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            # Сохраняем согласие для каждой новой версии
            for version in pending_versions:
                UserConsent.objects.create(
                    user=request.user,
                    document_version=version,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            # Убираем флаг ограниченного доступа, если он был
            request.session.pop('restricted_access', None)
            messages.success(request, 'Спасибо! Вы приняли обновлённые условия.')
            next_url = request.session.pop('next_url', '/')
            return redirect(next_url)
        elif action == 'reject':
            # Проверяем, есть ли у пользователя активные обязательства
            has_active_obligations = (
                MarathonAccess.objects.filter(user=request.user, is_active=True).exists() or
                UserSubscription.objects.filter(user=request.user, is_active=True).exists()
            )
            if has_active_obligations:
                # Переводим в ограниченный режим
                request.session['restricted_access'] = True
                messages.warning(request, 'Вы отказались от новых условий. Доступ ограничен только ранее приобретённым материалам.')
                return redirect('profile')  # или на главную
            else:
                # Разлогиниваем
                from django.contrib.auth import logout
                logout(request)
                messages.info(request, 'Вы отказались от новых условий и были разлогинены.')
                return redirect('home')
        else:
            messages.error(request, 'Неверное действие.')

    context = {
        'pending_versions': pending_versions,
    }
    return render(request, 'core/accept_consent.html', context)


def document_page(request, doc_type):
    doc = get_object_or_404(Document, type=doc_type)
    version = doc.current_version
    if not version:
        # Если нет версии, показываем заглушку
        return render(request, 'core/document_page.html', {'title': doc.get_type_display(), 'text': 'Документ готовится.'})
    return render(request, 'core/document_page.html', {
        'title': doc.get_type_display(),
        'text': version.text,
        'version_date': version.created_at,
        'version_number': version.version_number
    })

@require_POST
@csrf_exempt  # только для админки, можно обойтись без декоратора, если добавить csrf_exempt
def upload_video_file(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if 'file' not in request.FILES:
        return JsonResponse({'error': 'No file provided'}, status=400)

    uploaded_file = request.FILES['file']
    # Генерируем путь, аналогичный тому, что в модели Video.upload_to
    import time
    from django.utils import timezone
    now = timezone.now()
    path = f'videos/{now.year}/{now.month:02d}/'
    filename = f"{int(time.time())}_{uploaded_file.name}"
    full_path = os.path.join(path, filename)

    saved_path = default_storage.save(full_path, ContentFile(uploaded_file.read()))

    return JsonResponse({
        'file_path': saved_path,
        'filename': filename,
    })
