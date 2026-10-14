from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils import timezone
from datetime import timedelta
from accounts.models import CustomUser


class Category(models.Model):
    name = models.CharField("Название категории", max_length=100)
    icon = models.CharField("Иконка (эмодзи)", max_length=10, default="✨")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return f"{self.icon} {self.name}"


class Service(models.Model):
    name = models.CharField("Название", max_length=100)
    description = models.TextField("Описание", blank=True)
    price = models.DecimalField(
        "Цена",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0, "Цена не может быть отрицательной")],
    )
    duration_minutes = models.PositiveIntegerField(
        "Длительность, мин",
        validators=[MinValueValidator(1, "Минимум 1 минута")],
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="services",
        verbose_name="Категория",
    )

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Master(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='master_profile',
        verbose_name="Аккаунт мастера"
    )
    name = models.CharField("Имя", max_length=100)
    specialization = models.CharField("Специализация", max_length=100)
    photo = models.ImageField(upload_to='masters/', blank=True, null=True)
    rating = models.DecimalField(
        "Рейтинг",
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    services = models.ManyToManyField(Service, related_name="masters", verbose_name="Услуги")

    work_days = models.CharField(
        "Рабочие дни",
        max_length=20,
        default="1,2,3,4,5",
        help_text="Номера дней через запятую: 1=Пн, 2=Вт, 3=Ср, 4=Чт, 5=Пт, 6=Сб, 7=Вс"
    )
    work_start = models.TimeField(
        "Начало рабочего дня",
        default="09:00",
        help_text="Например: 09:00"
    )
    work_end = models.TimeField(
        "Конец рабочего дня",
        default="20:00",
        help_text="Например: 20:00"
    )
    lunch_start = models.TimeField(
        "Начало обеда",
        default="13:00",
        blank=True,
        null=True,
        help_text="Оставьте пустым, если обеда нет"
    )
    lunch_end = models.TimeField(
        "Конец обеда",
        default="14:00",
        blank=True,
        null=True,
        help_text="Оставьте пустым, если обеда нет"
    )

    class Meta:
        verbose_name = "Мастер"
        verbose_name_plural = "Мастера"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.specialization})"

    def get_work_days_list(self):
        """Возвращает список рабочих дней как числа [1, 2, 3, 4, 5]"""
        if not self.work_days:
            return []
        return [int(day.strip()) for day in self.work_days.split(',') if day.strip().isdigit()]

    def get_work_days_display(self):
        """Возвращает читаемое название рабочих дней: 'Пн, Вт, Ср, Чт, Пт'"""
        days_names = {
            1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт",
            5: "Пт", 6: "Сб", 7: "Вс"
        }
        work_days = self.get_work_days_list()
        return ", ".join(days_names.get(d, "") for d in sorted(work_days))

    def is_working_day(self, date):
        """Проверяет, работает ли мастер в указанный день"""
        day_number = date.weekday() + 1
        return day_number in self.get_work_days_list()

    def is_working_time(self, time_obj):
        """Проверяет, работает ли мастер в указанное время"""
        if time_obj < self.work_start or time_obj >= self.work_end:
            return False
        if self.lunch_start and self.lunch_end:
            if self.lunch_start <= time_obj < self.lunch_end:
                return False
        return True

    def is_time_available(self, date, time_obj):
        """Комплексная проверка: день + время"""
        return self.is_working_day(date) and self.is_working_time(time_obj)


class Appointment(models.Model):
    def get_status_badge_class(self):
        """Возвращает CSS-класс для бейджа статуса (обновлено под кастомные классы)"""
        return {
            self.Status.PENDING: "badge-warning",
            self.Status.CONFIRMED: "badge-success",
            self.Status.COMPLETED: "badge-secondary",
            self.Status.CANCELLED: "badge-danger",
        }.get(self.status, "badge-secondary")

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает подтверждения"
        CONFIRMED = "confirmed", "Подтверждена"
        COMPLETED = "completed", "Завершена"
        CANCELLED = "cancelled", "Отменена"

    client = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="appointments",
        verbose_name="Клиент",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Услуга",
    )
    master = models.ForeignKey(
        Master,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Мастер",
    )
    appointment_time = models.DateTimeField("Дата и время записи")
    end_time = models.DateTimeField("Время окончания", editable=False)
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Запись"
        verbose_name_plural = "Записи"
        ordering = ["-appointment_time"]
        indexes = [
            models.Index(fields=["master", "appointment_time"]),
            models.Index(fields=["client", "status"]),
            models.Index(fields=["status", "appointment_time"]),
        ]

    def save(self, *args, **kwargs):
        if self.appointment_time and self.service_id:
            self.end_time = self.appointment_time + timedelta(
                minutes=self.service.duration_minutes
            )
        super().save(*args, **kwargs)

    def clean(self):
        if self.appointment_time:
            now = timezone.now()
            if self.appointment_time < now:
                raise ValidationError("Нельзя записаться в прошлое")
            max_future = now + timedelta(days=365)
            if self.appointment_time > max_future:
                raise ValidationError("Нельзя записаться более чем на год вперед")

    def __str__(self):
        return (
            f"{self.client.username} — {self.service.name} "
            f"у {self.master.name} "
            f"({self.appointment_time.strftime('%d.%m.%Y %H:%M')})"
        )