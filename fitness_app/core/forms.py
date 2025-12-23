# forms.py
from allauth.account.forms import SignupForm, LoginForm, ResetPasswordForm, ResetPasswordKeyForm
from django import forms


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