from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SchoolYearManager(models.Manager):
    def get_current(self):
        now = timezone.now()
        year = now.year
        if now.month >= 8:
            return f"{year}-{year + 1}"
        return f"{year - 1}-{year}"


class SchoolYear(models.Model):
    year = models.CharField(max_length=9, unique=True)
    
    objects = SchoolYearManager()
    
    class Meta:
        ordering = ['-year']
    
    def __str__(self):
        return self.year


class EmailSettings(models.Model):
    smtp_host = models.CharField(max_length=100, default='smtp.gmail.com')
    smtp_port = models.IntegerField(default=587)
    smtp_username = models.CharField(max_length=254, blank=True)
    smtp_password = models.CharField(max_length=256, blank=True)
    smtp_from_email = models.CharField(max_length=254, blank=True)
    use_tls = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Email Settings'
        verbose_name_plural = 'Email Settings'
    
    def __str__(self):
        return 'Email Settings'
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        settings, _ = cls.objects.get_or_create(pk=1)
        return settings


class Student(models.Model):
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    code = models.CharField(max_length=6, unique=True, verbose_name='6-Digit Code')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Class(models.Model):
    name = models.CharField(max_length=100)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classes')
    school_year = models.CharField(max_length=9)
    students = models.ManyToManyField(Student, through='ClassStudent', related_name='classes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'teacher', 'school_year']
    
    def __str__(self):
        return self.name


class ClassStudent(models.Model):
    class_model = models.ForeignKey(Class, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['class_model', 'student']
    
    def __str__(self):
        return f"{self.student} in {self.class_model}"


class Punch(models.Model):
    PUNCH_TYPES = [
        ('IN', 'Clock In'),
        ('OUT', 'Clock Out'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='punches')
    punch_type = models.CharField(max_length=3, choices=PUNCH_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    school_year = models.CharField(max_length=9)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.student} - {self.get_punch_type_display()} at {self.timestamp}"
    
    def duration_since(self):
        if self.punch_type == 'OUT':
            punch_in = Punch.objects.filter(
                student=self.student,
                punch_type='IN',
                timestamp__lt=self.timestamp,
                school_year=self.school_year
            ).order_by('-timestamp').first()
            if punch_in:
                delta = self.timestamp - punch_in.timestamp
                hours = int(delta.total_seconds() // 3600)
                minutes = int((delta.total_seconds() % 3600) // 60)
                return f"{hours}h {minutes}m"
        return None
