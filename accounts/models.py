from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ("client", "Клиент"),
        ("master", "Мастер"),
        ("admin", "Администратор салона"),
    ]
    
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default="client", 
        verbose_name="Роль"
    )

    phone = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Телефон"
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
