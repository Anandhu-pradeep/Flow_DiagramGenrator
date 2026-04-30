from django.urls import path
from . import views

urlpatterns = [
    # Template Views
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('project/<int:pk>/', views.ProjectEditorView.as_view(), name='project_editor'),
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-dashboard/toggle-premium/<int:user_id>/', views.TogglePremiumView.as_view(), name='toggle_premium'),
    path('admin-dashboard/delete-user/<int:user_id>/', views.DeleteUserView.as_view(), name='delete_user'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),

    # API Endpoints
    path('api/projects/', views.ProjectListCreateAPI.as_view(), name='api_projects'),
    path('api/projects/<int:pk>/', views.ProjectDetailAPI.as_view(), name='api_project_detail'),
    path('api/projects/<int:pk>/parse/', views.ParseSchemaAPI.as_view(), name='api_parse_schema'),
]
