from django.urls import path
from . import views

urlpatterns = [
    # Template Views
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('project/<int:pk>/', views.ProjectEditorView.as_view(), name='project_editor'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # API Endpoints
    path('api/projects/', views.ProjectListCreateAPI.as_view(), name='api_projects'),
    path('api/projects/<int:pk>/', views.ProjectDetailAPI.as_view(), name='api_project_detail'),
    path('api/projects/<int:pk>/parse/', views.ParseSchemaAPI.as_view(), name='api_parse_schema'),
]
