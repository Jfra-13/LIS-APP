from django import forms

class RequestLoginLinkForm(forms.Form):
    dni = forms.CharField(label="DNI", max_length=20, widget=forms.TextInput(attrs={'placeholder': 'Ingresa tu DNI'}))
