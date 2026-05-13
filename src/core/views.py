from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_GET


@require_GET
def landing(request):
    if request.user.is_authenticated:
        return redirect("home")
    return TemplateResponse(request, "core/landing.html")


@login_required
def home(request):
    return TemplateResponse(request, "core/home.html")
