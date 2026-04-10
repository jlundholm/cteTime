from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta, datetime
from core.models import Student, Punch, StudentClass, ClassStudent, EmailSettings, SchoolYear
from .forms import (
    LoginForm, StudentForm, StudentCodeForm, ClassForm,
    EmailSettingsForm, TeacherForm, PunchFilterForm, ReportForm
)
import csv


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                error = 'Invalid username or password.'
        else:
            error = 'Username and password are required.'
        
        return render(request, 'teachers/login.html', {
            'error': error,
            'username': username,
        })
    
    return render(request, 'teachers/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    school_year = get_current_school_year()
    
    my_classes = StudentClass.objects.filter(teacher=request.user, school_year=school_year)
    my_class_ids = my_classes.values_list('id', flat=True)
    my_student_ids = ClassStudent.objects.filter(
        class_model_id__in=my_class_ids
    ).values_list('student_id', flat=True)
    
    clocked_in_students = Student.objects.filter(
        id__in=my_student_ids,
        punches__punch_type='IN',
        punches__school_year=school_year
    ).annotate(
        last_punch_time=Punch.objects.filter(
            student__id__in=my_student_ids,
            punch_type='IN',
            school_year=school_year
        ).values('student_id').order_by('-timestamp').values('timestamp')[:1]
    )
    
    punch_ins = Punch.objects.filter(
        student_id__in=my_student_ids,
        punch_type='IN',
        school_year=school_year
    ).select_related('student').order_by('-timestamp')
    
    clocked_in_ids = set()
    clocked_in_list = []
    
    for punch in punch_ins:
        if punch.student_id not in clocked_in_ids:
            clocked_in_ids.add(punch.student_id)
            punch.student.clocked_in_at = punch.timestamp
            punch.student.duration = calculate_duration(punch.timestamp)
            
            student_classes = StudentClass.objects.filter(
                teacher=request.user,
                school_year=school_year,
                classstudent__student=punch.student
            ).values_list('name', flat=True)
            punch.student.classes = ', '.join(student_classes)
            
            clocked_in_list.append(punch.student)
    
    for student in clocked_in_list:
        student_classes = StudentClass.objects.filter(
            teacher=request.user,
            school_year=school_year,
            classstudent__student=student
        ).values_list('name', flat=True)
        student.classes = ', '.join(student_classes)
    
    context = {
        'clocked_in_students': clocked_in_list,
        'total_clocked_in': len(clocked_in_list),
        'classes': my_classes,
        'school_year': school_year,
    }
    
    return render(request, 'teachers/dashboard.html', context)


@login_required
def student_list(request):
    school_year = get_current_school_year()
    
    search = request.GET.get('search', '')
    class_filter = request.GET.get('class_filter', '')
    
    my_classes = StudentClass.objects.filter(teacher=request.user, school_year=school_year)
    my_class_ids = my_classes.values_list('id', flat=True)
    
    students = Student.objects.annotate(
        num_classes=Count('classstudent')
    ).order_by('last_name', 'first_name')
    
    if search:
        students = students.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(code__icontains=search)
        )
    
    if class_filter:
        students = students.filter(
            classstudent__class_model_id=class_filter
        )
    
    paginator = Paginator(students, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'class_filter': class_filter,
        'classes': my_classes,
        'school_year': school_year,
    }
    
    return render(request, 'teachers/student_list.html', context)


@login_required
def student_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        code_form = StudentCodeForm(request.POST)
        if form.is_valid() and code_form.is_valid():
            code = code_form.cleaned_data['code']
            
            if Student.objects.filter(code=code).exists():
                messages.error(request, 'This code is already in use.')
                return render(request, 'teachers/student_form.html', {
                    'form': form,
                    'code_form': code_form,
                    'action': 'Add',
                })
            
            student = form.save(commit=False)
            student.code = code
            student.save()
            messages.success(request, f'Student {student.full_name} added successfully.')
            return redirect('student_list')
    else:
        form = StudentForm()
        code_form = StudentCodeForm()
    
    return render(request, 'teachers/student_form.html', {
        'form': form,
        'code_form': code_form,
        'action': 'Add',
    })


