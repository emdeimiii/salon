import re
from django import forms
from django.utils import timezone
from datetime import timedelta
from .models import Appointment, Master


class AppointmentForm(forms.ModelForm):
    appointment_time = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "input",
            },
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    phone = forms.CharField(
        label="Номер телефона",
        max_length=18,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "+7 (999) 123-45-67",
        }),
    )

    class Meta:
        model = Appointment
        fields = ["service", "master", "appointment_time"]
        widgets = {
            'service': forms.Select(attrs={'class': 'select'}),
            'master': forms.Select(attrs={'class': 'select'}),
        }

    def __init__(self, *args, **kwargs):
        self.client = kwargs.pop("client", None)
        super().__init__(*args, **kwargs)
        

        service_id = self.data.get('service') or self.initial.get('service')
        
        if service_id:

            if hasattr(service_id, 'id'):
                service_id = service_id.id
            

            self.fields['master'].queryset = Master.objects.filter(services__id=service_id)

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if not phone:
            return phone
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 11:
            raise forms.ValidationError("Введите корректный номер телефона (минимум 11 цифр)")
        return digits

    def clean(self):
        cleaned_data = super().clean()
        master = cleaned_data.get("master")
        appointment_time = cleaned_data.get("appointment_time")
        service = cleaned_data.get("service")

        if not master or not appointment_time or not service:
            return cleaned_data


        if appointment_time < (timezone.now() - timedelta(minutes=1)):
            self.add_error("appointment_time", "Нельзя записаться в прошлое")

        if appointment_time > (timezone.now() + timedelta(days=365)):
            self.add_error("appointment_time", "Нельзя записаться более чем на год вперед")


        if not master.services.filter(pk=service.pk).exists():
            self.add_error("service", "Этот мастер не оказывает выбранную услугу")


        

        if not master.is_working_day(appointment_time.date()):
            self.add_error(
                "appointment_time",
                f"Мастер {master.name} не работает в этот день. "
                f"Рабочие дни: {master.get_work_days_display()}"
            )


        if not master.is_working_time(appointment_time.time()):
            if master.lunch_start and master.lunch_end:
                if master.lunch_start <= appointment_time.time() < master.lunch_end:
                    self.add_error(
                        "appointment_time",
                        f"У мастера обед с {master.lunch_start.strftime('%H:%M')} "
                        f"до {master.lunch_end.strftime('%H:%M')}"
                    )
                else:
                    self.add_error(
                        "appointment_time",
                        f"Мастер работает с {master.work_start.strftime('%H:%M')} "
                        f"до {master.work_end.strftime('%H:%M')}"
                    )
            else:
                self.add_error(
                    "appointment_time",
                    f"Мастер работает с {master.work_start.strftime('%H:%M')} "
                    f"до {master.work_end.strftime('%H:%M')}"
                )


        end_time = appointment_time + timedelta(minutes=service.duration_minutes)


        if end_time.time() > master.work_end:
            self.add_error(
                "appointment_time",
                f"Услуга не успеет завершиться до конца рабочего дня. "
                f"Мастер заканчивает в {master.work_end.strftime('%H:%M')}"
            )

        qs = Appointment.objects.all()
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        overlapping_master = qs.filter(
            master=master,
            appointment_time__lt=end_time,
            end_time__gt=appointment_time,
            status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
        )
        if overlapping_master.exists():
            self.add_error("appointment_time", "Мастер уже занят в это время")


        if self.client:
            overlapping_client = qs.filter(
                client=self.client,
                appointment_time__lt=end_time,
                end_time__gt=appointment_time,
                status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED],
            )
            if overlapping_client.exists():
                self.add_error(
                    "appointment_time",
                    "У вас уже есть запись в это время"
                )

        return cleaned_data

    def save(self, commit=True):
        appointment = super().save(commit=False)

        if self.client and self.cleaned_data.get("phone"):
            self.client.phone = self.cleaned_data["phone"]
            if commit:
                self.client.save(update_fields=["phone"])

        if commit:
            appointment.save()

        return appointment