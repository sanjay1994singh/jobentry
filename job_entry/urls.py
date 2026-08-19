from django.urls import path

from . import views


app_name = "job_entry"

urlpatterns = [
    path("", views.home, name="home"),
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/report/", views.job_report, name="job_report"),
    path("jobs/report.pdf", views.job_report_pdf, name="job_report_pdf"),
    path("app/exit/", views.app_exit, name="app_exit"),
    path("options/", views.options_page, name="options"),
    path("options/data/", views.options_data, name="options_data"),
    path("options/<str:option_key>/save/", views.option_save, name="option_save"),
    path("options/<str:option_key>/<int:pk>/delete/", views.option_delete, name="option_delete"),
    path("system-value/save/", views.system_value_save, name="system_value_save"),
    path("job/first/", views.job_first, name="job_first"),
    path("job/last/", views.job_last, name="job_last"),
    path("job/<int:pk>/", views.home, name="job_edit"),
    path("job/<int:pk>/sheet.pdf", views.job_sheet_pdf, name="job_sheet_pdf"),
    path("job/<int:pk>/send-email/", views.job_send_email, name="job_send_email"),
    path("job/<int:pk>/previous/", views.job_previous, name="job_previous"),
    path("job/<int:pk>/next/", views.job_next, name="job_next"),
]