@login_required
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        code_form = StudentCodeForm(request.POST)
        if form.is_valid() and code_form.is_valid():
            new_code = code_form.cleaned_data['code']
            
            if new_code != student.code and Student.objects.filter(code=new_code).exists():
                messages.error(request, 'This code is already in use.')
                return render(request, 'teachers/student_form.html', {
                    'form': form,
                    'code_form': code_form,
                    'student': student,
                    'action': 'Edit',
                })
            
            student = form.save(commit=False)
            student.code = new_code
            student.save()
            messages.success(request, f'Student {student.full_name} updated.')
            return redirect('student_list')
    else:
        form = StudentForm(instance=student)
        code_form = StudentCodeForm(initial={'code': student.code})
    
    return render(request, 'teachers/student_form.html', {
        'form': form,
        'code_form': code_form,
        'student': student,
        'action': 'Edit',
    })


@login_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        student_name = student.full_name
        student.delete()
        messages.success(request, f'Student {student_name} deleted.')
        return redirect('student_list')
    
    return render(request, 'teachers/student_delete.html', {'student': student})


@login_required
def punch_list(request):
    school_year = get_current_school_year()
    
    form = PunchFilterForm(request.GET or None, teacher=request.user)
    punches = Punch.objects.all().select_related('student').order_by('-timestamp')
    
    if form.is_valid():
        student = form.cleaned_data.get('student')
        class_filter = form.cleaned_data.get('class_filter')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        punch_type = form.cleaned_data.get('punch_type')
        
        if student:
            punches = punches.filter(student=student)
        
        if class_filter:
            punches = punches.filter(student__in=ClassStudent.objects.filter(
                class_model=class_filter
            ).values('student'))
        
        if start_date:
            punches = punches.filter(timestamp__date__gte=start_date)
        
        if end_date:
            punches = punches.filter(timestamp__date__lte=end_date)
        
        if punch_type:
            punches = punches.filter(punch_type=punch_type)
    
    punches = punches.filter(school_year=school_year)
    
    paginator = Paginator(punches, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'form': form,
        'school_year': school_year,
    }
    
    return render(request, 'teachers/punch_list.html', context)


@login_required
def punch_export(request):
    school_year = get_current_school_year()
    
    form = PunchFilterForm(request.GET or None, teacher=request.user)
    punches = Punch.objects.all().select_related('student').order_by('-timestamp')
    
    if form.is_valid():
        student = form.cleaned_data.get('student')
        class_filter = form.cleaned_data.get('class_filter')
        start_date = form.cleaned_data.get('start_date')
        end_date = form.cleaned_data.get('end_date')
        
        if student:
            punches = punches.filter(student=student)
        
        if class_filter:
            punches = punches.filter(student__in=ClassStudent.objects.filter(
                class_model=class_filter
            ).values('student'))
        
        if start_date:
            punches = punches.filter(timestamp__date__gte=start_date)
        
        if end_date:
            punches = punches.filter(timestamp__date__lte=end_date)
    
    punches = punches.filter(school_year=school_year)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="punches.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Code', 'Punch Type', 'Timestamp', 'School Year'])
    
    for punch in punches:
        writer.writerow([
            punch.student.full_name,
            punch.student.code,
            punch.get_punch_type_display(),
            punch.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            punch.school_year,
        ])
    
    return response


@login_required
def report_view(request):
    school_year = get_current_school_year()
    
    my_classes = StudentClass.objects.filter(teacher=request.user, school_year=school_year)
    
    if request.method == 'POST':
        form = ReportForm(request.POST, teacher=request.user)
        if form.is_valid():
            selected_class = form.cleaned_data['class_model']
            week_start = form.cleaned_data['week_start']
            
            students = Student.objects.filter(
                classstudent__class_model=selected_class
            ).distinct()
            
            student_data = []
            for student in students:
                punches = Punch.objects.filter(
                    student=student,
                    school_year=school_year,
                    timestamp__date__gte=week_start,
                    timestamp__date__lt=week_start + timedelta(days=7)
                ).order_by('timestamp')
                
                total_minutes = calculate_week_minutes(punches)
                student_data.append({
                    'student': student,
                    'punches': punches,
                    'total_hours': total_minutes // 60,
                    'total_minutes': total_minutes % 60,
                })
            
            context = {
                'form': form,
                'class_model': selected_class,
                'week_start': week_start,
                'student_data': student_data,
                'school_year': school_year,
            }
            return render(request, 'teachers/report_detail.html', context)
    else:
        form = ReportForm(teacher=request.user, initial={
            'week_start': get_week_start(),
        })
    
    context = {
        'form': form,
        'classes': my_classes,
        'school_year': school_year,
    }
    
    return render(request, 'teachers/report.html', context)


