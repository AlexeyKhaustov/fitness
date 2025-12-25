from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, blank=True)
    subscription_active = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name


class Category(models.Model):
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField('URL', max_length=100, unique=True)
    icon = models.CharField('Иконка (Font Awesome)', max_length=50, default='film',
                            help_text='Например: dumbbell, running, heart-pulse, yoga, fire')
    color = models.CharField('Цвет (Tailwind)', max_length=300, default='bg-gradient-to-br from-purple-600 to-pink-600')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', args=[self.slug])


class Video(models.Model):
    title = models.CharField(max_length=100)
    file = models.FileField(upload_to='videos/')
    description = models.TextField()
    is_free = models.BooleanField(default=False)
    categories = models.ManyToManyField(
        Category,
        related_name='videos',
        blank=True,
        verbose_name='Категории'
    )

    def __str__(self):
        return self.title


class Banner(models.Model):
    title = models.CharField('Заголовок', max_length=200)
    subtitle = models.TextField('Подзаголовок', max_length=500, blank=True)
    button_text = models.CharField('Текст кнопки', max_length=50, default='Смотреть')
    button_link = models.CharField('Ссылка кнопки', max_length=200, default='/')
    image = models.ImageField('Изображение', upload_to='banners/')
    image_mobile = models.ImageField('Изображение (мобильное)', upload_to='banners/mobile/', blank=True)

    # Стилизация
    text_color = models.CharField('Цвет текста', max_length=7, default='#FFFFFF')
    overlay_color = models.CharField('Цвет оверлея', max_length=25, default='rgba(0,0,0,0.4)')
    text_position = models.CharField('Позиция текста', max_length=20,
                                     choices=[('left', 'Слева'), ('center', 'Центр'), ('right', 'Справа')],
                                     default='center')

    # Управление
    is_active = models.BooleanField('Активный', default=True)
    priority = models.IntegerField('Приоритет', default=1,
                                   help_text='Чем выше число, тем выше приоритет')
    show_on_mobile = models.BooleanField('Показывать на мобильных', default=True)
    show_on_desktop = models.BooleanField('Показывать на ПК', default=True)

    # Даты
    start_date = models.DateTimeField('Дата начала показа', blank=True, null=True)
    end_date = models.DateTimeField('Дата окончания показа', blank=True, null=True)

    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Баннер'
        verbose_name_plural = 'Баннеры'
        ordering = ['-priority', '-created_at']

    def __str__(self):
        return self.title

    @property
    def is_currently_active(self):
        """Проверяет, активен ли баннер в текущее время"""
        if not self.is_active:
            return False

        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False

        return True

