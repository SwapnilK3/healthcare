"""
URL configuration for healthcare project.
Refactored to use single accounts app with role-based users.
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def api_root(request):
    """API Root - shows all available endpoints."""
    return JsonResponse({
        'message': 'Welcome to Healthcare Backend API',
        'version': '2.0',
        'description': 'PostgreSQL + ViewSets - Role-based User model',
        'endpoints': {
            'auth': {
                'register': '/api/auth/register/',
                'login': '/api/auth/login/',
                'token_refresh': '/api/auth/token/refresh/',
            },
            'doctors': {
                'list_create': '/api/doctors/',
                'detail': '/api/doctors/<uuid:id>/',
            },
            'patients': {
                'list_create': '/api/patients/',
                'detail': '/api/patients/<uuid:id>/',
            },
            'mappings': {
                'list_create': '/api/mappings/',
                'patient_doctors': '/api/mappings/patient/<uuid:patient_id>/',
                'delete': '/api/mappings/<uuid:id>/',
            },
        },
        'admin': '/admin/',
    })


urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
]
