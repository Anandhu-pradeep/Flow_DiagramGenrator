from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# ──────────────────────────────────────────────
# User Profile – premium flag + metadata
# ──────────────────────────────────────────────
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
        UserProfile.objects.create(user=instance, is_premium=instance.is_superuser)
    else:
        if instance.is_superuser and hasattr(instance, 'profile') and not instance.profile.is_premium:
            instance.profile.is_premium = True
            instance.profile.save()


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    profile, created = UserProfile.objects.get_or_create(user=instance)
    if not created:
        profile.save()


# ──────────────────────────────────────────────
# Project – personal flow diagram project
# ──────────────────────────────────────────────
class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    organization = models.ForeignKey(
        'Organization', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='projects'
    )
    is_shared = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────
# Schema – raw flowchart code for a project
# ──────────────────────────────────────────────
class Schema(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='schema')
    raw_code = models.TextField()
    json_snapshot = models.JSONField(blank=True, null=True)
    last_parsed = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Schema for {self.project.name}"


# ──────────────────────────────────────────────
# Node / Edge – parsed diagram elements
# ──────────────────────────────────────────────
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


class Edge(models.Model):
    schema = models.ForeignKey(Schema, on_delete=models.CASCADE, related_name='edges')
    from_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='outgoing_edges')
    to_node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name='incoming_edges')
    label = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.from_node} -> {self.to_node}"


# ──────────────────────────────────────────────
# Diagram Version – auto-saved history
# ──────────────────────────────────────────────
class DiagramVersion(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='versions')
    editor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    raw_code = models.TextField()
    version_number = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"v{self.version_number} of {self.project.name} by {self.editor}"


# ──────────────────────────────────────────────
# Organization
# ──────────────────────────────────────────────
class Organization(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    logo_url = models.URLField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_orgs')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def member_count(self):
        return self.members.filter(is_active=True).count()

    def active_project_count(self):
        return self.projects.count()


# ──────────────────────────────────────────────
# Organization Member
# ──────────────────────────────────────────────
class OrganizationMember(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='org_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('organization', 'user')

    def __str__(self):
        return f"{self.user.username} @ {self.organization.name} [{self.role}]"

    def can_manage_members(self):
        return self.role in ('owner', 'admin')

    def can_edit(self):
        return self.role in ('owner', 'admin', 'editor')

    def can_view(self):
        return self.is_active


# ──────────────────────────────────────────────
# Organization Invitation
# ──────────────────────────────────────────────
class OrganizationInvitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invitee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    role = models.CharField(max_length=20, choices=OrganizationMember.ROLE_CHOICES, default='viewer')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('organization', 'invitee')

    def __str__(self):
        return f"Invite: {self.invitee.username} → {self.organization.name} [{self.status}]"


# ──────────────────────────────────────────────
# Notification
# ──────────────────────────────────────────────
class Notification(models.Model):
    TYPE_CHOICES = [
        ('org_invite', 'Organization Invite'),
        ('invite_accepted', 'Invite Accepted'),
        ('invite_rejected', 'Invite Rejected'),
        ('role_changed', 'Role Changed'),
        ('project_shared', 'Project Shared'),
        ('member_joined', 'Member Joined'),
        ('collab_request', 'Collaboration Request'),
        ('comment_mention', 'Comment Mention'),
        ('general', 'General'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    notif_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    # For invitation-linked notifications
    invitation = models.ForeignKey(OrganizationInvitation, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notif → {self.recipient.username}: {self.title}"


# ──────────────────────────────────────────────
# Activity Log
# ──────────────────────────────────────────────
class ActivityLog(models.Model):
    ACTION_CHOICES = [
        ('project_created', 'Project Created'),
        ('project_edited', 'Project Edited'),
        ('diagram_exported', 'Diagram Exported'),
        ('member_joined', 'Member Joined'),
        ('member_removed', 'Member Removed'),
        ('invite_sent', 'Invite Sent'),
        ('invite_accepted', 'Invite Accepted'),
        ('invite_rejected', 'Invite Rejected'),
        ('role_changed', 'Role Changed'),
        ('org_created', 'Organization Created'),
        ('comment_added', 'Comment Added'),
    ]

    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='activity_logs')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='activity_logs')
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.actor} → {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"
