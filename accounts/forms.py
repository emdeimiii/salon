from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "input",
            "placeholder": "example@mail.ru",
        }),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label="Телефон",
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "+7 (999) 123-45-67",
        }),
    )

    class Meta:
        model = CustomUser
        fields = ("username", "email", "phone", "password1", "password2")
        widgets = {
            'username': forms.TextInput(attrs={
                "class": "input",
                "placeholder": "Ваш логин",
            }),
            'password1': forms.PasswordInput(attrs={
                "class": "input",
                "placeholder": "Придумайте пароль",
            }),
            'password2': forms.PasswordInput(attrs={
                "class": "input",
                "placeholder": "Повторите пароль",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'email' in self.fields:
            self.fields['email'].widget.attrs.setdefault('placeholder', 'example@mail.ru')
        if 'phone' in self.fields:
            self.fields['phone'].widget.attrs.setdefault('placeholder', '+7 (999) 123-45-67')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким Email уже существует.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("Пользователь с таким логином уже существует.")
        return username