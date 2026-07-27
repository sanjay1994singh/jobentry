from django.contrib import admin

from .models import BindingType, JobEntry, PaymentThrough, Vendor


@admin.register(BindingType)
class BindingTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(PaymentThrough)
class PaymentThroughAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(JobEntry)
class JobEntryAdmin(admin.ModelAdmin):
    list_display = ("job_no", "item_name", "customer_name", "grand_total_amount", "created_at")
    search_fields = ("job_no", "item_name", "customer_name")
    list_filter = ("binding_type", "through", "created_at")
