from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path, re_path

from billing import views

admin.site.site_header = "Radiant Billing admin"

urlpatterns = [
    path("", views.index, name="app"),
    path("login/", auth.LoginView.as_view(template_name="billing/login.html", redirect_authenticated_user=True), name="login"),
    path("logout/", auth.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("api/records", views.records),
    path("api/rev", views.rev),
    path("api/write", views.write),
    path("api/upload", views.upload),
    path("api/ai/config", views.ai_config),
    path("api/ai/complete", views.ai_complete),
    path("api/ai/usage", views.ai_usage),
    path("api/backup", views.backup),
    path("api/restore", views.restore),
    re_path(r"^media/(?P<path>.+)$", views.media),
]
