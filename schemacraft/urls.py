from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.norm_admin if hasattr(admin.site, 'norm_admin') else admin.site.urls), # standard or custom
    path('', include('core.urls')),
]
