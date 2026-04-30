from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# User Profile Model - Tracks if user has premium account
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    is_premium = models.BooleanField(default=False)
    dob = models.DateField(blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} Profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    profile, created = UserProfile.objects.get_or_create(user=instance)
    if not created:
        profile.save()

# Project Model – Each user can have multiple Flow Diagram projects
class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# Schema Model – Stores the raw flowchart code for a project
class Schema(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='schema')
    raw_code = models.TextField()  # Raw flow syntax
    json_snapshot = models.JSONField(blank=True, null=True)
    last_parsed = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Schema for {self.project.name}"

# Node Model – Represents a box/node in the Flow Diagram
class Node(models.Model):
    NODE_TYPES = [
        ('process', 'Process (Square)'),
        ('decision', 'Decision (Diamond)'),
        ('start_end', 'Start/End (Rounded)'),
    ]

    schema = models.ForeignKey(Schema, on_delete=models.CASCADE, related_name='nodes')
    name = models.CharField(max_length=100)
    label = models.CharField(max_length=255, blank=True, null=True)
    node_type = models.CharField(max_length=20, choices=NODE_TYPES, default='process')

    def __str__(self):
        return self.label if self.label else self.name

# Edge Model – Represents the arrow/link between nodes
class Edge(models.Model):
    schema = models.ForeignKey(Schema, on_delete=models.CASCADE, related_name='edges')
    from_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='outgoing_edges')
    to_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='incoming_edges')
    label = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.from_node} -> {self.to_node}"
