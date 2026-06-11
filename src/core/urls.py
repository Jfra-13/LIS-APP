from django.contrib.auth import views as auth_views
from django.urls import path

from . import views


urlpatterns = [
    path("", views.landing, name="landing"),
    path("home/", views.home, name="home"),
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="landing"), name="logout"),
    # Role dashboards (global names — no app namespace)
    path("dashboard/admin/", views.dashboard_admin, name="dashboard_admin"),
    path("dashboard/medico/", views.dashboard_medico, name="dashboard_medico"),
    path("dashboard/enfermero/", views.dashboard_enfermero, name="dashboard_enfermero"),
    path("dashboard/admision/", views.dashboard_admision, name="dashboard_admision"),
]
