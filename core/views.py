from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.text import slugify
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from .forms import CustomRegisterForm, ProfileEditForm
from .models import (
    Project, Schema, Node, Edge, UserProfile,
    Organization, OrganizationMember, OrganizationInvitation,
    Notification, ActivityLog, DiagramVersion
)
from .parser import FlowParser
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.mixins import UserPassesTestMixin


# ─────────────────────────────────────────────
# ADMIN SETUP
# ─────────────────────────────────────────────
def setup_admin_view(request):
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin@123')
        return HttpResponse("Admin created! Username: admin | Password: admin@123")
    return HttpResponse("Admin already exists!")


# ─────────────────────────────────────────────
# CORE TEMPLATE VIEWS
# ─────────────────────────────────────────────
class HomeView(TemplateView):
    template_name = 'home.html'


class DashboardView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'dashboard.html'
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        ctx['is_premium'] = profile.is_premium
        ctx['user_orgs'] = OrganizationMember.objects.filter(
            user=user, is_active=True
        ).select_related('organization')
        return ctx


class ProjectEditorView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'editor.html'
    context_object_name = 'project'


# ─────────────────────────────────────────────
# ADMIN DASHBOARD
# ─────────────────────────────────────────────
class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'admin_dashboard.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        regular_users = User.objects.filter(is_superuser=False, is_staff=False).select_related('profile')
        context['total_users'] = regular_users.count()
        context['all_users'] = regular_users
        context['premium_count'] = UserProfile.objects.filter(
            is_premium=True, user__is_superuser=False, user__is_staff=False
        ).count()
        return context


class TogglePremiumView(LoginRequiredMixin, UserPassesTestMixin, APIView):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.is_premium = not profile.is_premium
        profile.save()
        return redirect('admin_dashboard')


class DeleteUserView(LoginRequiredMixin, UserPassesTestMixin, APIView):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def post(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        if user.is_superuser or user.is_staff:
            messages.error(request, 'Cannot delete admin accounts.')
            return redirect('admin_dashboard')
        user.delete()
        messages.success(request, f'User "{user.username}" has been deleted.')
        return redirect('admin_dashboard')


# ─────────────────────────────────────────────
# AUTHENTICATION VIEWS
# ─────────────────────────────────────────────
def register_view(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'🎉 Registration Successful! Welcome aboard, {user.first_name or user.username}!')
            return redirect('dashboard')
    else:
        form = CustomRegisterForm()
    return render(request, 'auth/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_superuser or user.is_staff:
                messages.success(request, '✅ Welcome, Administrator!')
                return redirect('admin_dashboard')
            messages.success(request, f'✅ Login Successful! Welcome back, {user.first_name or user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, '❌ Incorrect username or password. Please try again.')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


# ─────────────────────────────────────────────
# PROFILE VIEWS
# ─────────────────────────────────────────────
@login_required
def profile_view(request):
    profile, _ = request.user.profile.__class__.objects.get_or_create(user=request.user)
    return render(request, 'profile.html', {'profile': profile})


@login_required
def profile_edit_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if request.method == 'POST':
        form = ProfileEditForm(data=request.POST, user=user)
        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.username = form.cleaned_data['username']
            user.save()
            profile.phone = form.cleaned_data['phone']
            profile.bio = form.cleaned_data['bio']
            profile.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileEditForm(user=user, initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'phone': profile.phone or '',
            'bio': profile.bio or '',
        })
    return render(request, 'profile_edit.html', {'form': form, 'profile': profile})


# ─────────────────────────────────────────────
# NOTIFICATION VIEWS
# ─────────────────────────────────────────────
@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(recipient=request.user).select_related('sender', 'invitation__organization')
    # Mark all as read on page open
    notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications.html', {'notifications': notifs})


@login_required
def notifications_api(request):
    """Returns unread count + latest 10 notifications as JSON for the bell dropdown."""
    notifs = Notification.objects.filter(recipient=request.user).select_related('sender')[:10]
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    data = {
        'unread_count': unread_count,
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notif_type,
                'is_read': n.is_read,
                'sender': n.sender.username if n.sender else 'System',
                'created_at': n.created_at.strftime('%b %d, %H:%M'),
                'invitation_id': n.invitation_id,
            }
            for n in notifs
        ]
    }
    return JsonResponse(data)


