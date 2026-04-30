from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import UserProfile


class CustomRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text='Required. One account per email address.')
    dob = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Date of Birth'
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'dob', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.dob = self.cleaned_data['dob']
            profile.save()
        return user


class ProfileEditForm(forms.Form):
    first_name = forms.CharField(max_length=50, required=False, label='First Name')
    last_name = forms.CharField(max_length=50, required=False, label='Last Name')
    username = forms.CharField(max_length=150, required=True, label='Username')
    phone = forms.CharField(max_length=20, required=False, label='Phone Number')
    bio = forms.CharField(
        required=False,
        label='Bio',
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us a bit about yourself…'})
    )

    def __init__(self, data=None, user=None, **kwargs):
        super().__init__(data, **kwargs)
        self._user = user

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username=username)
        if self._user:
            qs = qs.exclude(pk=self._user.pk)
        if qs.exists():
            raise forms.ValidationError('This username is already taken.')
        return username
