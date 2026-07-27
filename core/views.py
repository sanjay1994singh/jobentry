from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import JobEntryForm
from .models import BindingType, JobEntry, PaymentThrough, Vendor


def seed_lookup_data():
    for name in ["Perfect Binding", "Center Pin", "Hard Binding"]:
        BindingType.objects.get_or_create(name=name)
    for name in ["Vendor Name"]:
        Vendor.objects.get_or_create(name=name)
    for name in ["Cash", "UPI", "Bank"]:
        PaymentThrough.objects.get_or_create(name=name)


def home(request):
    seed_lookup_data()

    if request.method == "POST":
        form = JobEntryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Job entry saved successfully.")
            return redirect("core:home")
        messages.error(request, "Please fill all required fields correctly.")
    else:
        form = JobEntryForm()

    context = {
        "form": form,
        "next_job_no": JobEntry.next_job_no(),
        "binding_types": BindingType.objects.filter(is_active=True),
        "vendors": Vendor.objects.filter(is_active=True),
        "payment_through_options": PaymentThrough.objects.filter(is_active=True),
    }
    return render(request, "core/home.html", context)
