from django.contrib import admin
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


admin.site.register(EmailSettings)
admin.site.register(SchoolYear)
admin.site.register(ClassStudent)