@login_required
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(Notification, id=notif_id, recipient=request.user)
    notif.is_read = True
    notif.save()
    return JsonResponse({'status': 'ok'})


# ─────────────────────────────────────────────
# ORGANIZATION VIEWS
# ─────────────────────────────────────────────
@login_required
def org_list_view(request):
    """Shows all orgs the user is a member of, or a premium-gate."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    memberships = OrganizationMember.objects.filter(
        user=request.user, is_active=True
    ).select_related('organization')
    return render(request, 'org/org_list.html', {
        'memberships': memberships,
        'is_premium': profile.is_premium,
    })


@login_required
def org_create_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if not profile.is_premium:
        messages.error(request, '🔒 Unlock Premium to Access Organization Features.')
        return redirect('org_list')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'Organization name is required.')
            return render(request, 'org/org_create.html')

        slug = slugify(name)
        # ensure unique slug
        base_slug = slug
        counter = 1
        while Organization.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization.objects.create(
            name=name, slug=slug, description=description, owner=request.user
        )
        # Owner is also a member with 'owner' role
        OrganizationMember.objects.create(organization=org, user=request.user, role='owner')

        ActivityLog.objects.create(
            actor=request.user, organization=org,
            action='org_created', detail=f'Created organization "{org.name}"'
        )
        messages.success(request, f'🏢 Organization "{org.name}" created successfully!')
        return redirect('org_dashboard', slug=org.slug)

    return render(request, 'org/org_create.html')


@login_required
def org_dashboard_view(request, slug):
    org = get_object_or_404(Organization, slug=slug)
    # Check membership
    try:
        membership = OrganizationMember.objects.get(organization=org, user=request.user, is_active=True)
    except OrganizationMember.DoesNotExist:
        messages.error(request, 'You are not a member of this organization.')
        return redirect('org_list')

    members = OrganizationMember.objects.filter(organization=org, is_active=True).select_related('user', 'user__profile')
    pending_invites = OrganizationInvitation.objects.filter(organization=org, status='pending').select_related('invitee', 'invited_by')
    activity = ActivityLog.objects.filter(organization=org)[:15]
    shared_projects = Project.objects.filter(organization=org)

    return render(request, 'org/org_dashboard.html', {
        'org': org,
        'membership': membership,
        'members': members,
        'pending_invites': pending_invites,
        'activity': activity,
        'shared_projects': shared_projects,
        'is_owner': membership.role == 'owner',
        'can_manage': membership.can_manage_members(),
        'can_edit': membership.can_edit(),
    })


@login_required
def org_projects_view(request, slug):
    org = get_object_or_404(Organization, slug=slug)
    try:
        membership = OrganizationMember.objects.get(organization=org, user=request.user, is_active=True)
    except OrganizationMember.DoesNotExist:
        messages.error(request, 'Access denied.')
        return redirect('org_list')

    projects = Project.objects.filter(organization=org).order_by('-updated_at')

    return render(request, 'org/org_projects.html', {
        'org': org,
        'membership': membership,
        'projects': projects,
        'can_manage': membership.can_manage_members(),
        'can_edit': membership.can_edit(),
    })


@login_required
def org_invite_view(request, slug):
    org = get_object_or_404(Organization, slug=slug)
    try:
        membership = OrganizationMember.objects.get(organization=org, user=request.user, is_active=True)
    except OrganizationMember.DoesNotExist:
        messages.error(request, 'Access denied.')
        return redirect('org_list')

    if not membership.can_manage_members():
        messages.error(request, 'Only owners and admins can invite members.')
        return redirect('org_dashboard', slug=slug)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        role = request.POST.get('role', 'viewer')

        try:
            invitee = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, f'❌ User "{username}" not found.')
            return redirect('org_invite', slug=slug)

        if invitee == request.user:
            messages.error(request, 'You cannot invite yourself.')
            return redirect('org_invite', slug=slug)

        if OrganizationMember.objects.filter(organization=org, user=invitee, is_active=True).exists():
            messages.error(request, f'{username} is already a member.')
            return redirect('org_invite', slug=slug)

        invite, created = OrganizationInvitation.objects.get_or_create(
            organization=org, invitee=invitee,
            defaults={'invited_by': request.user, 'role': role, 'status': 'pending'}
        )
        if not created:
            if invite.status == 'pending':
                messages.warning(request, f'An invitation is already pending for {username}.')
                return redirect('org_invite', slug=slug)
            else:
                invite.status = 'pending'
                invite.role = role
                invite.invited_by = request.user
                invite.responded_at = None
                invite.save()

        # Create notification for invitee
        Notification.objects.create(
            recipient=invitee,
            sender=request.user,
            notif_type='org_invite',
            title=f'Organization Invitation',
            message=f'{request.user.username} invited you to join "{org.name}" as {role}.',
            invitation=invite,
        )
        ActivityLog.objects.create(
            actor=request.user, organization=org,
            action='invite_sent', detail=f'Invited {username} as {role}'
        )
        messages.success(request, f'✉️ Invitation sent to {username}!')
        return redirect('org_dashboard', slug=slug)

    return render(request, 'org/org_invite.html', {'org': org, 'membership': membership})


@login_required
def invite_respond_view(request, invite_id, action):
    """action = 'accept' or 'reject'"""
    invite = get_object_or_404(OrganizationInvitation, id=invite_id, invitee=request.user, status='pending')
    org = invite.organization

    if action == 'accept':
        OrganizationMember.objects.get_or_create(
            organization=org, user=request.user,
            defaults={'role': invite.role}
        )
        invite.status = 'accepted'
        invite.responded_at = timezone.now()
        invite.save()

        # Notify inviter
        Notification.objects.create(
            recipient=invite.invited_by,
            sender=request.user,
            notif_type='invite_accepted',
            title='Invitation Accepted',
            message=f'{request.user.username} accepted your invitation to "{org.name}".',
        )
        ActivityLog.objects.create(
            actor=request.user, organization=org,
            action='invite_accepted', detail=f'{request.user.username} joined as {invite.role}'
        )
        messages.success(request, f'✅ You joined "{org.name}" as {invite.role}!')
        return redirect('org_dashboard', slug=org.slug)

    elif action == 'reject':
        invite.status = 'rejected'
        invite.responded_at = timezone.now()
        invite.save()

        Notification.objects.create(
            recipient=invite.invited_by,
            sender=request.user,
            notif_type='invite_rejected',
            title='Invitation Rejected',
            message=f'{request.user.username} declined your invitation to "{org.name}".',
        )
        ActivityLog.objects.create(
            actor=request.user, organization=org,
            action='invite_rejected', detail=f'{request.user.username} rejected invite'
        )
        messages.info(request, f'You declined the invitation to "{org.name}".')

    return redirect('notifications')


@login_required
def org_change_role_view(request, slug, member_id):
    org = get_object_or_404(Organization, slug=slug)
    try:
        requester = OrganizationMember.objects.get(organization=org, user=request.user, is_active=True)
    except OrganizationMember.DoesNotExist:
        messages.error(request, 'Access denied.')
        return redirect('org_list')

    if not requester.can_manage_members():
        messages.error(request, 'Permission denied.')
        return redirect('org_dashboard', slug=slug)

    target = get_object_or_404(OrganizationMember, id=member_id, organization=org)
    if target.role == 'owner':
        messages.error(request, "Cannot change the owner's role.")
        return redirect('org_dashboard', slug=slug)

    new_role = request.POST.get('role', 'viewer')
    old_role = target.role
    target.role = new_role
    target.save()

    Notification.objects.create(
        recipient=target.user,
        sender=request.user,
        notif_type='role_changed',
        title='Role Updated',
        message=f'Your role in "{org.name}" changed from {old_role} to {new_role}.',
    )
    ActivityLog.objects.create(
        actor=request.user, organization=org,
        action='role_changed',
        detail=f'{target.user.username} role: {old_role} → {new_role}'
    )
    messages.success(request, f'Role updated to {new_role}.')
    return redirect('org_dashboard', slug=slug)


@login_required
def org_remove_member_view(request, slug, member_id):
    org = get_object_or_404(Organization, slug=slug)
    try:
        requester = OrganizationMember.objects.get(organization=org, user=request.user, is_active=True)
    except OrganizationMember.DoesNotExist:
        messages.error(request, 'Access denied.')
        return redirect('org_list')

    if not requester.can_manage_members():
        messages.error(request, 'Permission denied.')
        return redirect('org_dashboard', slug=slug)

    target = get_object_or_404(OrganizationMember, id=member_id, organization=org)
    if target.role == 'owner':
        messages.error(request, "Cannot remove the organization owner.")
        return redirect('org_dashboard', slug=slug)

    target.is_active = False
    target.save()
    ActivityLog.objects.create(
        actor=request.user, organization=org,
        action='member_removed',
        detail=f'{target.user.username} removed from organization'
    )
    messages.success(request, f'{target.user.username} removed from organization.')
    return redirect('org_dashboard', slug=slug)


# ─────────────────────────────────────────────
# VERSION HISTORY
# ─────────────────────────────────────────────
@login_required
def project_versions_view(request, pk):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    versions = DiagramVersion.objects.filter(project=project).select_related('editor')
    return render(request, 'versions.html', {'project': project, 'versions': versions})


@login_required
def restore_version_view(request, pk, version_id):
    project = get_object_or_404(Project, pk=pk, user=request.user)
    version = get_object_or_404(DiagramVersion, id=version_id, project=project)
    schema, _ = Schema.objects.get_or_create(project=project)
    schema.raw_code = version.raw_code
    schema.save()
    messages.success(request, f'✅ Restored to version #{version.version_number}')
    return redirect('project_editor', pk=pk)


# ─────────────────────────────────────────────
# API ENDPOINTS
# ─────────────────────────────────────────────
class ProjectListCreateAPI(generics.ListCreateAPIView):
    queryset = Project.objects.all()

    def get(self, request):
        projects = Project.objects.filter(user=request.user)
        data = [{"id": p.id, "name": p.name} for p in projects]
        return Response(data)

    def post(self, request):
        name = request.data.get('name')
        org_id = request.data.get('org_id')

        new_proj = Project.objects.create(name=name, user=request.user)

        if org_id:
            try:
                org = Organization.objects.get(id=org_id)
                member = OrganizationMember.objects.filter(organization=org, user=request.user, is_active=True).first()
                if member and member.can_edit():
                    new_proj.organization = org
                    new_proj.is_shared = True
                    new_proj.save()
            except Organization.DoesNotExist:
                pass

        default_code = "ErStart\n1->(start)\n1-2[content]\n2-\"yes\"-3{ok}\n3-\"no\"-2\n3-4->(stop)\nErStop"
        Schema.objects.create(project=new_proj, raw_code=default_code)
        
        detail_msg = f'Created project "{name}"'
        if new_proj.organization:
            detail_msg += f' in organization'
            ActivityLog.objects.create(
                actor=request.user, organization=new_proj.organization, project=new_proj,
                action='project_created', detail=detail_msg
            )
        else:
            ActivityLog.objects.create(
                actor=request.user, project=new_proj,
                action='project_created', detail=detail_msg
            )

        return Response({"id": new_proj.id, "name": new_proj.name}, status=status.HTTP_201_CREATED)


class ProjectDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk, user=request.user)
        schema = getattr(project, 'schema', None)
        return Response({
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "schema_code": schema.raw_code if schema else ""
        })

    def put(self, request, pk):
        project = get_object_or_404(Project, pk=pk, user=request.user)
        schema_code = request.data.get('schema_code')
        schema, created = Schema.objects.get_or_create(project=project)

        # Auto-save version before overwriting
        last_version = DiagramVersion.objects.filter(project=project).order_by('-version_number').first()
        next_num = (last_version.version_number + 1) if last_version else 1
        DiagramVersion.objects.create(
            project=project,
            editor=request.user,
            raw_code=schema.raw_code,
            version_number=next_num,
        )
        # Keep max 20 versions
        old_versions = DiagramVersion.objects.filter(project=project).order_by('-version_number')[20:]
        for v in old_versions:
            v.delete()

        schema.raw_code = schema_code
        schema.save()
        ActivityLog.objects.create(
            actor=request.user, project=project,
            action='project_edited', detail=f'Edited diagram'
        )
        return Response({"status": "success"})


class ParseSchemaAPI(APIView):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, user=request.user)
        raw_code = request.data.get('schema_code')
        parser = FlowParser(raw_code)
        parsed_data = parser.parse()
        mermaid_code = parser.to_mermaid()
        return Response({
            "mermaid_code": mermaid_code,
            "parsed_data": parsed_data
        })


# User search API for invitation
@login_required
def user_search_api(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'users': []})
    users = User.objects.filter(username__icontains=q).exclude(id=request.user.id)[:8]
    return JsonResponse({'users': [{'username': u.username, 'name': f'{u.first_name} {u.last_name}'.strip()} for u in users]})
