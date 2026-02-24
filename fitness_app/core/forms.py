from allauth.account.forms import SignupForm, LoginForm, ResetPasswordForm, ResetPasswordKeyForm
from django import forms
from .models import VideoComment


class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Логин',
            'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Email (обязательно)',
            'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Пароль',
            'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Повторите пароль',
            'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'
        })

        # Делаем email обязательным
        self.fields['email'].required = True

    def _translate_error(self, error):
        translations = {
            "This password is too short. It must contain at least %(min_length)d characters.":
                "Пароль слишком короткий. Должен содержать минимум 6 символов.",
            "The password is too common.":
                "Введённый пароль слишком широко распространён.",
            "The password is entirely numeric.":
                "Введённый пароль состоит только из цифр.",
            "The two password fields didn't match.":
                "Пароли не совпадают.",
            "A user with that username already exists.":
                "Пользователь с таким логином уже существует.",
            "A user is already registered with this e-mail address.":
                "Пользователь с таким email уже зарегистрирован.",
        }

        for eng, rus in translations.items():
            if eng in error:
                return rus
        return error

    def add_error(self, field, error):
        if isinstance(error, str):
            error = self._translate_error(error)
        super().add_error(field, error)


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['login'].widget.attrs.update({
            'placeholder': 'Email или логин',
            'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': 'Пароль',
            'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'
        })


class CustomResetPasswordForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'placeholder': 'Введите ваш email',
            'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'
        })


class CustomResetPasswordKeyForm(ResetPasswordKeyForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'placeholder': 'Новый пароль',
            'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': 'Повторите новый пароль',
            'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'
        })


class VideoCommentForm(forms.ModelForm):
    """Форма для добавления комментария"""
    parent_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = VideoComment
        fields = ['text', 'parent_id']  # ДОБАВЛЯЕМ parent_id
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent',
                'rows': 3,
                'placeholder': 'Напишите ваш комментарий...',
                'maxlength': 1000,
            })
        }
        labels = {
            'text': ''
        }

class VideoLikeForm(forms.ModelForm):
    """Форма для лайка (скрытая)"""
    class Meta:
        model = VideoComment
        fields = ['is_like']
        widgets = {
            'is_like': forms.HiddenInput()
        }


from .models import ServiceRequest

class ServiceRequestForm(forms.ModelForm):
    """Форма заявки на услугу"""
    class Meta:
        model = ServiceRequest
        fields = ['full_name', 'email', 'phone', 'additional_info']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg',
                'placeholder': 'Иванов Иван Иванович'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg',
                'placeholder': 'ivan@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg',
                'placeholder': '+7 (999) 123-45-67'
            }),
            'additional_info': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg',
                'rows': 4,
                'placeholder': 'Расскажите о ваших целях, уровне подготовки, пожеланиях...'
            }),
        }
