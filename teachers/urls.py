from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    
    path('punches/', views.punch_list, name='punch_list'),
    path('punches/export/', views.punch_export, name='punch_export'),
    
    path('reports/', views.report_view, name='report'),
    path('reports/send/', views.report_send, name='report_send'),
    
    path('classes/', views.class_list, name='class_list'),
    path('classes/add/', views.class_add, name='class_add'),
    path('classes/<int:pk>/edit/', views.class_edit, name='class_edit'),
    path('classes/<int:pk>/delete/', views.class_delete, name='class_delete'),
    
    path('settings/', views.settings_view, name='settings'),
    path('settings/test-email/', views.test_email_view, name='test_email'),
    path('clear-year/', views.clear_year_view, name='clear_year'),
    
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/add/', views.teacher_add, name='teacher_add'),
    path('teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),
]
