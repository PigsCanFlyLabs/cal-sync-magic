from django.urls import include, path

urlpatterns = [
    path("farts/", include("cal_sync_magic.urls")),
]
