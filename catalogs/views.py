from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from django.db.models import Count, Sum, Q
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta
from .forms import AppointmentForm
from .models import Appointment, Service, Master, Category


def home(request):
    """Главная страница"""
    categories = Category.objects.all()
    featured_services = Service.objects.all()[:3]
    
    return render(request, "catalogs/home.html", {
        "categories": categories,
        "featured_services": featured_services,
    })


def services_list(request):
    """Каталог услуг с фильтрацией по категориям"""
    category_id = request.GET.get("category")
    
    services = Service.objects.all()
    active_category = None
    
    if category_id and category_id.isdigit():
        active_category = int(category_id)
        services = services.filter(category_id=active_category)

    categories = Category.objects.all()

    return render(request, "catalogs/services_list.html", {
        "services": services,
        "categories": categories,
        "active_category": active_category,
    })


def masters_list(request):
    """Список мастеров с фильтрацией по специализации"""
    specialization = request.GET.get("specialization")
    
    masters = Master.objects.all()
    active_specialization = None
    
    if specialization:
        active_specialization = specialization
        masters = masters.filter(specialization__icontains=specialization)
    

    specializations = Master.objects.values_list('specialization', flat=True).distinct()
    
    return render(request, "catalogs/masters_list.html", {
        "masters": masters,
        "specializations": specializations,
        "active_specialization": active_specialization,
    })


@login_required
def create_appointment(request):
    """Форма создания записи с поддержкой предзаполнения из URL"""
    service_id = request.GET.get('service')
    master_id = request.GET.get('master')
    
    initial_data = {}
    if service_id and service_id.isdigit():
        initial_data['service'] = int(service_id)
    if master_id and master_id.isdigit():
        initial_data['master'] = int(master_id)
    
    if request.method == "POST":
        form = AppointmentForm(request.POST, client=request.user)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.client = request.user
            appointment.save()
            messages.success(request, "Запись успешно создана!")
            return redirect("catalogs:appointment_success")
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме")
    else:
        form = AppointmentForm(client=request.user, initial=initial_data)
    
    return render(request, "catalogs/appointment_form.html", {"form": form})


@require_GET
def masters_by_service(request):
    """AJAX endpoint: возвращает мастеров, оказывающих выбранную услугу"""
    service_id = request.GET.get('service')
    
    if not service_id or not service_id.isdigit():
        return JsonResponse({'masters': []})
    
    try:
        service = Service.objects.get(id=int(service_id))
        masters = Master.objects.filter(services=service).values('id', 'name', 'specialization')
        return JsonResponse({'masters': list(masters)})
    except Service.DoesNotExist:
        return JsonResponse({'masters': []})


def appointment_success(request):
    return render(request, "catalogs/appointment_success.html")


@login_required
def profile(request):
    """Личный кабинет клиента"""
    upcoming_appointments = request.user.appointments.filter(
        appointment_time__gte=timezone.now(),
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
    ).order_by('appointment_time')
    
    past_appointments = request.user.appointments.filter(
        appointment_time__lt=timezone.now()
    ).order_by('-appointment_time')[:10]
    
    return render(request, "accounts/profile.html", {
        "upcoming_appointments": upcoming_appointments,
        "past_appointments": past_appointments,
    })


@login_required
@require_POST
def cancel_appointment(request, pk):
    """Отмена записи клиентом"""
    appointment = get_object_or_404(Appointment, pk=pk, client=request.user)
    
    if appointment.appointment_time < timezone.now():
        messages.error(request, "Нельзя отменить прошедшую запись")
        return redirect("catalogs:profile")
    
    if appointment.status in [Appointment.Status.PENDING, Appointment.Status.CONFIRMED]:
        appointment.status = Appointment.Status.CANCELLED
        appointment.save()
        messages.success(request, "Запись успешно отменена")
    else:
        messages.error(request, "Эту запись нельзя отменить")
    
    return redirect("catalogs:profile")




