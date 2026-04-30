from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from .forms import CustomRegisterForm, ProfileEditForm
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from .models import Project, Schema, Node, Edge, UserProfile
from .parser import FlowParser
from django.http import JsonResponse

# Template-based Views
class HomeView(TemplateView):
    template_name = 'home.html'

class DashboardView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'dashboard.html'
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

class ProjectEditorView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'editor.html'
    context_object_name = 'project'

from django.contrib.auth.mixins import UserPassesTestMixin

class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'admin_dashboard.html'

    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Exclude admins/staff — only show regular users
        regular_users = User.objects.filter(is_superuser=False, is_staff=False).select_related('profile')
        context['total_users'] = regular_users.count()
        context['all_users'] = regular_users
        context['premium_count'] = UserProfile.objects.filter(is_premium=True, user__is_superuser=False, user__is_staff=False).count()
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
        # Safety: never delete another superuser/staff
        if user.is_superuser or user.is_staff:
            messages.error(request, 'Cannot delete admin accounts.')
            return redirect('admin_dashboard')
        user.delete()
        messages.success(request, f'User "{user.username}" has been deleted.')
        return redirect('admin_dashboard')

# Authentication Views
def register_view(request):
    if request.method == 'POST':
        form = CustomRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomRegisterForm()
    return render(request, 'auth/register.html', {'form': form})

from django.contrib import messages

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_superuser or user.is_staff:
                messages.success(request, 'Welcome administrator')
                return redirect('admin_dashboard')
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

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
        # form invalid — fall through and re-render with errors
    else:
        form = ProfileEditForm(user=user, initial={
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
            'phone': profile.phone or '',
            'bio': profile.bio or '',
        })
    return render(request, 'profile_edit.html', {'form': form, 'profile': profile})

# API Endpoints (DRF)
class ProjectListCreateAPI(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    # Manual Serializer logic or basic dicts for now to keep it simple
    def get(self, request):
        projects = Project.objects.filter(user=request.user)
        data = [{"id": p.id, "name": p.name} for p in projects]
        return Response(data)
    
    def post(self, request):
        name = request.data.get('name')
        new_proj = Project.objects.create(name=name, user=request.user)
        # Initialize a default flowchart with the requested syntax
        default_code = "ErStart\n1([start])\n1-2[content]\n2-\"yes\"-3{ok}\n3-\"no\"-2\n3-4([stop])\nErStop"
        Schema.objects.create(project=new_proj, raw_code=default_code)
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
        schema.raw_code = schema_code
        schema.save()
        return Response({"status": "success"})

class ParseSchemaAPI(APIView):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, user=request.user)
        raw_code = request.data.get('schema_code')
        
        parser = FlowParser(raw_code)
        parsed_data = parser.parse()
        mermaid_code = parser.to_mermaid()
        
        # Optionally persist parsed entities/attributes here
        # For this version, we return the mermaid code for the live preview
        return Response({
            "mermaid_code": mermaid_code,
            "parsed_data": parsed_data
        })
