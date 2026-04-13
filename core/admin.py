from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.http import JsonResponse
from django.core.mail import send_mail
from .models import Student, StudentClass, ClassStudent, Punch, EmailSettings, SchoolYear


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'code', 'created_at']
    search_fields = ['first_name', 'last_name', 'code']
    ordering = ['last_name', 'first_name']


@admin.register(StudentClass)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['name', 'teacher', 'school_year']
    list_filter = ['school_year', 'teacher']
    search_fields = ['name']


@admin.register(Punch)
class PunchAdmin(admin.ModelAdmin):
    list_display = ['student', 'punch_type', 'timestamp', 'school_year']
    list_filter = ['punch_type', 'school_year', 'timestamp']
    search_fields = ['student__first_name', 'student__last_name', 'student__code']


class EmailSettingsAdmin(admin.ModelAdmin):
    change_form_template = 'admin/emailsettings_change_form.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('test-email/', self.admin_site.admin_view(self.test_email), name='test_email'),
        ]
        return custom_urls
    
    def test_email(self, request):
        if request.method == 'POST':
            test_email = request.POST.get('email')
            if not test_email:
                return JsonResponse({'error': 'Email address required'}, status=400)
            
            email_settings = EmailSettings.get_settings()
            
            if not email_settings.smtp_username or not email_settings.smtp_from_email:
                return JsonResponse({'error': 'SMTP settings not configured'}, status=400)
            
            try:
                send_mail(
                    subject='CTE Timeclock Test Email',
                    message='This is a test email from CTE Timeclock.\n\nIf you received this, your email settings are working correctly.',
                    from_email=email_settings.smtp_from_email,
                    recipient_list=[test_email],
                    fail_silently=False,
                )
                return JsonResponse({'success': True, 'message': f'Test email sent to {test_email}'})
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        
        return JsonResponse({'error': 'Invalid request'}, status=400)
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['test_email_url'] = '/admin/test-email/'
        return super().changeform_view(request, object_id, form_url, extra_context)


admin.site.register(EmailSettings, EmailSettingsAdmin)
admin.site.register(SchoolYear)
admin.site.register(ClassStudent)
