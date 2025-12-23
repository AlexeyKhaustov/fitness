from allauth.account.forms import SignupForm, LoginForm

class CustomSignupForm(SignupForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'Логин', 'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'})
        self.fields['email'].widget.attrs.update({'placeholder': 'Email', 'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'Пароль', 'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'Повторите пароль', 'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'})

    def save(self, request):
        user = super().save(request)
        user.save()
        return user

class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['login'].widget.attrs.update({'placeholder': 'Email или логин', 'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'})
        self.fields['password'].widget.attrs.update({'placeholder': 'Пароль', 'class': 'w-full px-4 py-3 bg-gray-700 rounded-lg'})