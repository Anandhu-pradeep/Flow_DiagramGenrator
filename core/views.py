from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Project, Schema, Node, Edge
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

# Authentication Views
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'auth/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'auth/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('home')

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
