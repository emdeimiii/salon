from django.contrib import admin
from .models import Service, Master, Appointment, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "duration_minutes")
    search_fields = ("name", "description")
    list_filter = ("category", "duration_minutes")
    ordering = ("category", "name")


@admin.register(Master)
class MasterAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "specialization",
        "user",
        "get_work_days_display",
        "work_start",
        "work_end",
        "rating",
    )
    search_fields = ("name", "specialization", "user__username")
    list_filter = ("specialization", "user")
    filter_horizontal = ("services",)
    ordering = ("name",)

    fieldsets = (
        ("Основная информация", {

            "fields": ("user", "name", "specialization", "photo", "rating", "services"),
        }),
        ("График работы", {
            "fields": (
                "work_days",
                "work_start",
                "work_end",
                "lunch_start",
                "lunch_end",
            ),
            "description": "Укажите рабочие дни (1=Пн, 2=Вт, ..., 7=Вс) и часы работы мастера. Обед — опционально.",
        }),
    )


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("client", "service", "master", "appointment_time", "end_time", "status")
    list_filter = ("status", "master", "appointment_time")
    search_fields = ("client__username", "client__email", "service__name", "master__name")
    date_hierarchy = "appointment_time"
    readonly_fields = ("end_time", "created_at", "updated_at")
    ordering = ("-appointment_time",)

    @admin.action(description="✅ Подтвердить выбранные записи")
    def confirm_appointments(self, request, queryset):
        updated = queryset.update(status=Appointment.Status.CONFIRMED)
        self.message_user(request, f"Подтверждено записей: {updated}")

    @admin.action(description="❌ Отменить выбранные записи")
    def cancel_appointments(self, request, queryset):
        updated = queryset.update(status=Appointment.Status.CANCELLED)
        self.message_user(request, f"Отменено записей: {updated}")

    @admin.action(description="✔️ Завершить выбранные записи")
    def complete_appointments(self, request, queryset):
        updated = queryset.update(status=Appointment.Status.COMPLETED)
        self.message_user(request, f"Завершено записей: {updated}")

    actions = [confirm_appointments, cancel_appointments, complete_appointments]