@login_required
def master_dashboard(request):
    """Личный кабинет мастера"""
    if request.user.role != 'master' or not hasattr(request.user, 'master_profile'):
        messages.error(request, "У вас нет доступа к кабинету мастера")
        return redirect('catalogs:home')
    
    master = request.user.master_profile
    
    today = timezone.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    month_ago = today - timedelta(days=30)
    
    today_appointments = Appointment.objects.filter(
        master=master,
        appointment_time__date=today,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
    ).select_related('service', 'client').order_by('appointment_time')
    
    week_appointments = Appointment.objects.filter(
        master=master,
        appointment_time__date__gte=week_start,
        appointment_time__date__lte=week_end,
        status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
    ).select_related('service', 'client').order_by('appointment_time')
    
    month_stats = Appointment.objects.filter(
        master=master,
        appointment_time__date__gte=month_ago,
        status=Appointment.Status.COMPLETED
    ).aggregate(
        count=Count('id'),
        revenue=Sum('service__price')
    )
    
    total_stats = Appointment.objects.filter(
        master=master,
        status=Appointment.Status.COMPLETED
    ).aggregate(
        total_count=Count('id'),
        total_revenue=Sum('service__price')
    )
    
    context = {
        'master': master,
        'today_appointments': today_appointments,
        'week_appointments': week_appointments,
        'month_stats': month_stats,
        'total_stats': total_stats,
        'today': today,
        'week_start': week_start,
        'week_end': week_end,
    }
    
    return render(request, 'catalogs/master_dashboard.html', context)


@login_required
@require_POST
def master_update_status(request, pk):
    """Мастер меняет статус своей записи"""
    if request.user.role != 'master' or not hasattr(request.user, 'master_profile'):
        messages.error(request, "У вас нет доступа")
        return redirect('catalogs:home')
    
    appointment = get_object_or_404(
        Appointment, 
        pk=pk, 
        master=request.user.master_profile
    )
    
    new_status = request.POST.get('status')
    valid_statuses = [
        Appointment.Status.CONFIRMED, 
        Appointment.Status.COMPLETED, 
        Appointment.Status.CANCELLED
    ]
    
    if new_status in valid_statuses:
        appointment.status = new_status
        appointment.save()
        messages.success(
            request, 
            f"Статус записи изменён: '{appointment.get_status_display()}'"
        )
    else:
        messages.error(request, "Недопустимый статус")
    
    return redirect('catalogs:master_dashboard')




@staff_member_required
def salon_admin_dashboard(request):
    """Панель администратора салона: общее расписание и аналитика"""
    today = timezone.now().date()
    month_ago = today - timedelta(days=30)
    week_ago = today - timedelta(days=7)
    

    today_all = Appointment.objects.filter(
        appointment_time__date=today
    ).select_related('master', 'client', 'service').order_by('appointment_time')
    

    total_stats = Appointment.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=Q(status=Appointment.Status.PENDING)),
        confirmed=Count('id', filter=Q(status=Appointment.Status.CONFIRMED)),
        completed=Count('id', filter=Q(status=Appointment.Status.COMPLETED)),
        cancelled=Count('id', filter=Q(status=Appointment.Status.CANCELLED)),
    )
    

    monthly_revenue = Appointment.objects.filter(
        appointment_time__date__gte=month_ago,
        status=Appointment.Status.COMPLETED
    ).aggregate(total=Sum('service__price'))['total'] or 0
    

    weekly_revenue = Appointment.objects.filter(
        appointment_time__date__gte=week_ago,
        status=Appointment.Status.COMPLETED
    ).aggregate(total=Sum('service__price'))['total'] or 0
    

    masters_load = Master.objects.annotate(
        today_count=Count('appointments', filter=Q(
            appointments__appointment_time__date=today,
            appointments__status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
        )),
        week_count=Count('appointments', filter=Q(
            appointments__appointment_time__date__gte=week_ago,
            appointments__status__in=[Appointment.Status.PENDING, Appointment.Status.CONFIRMED]
        ))
    ).order_by('-today_count')
    
    top_services = Service.objects.annotate(
        month_count=Count('appointments', filter=Q(
            appointments__appointment_time__date__gte=month_ago,
            appointments__status=Appointment.Status.COMPLETED
        ))
    ).filter(month_count__gt=0).order_by('-month_count')[:5]
    
    top_masters = Master.objects.annotate(
        month_count=Count('appointments', filter=Q(
            appointments__appointment_time__date__gte=month_ago,
            appointments__status=Appointment.Status.COMPLETED
        )),
        month_revenue=Sum('appointments__service__price', filter=Q(
            appointments__appointment_time__date__gte=month_ago,
            appointments__status=Appointment.Status.COMPLETED
        ))
    ).filter(month_count__gt=0).order_by('-month_count')[:5]
    
    context = {
        'today_all': today_all,
        'total_stats': total_stats,
        'monthly_revenue': monthly_revenue,
        'weekly_revenue': weekly_revenue,
        'masters_load': masters_load,
        'top_services': top_services,
        'top_masters': top_masters,
        'today': today,
    }
    
    return render(request, 'catalogs/salon_admin_dashboard.html', context)