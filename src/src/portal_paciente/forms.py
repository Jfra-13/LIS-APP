from django import forms
from django.contrib.auth.forms import AuthenticationForm

class PatientLoginForm(AuthenticationForm):
    username = forms.CharField(label="DNI", widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese su DNI'}))
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'}))
