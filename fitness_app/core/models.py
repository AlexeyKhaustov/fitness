from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse

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
