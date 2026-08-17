from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(url="/api/dashboard/")),
    path("admin/", admin.site.urls),
    path("api/", include("apps.subscriptions.urls")),
]