from django.contrib import admin

from .models import (
    BindingThrough,
    BindingVendor,
    JobStyle,
    PaperThrough,
    PaperVendor,
    PrintingJobSheet,
    PrintingThrough,
    SystemValue,
)


@admin.register(PaperVendor)
class PaperVendorAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(BindingVendor)
class BindingVendorAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(PrintingThrough)
class PrintingThroughAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(PaperThrough)
class PaperThroughAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(BindingThrough)
class BindingThroughAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(JobStyle)
class JobStyleAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(PrintingJobSheet)
class PrintingJobSheetAdmin(admin.ModelAdmin):
    list_display = ("job_no", "name", "job_date", "printing_total", "binding_total_of_this_job", "updated_at")
    search_fields = ("job_no", "name", "size", "binder")
    list_filter = ("job_date", "created_at")


@admin.register(SystemValue)
class SystemValueAdmin(admin.ModelAdmin):
    list_display = ("mail_from", "mail_to", "mail_cc", "starting_amount", "updated_at")
