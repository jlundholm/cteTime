from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from core.models import Student, StudentClass, ClassStudent, EmailSettings


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
        })
    )


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class StudentCodeForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '6-digit code',
            'maxlength': '6',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric',
        }),
        help_text='Enter a 6-digit number'
    )


class ClassForm(forms.ModelForm):
    school_year = forms.CharField(
        max_length=9,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )
    
    class Meta:
        model = StudentClass
        fields = ['name', 'school_year', 'students']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'students': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        if teacher:
            school_year = self.initial.get('school_year') or self.fields['school_year'].initial
            if school_year:
                existing_student_ids = ClassStudent.objects.filter(
                    class_model__teacher=teacher,
                    class_model__school_year=school_year
                ).values_list('student_id', flat=True)
                self.fields['students'].queryset = Student.objects.filter(
                    id__in=existing_student_ids
                ).order_by('last_name', 'first_name')


class EmailSettingsForm(forms.ModelForm):
    class Meta:
        model = EmailSettings
        fields = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'smtp_from_email', 'use_tls']
        widgets = {
            'smtp_host': forms.TextInput(attrs={'class': 'form-control'}),
            'smtp_port': forms.NumberInput(attrs={'class': 'form-control'}),
            'smtp_username': forms.TextInput(attrs={'class': 'form-control'}),
            'smtp_password': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
            'smtp_from_email': forms.TextInput(attrs={'class': 'form-control'}),
            'use_tls': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TeacherForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2
    
    def save(self, commit=True):
        user = super().save(commit=False)
        return user


class PunchFilterForm(forms.Form):
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        if teacher:
            from django.utils import timezone
            now = timezone.now()
            year = now.year
            school_year = f"{year}-{year + 1}" if now.month >= 8 else f"{year - 1}-{year}"
            
            my_classes = StudentClass.objects.filter(teacher=teacher, school_year=school_year)
            my_class_ids = my_classes.values_list('id', flat=True)
            my_student_ids = ClassStudent.objects.filter(
                class_model_id__in=my_class_ids
            ).values_list('student_id', flat=True)
            
            self.fields['student'].queryset = Student.objects.filter(
                id__in=my_student_ids
            ).order_by('last_name', 'first_name')
            self.fields['class'].queryset = my_classes
    
    student = forms.ModelChoiceField(
        queryset=Student.objects.none(),
        required=False,
        empty_label='All Students',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class_filter = forms.ModelChoiceField(
        queryset=StudentClass.objects.none(),
        required=False,
        empty_label='All Classes',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    punch_type = forms.ChoiceField(
        choices=[('', 'All Types'), ('IN', 'Clock In'), ('OUT', 'Clock Out')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        fields = ['student', 'class', 'start_date', 'end_date', 'punch_type']


class ReportForm(forms.Form):
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        super().__init__(*args, **kwargs)
        
        if teacher:
            from django.utils import timezone
            now = timezone.now()
            year = now.year
            school_year = f"{year}-{year + 1}" if now.month >= 8 else f"{year - 1}-{year}"
            
            self.fields['class_model'].queryset = StudentClass.objects.filter(
                teacher=teacher,
                school_year=school_year
            ).order_by('name')
    
    class_model = forms.ModelChoiceField(
        queryset=StudentClass.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Class'
    )
    week_start = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Week Starting'
    )
