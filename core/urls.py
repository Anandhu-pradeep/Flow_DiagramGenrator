from django.urls import path
from . import views

urlpatterns = [
    # ── Core Pages ──────────────────────────────
    path('', views.HomeView.as_view(), name='home'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('project/<int:pk>/', views.ProjectEditorView.as_view(), name='project_editor'),
    path('project/<int:pk>/versions/', views.project_versions_view, name='project_versions'),
    path('project/<int:pk>/versions/<int:version_id>/restore/', views.restore_version_view, name='restore_version'),

    # ── Admin ──────────────────────────────────
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin-dashboard/toggle-premium/<int:user_id>/', views.TogglePremiumView.as_view(), name='toggle_premium'),
    path('admin-dashboard/delete-user/<int:user_id>/', views.DeleteUserView.as_view(), name='delete_user'),

    # ── Auth ───────────────────────────────────
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),

    # ── Notifications ──────────────────────────
    path('notifications/', views.notifications_view, name='notifications'),
    path('api/notifications/', views.notifications_api, name='api_notifications'),
    path('api/notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notif_read'),

    # ── Organizations ──────────────────────────
    path('organizations/', views.org_list_view, name='org_list'),
    path('organizations/create/', views.org_create_view, name='org_create'),
    path('organizations/<slug:slug>/', views.org_dashboard_view, name='org_dashboard'),
    path('organizations/<slug:slug>/projects/', views.org_projects_view, name='org_projects'),
    path('organizations/<slug:slug>/invite/', views.org_invite_view, name='org_invite'),
    path('organizations/<slug:slug>/member/<int:member_id>/role/', views.org_change_role_view, name='org_change_role'),
    path('organizations/<slug:slug>/member/<int:member_id>/remove/', views.org_remove_member_view, name='org_remove_member'),

    # ── Invitation respond ─────────────────────
    path('invite/<int:invite_id>/<str:action>/', views.invite_respond_view, name='invite_respond'),

    # ── API Endpoints ──────────────────────────
    path('api/projects/', views.ProjectListCreateAPI.as_view(), name='api_projects'),
    path('api/projects/<int:pk>/', views.ProjectDetailAPI.as_view(), name='api_project_detail'),
    path('api/projects/<int:pk>/parse/', views.ParseSchemaAPI.as_view(), name='api_parse_schema'),
    path('api/users/search/', views.user_search_api, name='user_search'),

    # ── Setup ──────────────────────────────────
    path('setup-admin-secret/', views.setup_admin_view, name='setup_admin'),
]