@login_required
def report_send(request):
    school_year = get_current_school_year()
    
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        week_start_str = request.POST.get('week_start')
        
        if not class_id or not week_start_str:
            messages.error(request, 'Missing required data.')
            return redirect('report')
        
        try:
            selected_class = StudentClass.objects.get(id=class_id, teacher=request.user)
            week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        except (StudentClass.DoesNotExist, ValueError):
            messages.error(request, 'Invalid class or date.')
            return redirect('report')
        
        students = Student.objects.filter(
            classstudent__class_model=selected_class
        ).distinct()
        
        email_settings = EmailSettings.get_settings()
        
        if not email_settings.smtp_username or not email_settings.smtp_from_email:
            messages.error(request, 'Email settings not configured. Please configure SMTP settings first.')
            return redirect('settings')
        
        html_content = generate_report_html(selected_class, week_start, students, school_year)
        week_end = week_start + timedelta(days=6)
        subject = f"Weekly Time Report - {selected_class.name} ({week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')})"
        
        try:
            send_mail(
                subject=subject,
                message='',
                from_email=email_settings.smtp_from_email,
                recipient_list=[request.user.email],
                html_message=html_content,
                fail_silently=False,
            )
            messages.success(request, f'Report sent to {request.user.email}')
        except Exception as e:
            messages.error(request, f'Failed to send email: {str(e)}')
    
    return redirect('report')


@login_required
def class_list(request):
    school_year = get_current_school_year()
    
    classes = StudentClass.objects.filter(teacher=request.user, school_year=school_year)
    
    for cls in classes:
        cls.student_count = ClassStudent.objects.filter(class_model=cls).count()
    
    context = {
        'classes': classes,
        'school_year': school_year,
    }
    
    return render(request, 'teachers/class_list.html', context)


@login_required
def class_add(request):
    if request.method == 'POST':
        form = ClassForm(request.POST, teacher=request.user)
        if form.is_valid():
            class_model = form.save(commit=False)
            class_model.teacher = request.user
            class_model.school_year = get_current_school_year()
            class_model.save()
            form.save_m2m()
            messages.success(request, f'Class "{class_model.name}" created.')
            return redirect('class_list')
    else:
        form = ClassForm(teacher=request.user, initial={
            'school_year': get_current_school_year(),
        })
    
    return render(request, 'teachers/class_form.html', {
        'form': form,
        'action': 'Add',
    })


