from django.urls import path

from . import views


app_name = "paper_job"

urlpatterns = [
    path("", views.index, name="index"),
]
