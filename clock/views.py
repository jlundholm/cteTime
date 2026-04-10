from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from core.models import Student, Punch


def get_current_school_year():
    now = timezone.now()
    year = now.year
    if now.month >= 8:
        return f"{year}-{year + 1}"
    return f"{year - 1}-{year}"


def clock_view(request):
    school_year = get_current_school_year()
    
    code = request.POST.get('code', '').strip()
    student = None
    status = None
    last_punch = None
    clocked_in_time = None
    
    if code:
        if len(code) != 6 or not code.isdigit():
            error = "Please enter a valid 6-digit code"
            return render(request, 'clock/clock.html', {
                'error': error,
                'school_year': school_year,
            })
        
        try:
            student = Student.objects.get(code=code)
        except Student.DoesNotExist:
            error = "Student not found. Please check your code."
            return render(request, 'clock/clock.html', {
                'error': error,
                'school_year': school_year,
            })
        
        last_punch = Punch.objects.filter(
            student=student,
            school_year=school_year
        ).first()
        
        if last_punch and last_punch.punch_type == 'IN':
            status = 'IN'
            clocked_in_time = last_punch.timestamp
        else:
            status = 'OUT'
        
        if request.method == 'POST' and 'action' in request.POST:
            action = request.POST.get('action')
            
            if action == 'clock_in' and status == 'OUT':
                Punch.objects.create(
                    student=student,
                    punch_type='IN',
                    school_year=school_year
                )
                return redirect('clock_success', code=code)
            
            elif action == 'clock_out' and status == 'IN':
                Punch.objects.create(
                    student=student,
                    punch_type='OUT',
                    school_year=school_year
                )
                return redirect('clock_success', code=code)
    
    return render(request, 'clock/clock.html', {
        'student': student,
        'status': status,
        'last_punch': last_punch,
        'clocked_in_time': clocked_in_time,
        'school_year': school_year,
    })


def clock_success(request, code):
    school_year = get_current_school_year()
    
    try:
        student = Student.objects.get(code=code)
    except Student.DoesNotExist:
        return redirect('clock')
    
    last_punch = Punch.objects.filter(
        student=student,
        school_year=school_year
    ).first()
    
    status = 'OUT'
    action_taken = 'Clocked Out'
    
    if last_punch and last_punch.punch_type == 'IN':
        status = 'IN'
        action_taken = 'Clocked In'
    
    return render(request, 'clock/clock_success.html', {
        'student': student,
        'status': status,
        'action_taken': action_taken,
        'school_year': school_year,
    })


@require_http_methods(["GET", "POST"])
def clock_lookup(request):
    code = request.POST.get('code', '').strip()
    school_year = get_current_school_year()
    
    if not code or len(code) != 6 or not code.isdigit():
        return JsonResponse({'error': 'Invalid code'}, status=400)
    
    try:
        student = Student.objects.get(code=code)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    
    last_punch = Punch.objects.filter(
        student=student,
        school_year=school_year
    ).first()
    
    status = 'OUT'
    if last_punch and last_punch.punch_type == 'IN':
        status = 'IN'
    
    return JsonResponse({
        'id': student.id,
        'name': student.full_name,
        'status': status,
    })