@login_required
def class_edit(request, pk):
    class_model = get_object_or_404(Class, pk=pk, teacher=request.user)
    
    if request.method == 'POST':
        form = ClassForm(request.POST, instance=class_model, teacher=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Class "{class_model.name}" updated.')
            return redirect('class_list')
    else:
        form = ClassForm(instance=class_model, teacher=request.user)
    
    return render(request, 'teachers/class_form.html', {
        'form': form,
        'class_model': class_model,
        'action': 'Edit',
    })


@login_required
def class_delete(request, pk):
    class_model = get_object_or_404(Class, pk=pk, teacher=request.user)
    
    if request.method == 'POST':
        class_name = class_model.name
        class_model.delete()
        messages.success(request, f'Class "{class_name}" deleted.')
        return redirect('class_list')
    
    return render(request, 'teachers/class_delete.html', {'class_model': class_model})


@login_required
def settings_view(request):
    email_settings = EmailSettings.get_settings()
    
    if request.method == 'POST':
        form = EmailSettingsForm(request.POST, instance=email_settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'Email settings saved.')
            return redirect('settings')
    else:
        form = EmailSettingsForm(instance=email_settings)
    
    return render(request, 'teachers/settings.html', {'form': form})


@login_required
def clear_year_view(request):
    school_year = get_current_school_year()
    
    my_classes = StudentClass.objects.filter(teacher=request.user, school_year=school_year)
    class_ids = my_classes.values_list('id', flat=True)
    
    class_student_count = ClassStudent.objects.filter(class_model_id__in=class_ids).count()
    student_ids = ClassStudent.objects.filter(class_model_id__in=class_ids).values_list('student_id', flat=True)
    punch_count = Punch.objects.filter(student_id__in=student_ids, school_year=school_year).count()
    student_count = Student.objects.filter(id__in=student_ids).count()
    
    if request.method == 'POST':
        ClassStudent.objects.filter(class_model_id__in=class_ids).delete()
        Punch.objects.filter(student_id__in=student_ids, school_year=school_year).delete()
        Student.objects.filter(id__in=student_ids).delete()
        my_classes.delete()
        
        messages.success(request, f'All data for school year {school_year} has been cleared.')
        return redirect('dashboard')
    
    context = {
        'school_year': school_year,
        'class_count': my_classes.count(),
        'student_count': student_count,
        'punch_count': punch_count,
        'class_student_count': class_student_count,
    }
    
    return render(request, 'teachers/clear_year.html', context)


@login_required
def teacher_list(request):
    teachers = User.objects.filter(is_staff=False).order_by('username')
    
    return render(request, 'teachers/teacher_list.html', {'teachers': teachers})


@login_required
def teacher_add(request):
    if request.method == 'POST':
        form = TeacherForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password1']
            user = form.save()
            user.set_password(password)
            user.save()
            messages.success(request, f'Teacher "{user.username}" created.')
            return redirect('teacher_list')
    else:
        form = TeacherForm()
    
    return render(request, 'teachers/teacher_form.html', {
        'form': form,
        'action': 'Add',
    })


@login_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(User, pk=pk)
    
    if request.user == teacher:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('teacher_list')
    
    if request.method == 'POST':
        teacher_name = teacher.username
        teacher.delete()
        messages.success(request, f'Teacher "{teacher_name}" deleted.')
        return redirect('teacher_list')
    
    return render(request, 'teachers/teacher_delete.html', {'teacher': teacher})


def get_current_school_year():
    now = timezone.now()
    year = now.year
    if now.month >= 8:
        return f"{year}-{year + 1}"
    return f"{year - 1}-{year}"


def get_week_start():
    today = timezone.now().date()
    return today - timedelta(days=today.weekday())


def calculate_duration(start_time):
    delta = timezone.now() - start_time
    hours = int(delta.total_seconds() // 3600)
    minutes = int((delta.total_seconds() % 3600) // 60)
    return f"{hours}h {minutes}m"


def calculate_week_minutes(punches):
    total_minutes = 0
    current_in = None
    
    for punch in punches:
        if punch.punch_type == 'IN':
            current_in = punch.timestamp
        elif punch.punch_type == 'OUT' and current_in:
            delta = punch.timestamp - current_in
            total_minutes += int(delta.total_seconds() / 60)
            current_in = None
    
    return total_minutes


def generate_report_html(class_model, week_start, students, school_year):
    week_end = week_start + timedelta(days=6)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #667eea; color: white; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .total-row {{ font-weight: bold; background-color: #e8f5e9; }}
        </style>
    </head>
    <body>
        <h1>Weekly Time Report</h1>
        <p><strong>Class:</strong> {class_model.name}</p>
        <p><strong>Week:</strong> {week_start.strftime('%B %d, %Y')} - {week_end.strftime('%B %d, %Y')}</p>
        <p><strong>School Year:</strong> {school_year}</p>
        
        <table>
            <thead>
                <tr>
                    <th>Student</th>
                    <th>Code</th>
                    <th>Total Hours</th>
                </tr>
            </thead>
            <tbody>
    """
    
    grand_total = 0
    for student in students:
        punches = Punch.objects.filter(
            student=student,
            school_year=school_year,
            timestamp__date__gte=week_start,
            timestamp__date__lt=week_start + timedelta(days=7)
        ).order_by('timestamp')
        
        total_minutes = calculate_week_minutes(punches)
        grand_total += total_minutes
        
        hours = total_minutes // 60
        mins = total_minutes % 60
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        
        html += f"""
                <tr>
                    <td>{student.full_name}</td>
                    <td>{student.code}</td>
                    <td>{time_str}</td>
                </tr>
        """
    
    total_hours = grand_total // 60
    total_mins = grand_total % 60
    
    html += f"""
            </tbody>
            <tfoot>
                <tr class="total-row">
                    <td colspan="2">Grand Total</td>
                    <td>{total_hours}h {total_mins}m</td>
                </tr>
            </tfoot>
        </table>
    </body>
    </html>
    """
    
    return html
