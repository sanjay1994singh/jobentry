from datetime import datetime
from io import BytesIO
from decimal import Decimal, InvalidOperation
import os
import threading
import time

from django.contrib import messages
from django.core.mail import EmailMessage
from django.db import IntegrityError
from django.db import OperationalError, ProgrammingError
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from harinam_paper.backup import backup_database

from .models import (
    BindingVendor,
    JobStyle,
    PaperVendor,
    PrintingJobSheet,
    SystemValue,
)


OPTION_MODELS = {
    "job_style": ("Job Style", JobStyle),
    "paper_vendor": ("Paper Vendor", PaperVendor),
    "binding_vendor": ("Binding Vendor", BindingVendor),
}


def table_ready(model):
    try:
        model.objects.exists()
        return True
    except (OperationalError, ProgrammingError):
        return False


def active_options(model):
    if not table_ready(model):
        return []
    return model.objects.filter(is_active=True)


def active_options_payload(model):
    return [{"id": option.pk, "name": option.name} for option in active_options(model)]


def saved_option_missing(model, value):
    if not value or not table_ready(model):
        return False
    return not model.objects.filter(name=value, is_active=True).exists()


def normalize_lookup_names(model):
    if not table_ready(model):
        return
    for option in model.objects.all():
        uppercase_name = option.name.strip().upper()
        if not uppercase_name:
            option.delete()
            continue
        if option.name == uppercase_name:
            continue
        duplicate = model.objects.filter(name=uppercase_name).exclude(pk=option.pk).first()
        if duplicate:
            option.delete()
        else:
            option.name = uppercase_name
            option.save(update_fields=["name"])


def decimal_post(request, name):
    value = (request.POST.get(name) or "").strip()
    if not value:
        return Decimal("0")
    value = value.replace(",", "")
    if "." in value:
        value = value.split(".", 1)[0]
    value = "".join(char for char in value if char.isdigit())
    if not value:
        return Decimal("0")
    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal("0")


def int_post(request, name):
    value = (request.POST.get(name) or "").strip()
    if not value:
        return 0
    try:
        return int(Decimal(value.replace(",", "")))
    except (InvalidOperation, ValueError):
        return 0


def optional_int_post(request, name):
    value = (request.POST.get(name) or "").strip()
    return optional_int_value(value)


def optional_int_value(value):
    value = (value or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def text_post(request, name):
    return (request.POST.get(name) or "").strip().upper()


def selected_option_post(request, name):
    value = text_post(request, name)
    if not value or value.startswith("SELECT "):
        return ""
    return value


def option_snapshot_post(request, model, name_field, id_field, current_id=None):
    selected_name = text_post(request, name_field)
    selected_id = optional_int_post(request, id_field)
    if not selected_name:
        return None, ""
    if selected_id and table_ready(model):
        option = model.objects.filter(pk=selected_id, name=selected_name).first()
        if option:
            return option.pk, option.name
    if table_ready(model):
        option = model.objects.filter(name=selected_name).first()
        if option:
            return option.pk, option.name
    return current_id, selected_name


def date_post(request, name):
    value = text_post(request, name)
    if not value:
        return timezone.localdate()
    parsed_date = date_filter_value(value)
    return parsed_date or timezone.localdate()


def date_filter_value(value):
    value = (value or "").strip()
    if not value:
        return None
    for date_format in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            pass
    return None


def display_date(value):
    if not value:
        return timezone.localdate().strftime("%d-%m-%Y")
    return value.strftime("%d-%m-%Y")


def display_amount(value, blank_zero=True):
    if value is None:
        return ""
    if blank_zero and Decimal(value) == Decimal("0"):
        return ""
    rounded = Decimal(value).quantize(Decimal("1"))
    return str(rounded)


def pdf_amount(value):
    return display_amount(value, blank_zero=False)


def vendor_account_totals(current_job=None):
    jobs = PrintingJobSheet.objects.order_by()
    if current_job:
        jobs = jobs.filter(job_no__lt=current_job.job_no)
    totals = {"paper": {}, "binding": {}}
    for row in (
        jobs.exclude(paper_vendor="")
        .values("paper_vendor")
        .annotate(bill=Sum("paper_total_rs"), paid=Sum("paper_paid_amount"))
    ):
        totals["paper"][row["paper_vendor"]] = {
            "bill": display_amount(row["bill"] or Decimal("0"), blank_zero=False),
            "paid": display_amount(row["paid"] or Decimal("0"), blank_zero=False),
        }
    for row in (
        jobs.exclude(binding_vendor="")
        .values("binding_vendor")
        .annotate(bill=Sum("binding_total_rs"), paid=Sum("binding_paid_rs"))
    ):
        totals["binding"][row["binding_vendor"]] = {
            "bill": display_amount(row["bill"] or Decimal("0"), blank_zero=False),
            "paid": display_amount(row["paid"] or Decimal("0"), blank_zero=False),
        }
    return totals


def vendor_total_decimal(totals, section, vendor, key):
    try:
        return Decimal(totals[section][vendor][key])
    except (KeyError, InvalidOperation):
        return Decimal("0")


def next_prev_balance(system_value):
    latest_job = PrintingJobSheet.objects.order_by("-job_no").first()
    if latest_job:
        return running_summary_balance_until(latest_job, system_value)["balance"]
    return system_value.starting_amount


def running_summary_balance_until(current_job, system_value):
    previous_balance = system_value.starting_amount
    if not current_job:
        return {"prev": previous_balance, "balance": previous_balance}

    previous_jobs = PrintingJobSheet.objects.filter(job_no__lt=current_job.job_no).order_by("job_no")
    if current_job.pk:
        previous_jobs = previous_jobs.exclude(pk=current_job.pk)

    for job in previous_jobs:
        previous_balance = previous_balance + job.printing_total - job.printing_paid_rs

    current_balance = previous_balance + current_job.printing_total - current_job.printing_paid_rs
    return {"prev": previous_balance, "balance": current_balance}


def running_summary_prev_for_job(job, system_value):
    target_job_no = job.job_no or PrintingJobSheet.next_job_no()
    previous_balance = system_value.starting_amount
    previous_jobs = PrintingJobSheet.objects.filter(job_no__lt=target_job_no).order_by("job_no")
    if job.pk:
        previous_jobs = previous_jobs.exclude(pk=job.pk)

    for previous_job in previous_jobs:
        previous_balance = previous_balance + previous_job.printing_total - previous_job.printing_paid_rs
    return previous_balance


def has_printing_job_sheet_data(request):
    text_fields = [
        "job_name",
        "job_size",
        "job_page",
        "job_copies",
        "job_ink",
        "job_ss_fb",
        "job_binder",
        "job_style",
        "printing_lam_uv",
        "printing_bdg",
        "printing_other_gst",
        "printing_paper_details",
        "printing_reference",
        "printing_thru",
        "paper_qty",
        "paper_size",
        "paper_quality",
        "paper_gsm",
        "paper_discount_2",
        "paper_reference",
        "paper_vendor",
        "paper_thru",
        "binding_discount",
        "binding_qty",
        "binding_rate_rate",
        "binding_reference",
        "binding_vendor",
        "binding_thru",
    ]
    number_fields = [
        "printing_plates_qty",
        "printing_plates_price",
        "printing_ptg_qty",
        "printing_ptg_price",
        "printing_lam_uv_price",
        "printing_bdg_price",
        "printing_other_gst_price",
        "printing_paper_amount",
        "printing_paid_rs",
        "paper_total_rs",
        "paper_paid_amount",
        "binding_total_rs",
        "binding_paid_rs",
        "summary_prev_bal",
    ]

    if any(text_post(request, field) for field in text_fields):
        return True
    return any(decimal_post(request, field) != Decimal("0") for field in number_fields)


def assign_printing_job_sheet(job, request):
    job.job_date = date_post(request, "job_date")
    job.name = text_post(request, "job_name")
    job.size = text_post(request, "job_size")
    job.page = text_post(request, "job_page")
    job.copies = text_post(request, "job_copies")
    job.ink = text_post(request, "job_ink")
    job.ss_fb = text_post(request, "job_ss_fb")
    job.binder = text_post(request, "job_binder")
    job.job_style_id_snapshot, job.job_style = option_snapshot_post(
        request, JobStyle, "job_style", "job_style_id_snapshot", job.job_style_id_snapshot
    )

    job.printing_plates_qty = decimal_post(request, "printing_plates_qty")
    job.printing_plates_price = decimal_post(request, "printing_plates_price")
    job.printing_ptg_qty = decimal_post(request, "printing_ptg_qty")
    job.printing_ptg_price = decimal_post(request, "printing_ptg_price")
    job.printing_lam_uv = text_post(request, "printing_lam_uv")
    job.printing_lam_uv_price = decimal_post(request, "printing_lam_uv_price")
    job.printing_bdg = text_post(request, "printing_bdg")
    job.printing_bdg_price = decimal_post(request, "printing_bdg_price")
    job.printing_other_gst = text_post(request, "printing_other_gst")
    job.printing_other_gst_price = decimal_post(request, "printing_other_gst_price")
    job.printing_paper_details = text_post(request, "printing_paper_details")
    job.printing_paper_amount = decimal_post(request, "printing_paper_amount")
    job.printing_paid_rs = decimal_post(request, "printing_paid_rs")
    job.printing_paid_date = date_post(request, "printing_paid_date")
    job.printing_reference = text_post(request, "printing_reference")
    job.printing_thru_id_snapshot = None
    job.printing_thru = text_post(request, "printing_thru")

    job.paper_qty = text_post(request, "paper_qty")
    job.paper_size = text_post(request, "paper_size")
    job.paper_quality = text_post(request, "paper_quality")
    job.paper_gsm = text_post(request, "paper_gsm")
    job.paper_total_rs = decimal_post(request, "paper_total_rs")
    job.paper_discount_2 = text_post(request, "paper_discount_2")
    job.paper_paid_amount = decimal_post(request, "paper_paid_amount")
    job.paper_paid_date = date_post(request, "paper_paid_date")
    job.paper_reference = text_post(request, "paper_reference")
    job.paper_vendor_id_snapshot, job.paper_vendor = option_snapshot_post(
        request, PaperVendor, "paper_vendor", "paper_vendor_id_snapshot", job.paper_vendor_id_snapshot
    )
    job.paper_thru_id_snapshot = None
    job.paper_thru = text_post(request, "paper_thru")

    job.binding_qty = text_post(request, "binding_qty")
    job.binding_rate_rate = text_post(request, "binding_rate_rate")
    job.binding_total_rs = decimal_post(request, "binding_total_rs")
    job.binding_discount = text_post(request, "binding_discount")
    job.binding_paid_rs = decimal_post(request, "binding_paid_rs")
    job.binding_paid_date = date_post(request, "binding_paid_date")
    job.binding_reference = text_post(request, "binding_reference")
    job.binding_vendor_id_snapshot, job.binding_vendor = option_snapshot_post(
        request, BindingVendor, "binding_vendor", "binding_vendor_id_snapshot", job.binding_vendor_id_snapshot
    )
    job.binding_thru_id_snapshot = None
    job.binding_thru = text_post(request, "binding_thru")

    job.summary_prev_bal = decimal_post(request, "summary_prev_bal")
    return job


def seed_lookup_data():
    for _label, model in OPTION_MODELS.values():
        normalize_lookup_names(model)


def home(request, pk=None):
    seed_lookup_data()
    current_job = get_object_or_404(PrintingJobSheet, pk=pk) if pk else None
    system_value = SystemValue.load()

    if request.method == "POST":
        if not current_job and system_value.starting_amount == Decimal("0"):
            messages.error(request, "Please System Value me jaakar STARTING AMOUNT fill karein, fir form fill karein.")
            return redirect("job_entry:home")
        if not has_printing_job_sheet_data(request):
            messages.error(request, "Blank form save nahi hoga. Pehle koi field fill karein.")
            return redirect("job_entry:job_edit", pk=current_job.pk) if current_job else redirect("job_entry:home")
        if not selected_option_post(request, "paper_vendor") or not selected_option_post(request, "binding_vendor"):
            messages.error(request, "Paper Vendor aur Binding Vendor select karein.")
            return redirect("job_entry:job_edit", pk=current_job.pk) if current_job else redirect("job_entry:home")
        job = current_job or PrintingJobSheet()
        assign_printing_job_sheet(job, request)
        job.summary_prev_bal = running_summary_prev_for_job(job, system_value)
        job.save()
        if current_job:
            messages.success(request, "Job entry successfully updated.")
            return redirect("job_entry:job_edit", pk=job.pk)
        messages.success(request, "Job entry successfully saved.")
        return redirect("%s?saved=1" % redirect("job_entry:home").url)

    context = {
        "current_job": current_job,
        "next_job_no": current_job.job_no if current_job else PrintingJobSheet.next_job_no(),
        "job_date_value": display_date(current_job.job_date) if current_job else display_date(None),
        "printing_paid_date_value": display_date(current_job.printing_paid_date) if current_job else display_date(None),
        "paper_paid_date_value": display_date(current_job.paper_paid_date) if current_job else display_date(None),
        "binding_paid_date_value": display_date(current_job.binding_paid_date) if current_job else display_date(None),
        "paper_vendor_options": active_options(PaperVendor),
        "binding_vendor_options": active_options(BindingVendor),
        "job_style_options": active_options(JobStyle),
        "job_style_saved_missing": saved_option_missing(JobStyle, current_job.job_style) if current_job else False,
        "paper_vendor_saved_missing": saved_option_missing(PaperVendor, current_job.paper_vendor) if current_job else False,
        "binding_vendor_saved_missing": saved_option_missing(BindingVendor, current_job.binding_vendor) if current_job else False,
        "system_value": system_value,
    }
    summary_running = running_summary_balance_until(current_job, system_value)
    context["summary_prev_bal_value"] = summary_running["prev"] if current_job else next_prev_balance(context["system_value"])
    amount_source = current_job
    vendor_totals = vendor_account_totals(current_job)
    paper_bill_base = vendor_total_decimal(vendor_totals, "paper", current_job.paper_vendor, "bill") if current_job else Decimal("0")
    paper_paid_base = vendor_total_decimal(vendor_totals, "paper", current_job.paper_vendor, "paid") if current_job else Decimal("0")
    binding_bill_base = vendor_total_decimal(vendor_totals, "binding", current_job.binding_vendor, "bill") if current_job else Decimal("0")
    binding_paid_base = vendor_total_decimal(vendor_totals, "binding", current_job.binding_vendor, "paid") if current_job else Decimal("0")
    first_job = PrintingJobSheet.objects.order_by("job_no").first()
    last_job = PrintingJobSheet.objects.order_by("-job_no").first()
    previous_job = (
        PrintingJobSheet.objects.filter(job_no__lt=current_job.job_no).order_by("-job_no").first()
        if current_job else None
    )
    next_job = (
        PrintingJobSheet.objects.filter(job_no__gt=current_job.job_no).order_by("job_no").first()
        if current_job else None
    )
    context.update({
        "printing_plates_total_value": display_amount(amount_source.printing_plates_total) if amount_source else "",
        "printing_ptg_total_value": display_amount(amount_source.printing_ptg_total) if amount_source else "",
        "printing_total_value": display_amount(amount_source.printing_total) if amount_source else "",
        "vendor_account_totals": vendor_totals,
        "paper_total_paid_display_value": display_amount(paper_paid_base + amount_source.paper_paid_amount) if amount_source else "",
        "paper_balance_value": display_amount(
            (paper_bill_base + amount_source.paper_total_rs) - (paper_paid_base + amount_source.paper_paid_amount)
        ) if amount_source else "",
        "binding_total_paid_display_value": display_amount(binding_paid_base + amount_source.binding_paid_rs) if amount_source else "",
        "binding_balance_value": display_amount(
            (binding_bill_base + amount_source.binding_total_rs) - (binding_paid_base + amount_source.binding_paid_rs)
        ) if amount_source else "",
        "summary_prev_bal_display_value": display_amount(context["summary_prev_bal_value"]),
        "summary_balance_value": display_amount(summary_running["balance"]) if amount_source else "",
        "total_of_this_job_value": display_amount(amount_source.binding_total_of_this_job) if amount_source else "",
        "system_starting_amount_value": display_amount(context["system_value"].starting_amount),
        "first_job": first_job,
        "last_job": last_job,
        "has_previous_job": bool(previous_job),
        "has_next_job": bool(next_job),
    })
    return render(request, "job_entry/home.html", context)


def app_exit(request):
    backup_database()

    def stop_process():
        time.sleep(0.35)
        os._exit(0)

    threading.Thread(target=stop_process, daemon=True).start()
    return JsonResponse({"ok": True})


def option_groups():
    groups = []
    for key, (title, model) in OPTION_MODELS.items():
        groups.append({
            "key": key,
            "title": title,
            "items": model.objects.all(),
        })
    return groups


def options_page(request):
    seed_lookup_data()
    return render(request, "job_entry/options.html", {
        "option_groups": option_groups(),
        "options_changed": request.GET.get("changed") == "1",
    })


def options_data(request):
    seed_lookup_data()
    return JsonResponse({
        "job_style": active_options_payload(JobStyle),
        "paper_vendor": active_options_payload(PaperVendor),
        "binding_vendor": active_options_payload(BindingVendor),
    })


def option_save(request, option_key):
    if request.method != "POST" or option_key not in OPTION_MODELS:
        return redirect("job_entry:options")

    title, model = OPTION_MODELS[option_key]
    option_id = request.POST.get("option_id")
    name = text_post(request, "name")
    is_active = request.POST.get("is_active") == "1"

    if not name:
        messages.error(request, "%s name blank nahi ho sakta." % title)
        return redirect("job_entry:options")

    try:
        if option_id:
            option = get_object_or_404(model, pk=option_id)
            option.name = name
            option.is_active = is_active
            option.save()
            messages.success(request, "%s updated." % title)
        else:
            model.objects.create(name=name, is_active=is_active)
            messages.success(request, "%s added." % title)
    except IntegrityError:
        messages.error(request, "%s already exist karta hai." % name)
    return redirect("%s?changed=1" % redirect("job_entry:options").url)


def option_delete(request, option_key, pk):
    if request.method != "POST" or option_key not in OPTION_MODELS:
        return redirect("job_entry:options")

    title, model = OPTION_MODELS[option_key]
    option = get_object_or_404(model, pk=pk)
    option.delete()
    messages.success(request, "%s deleted." % title)
    return redirect("%s?changed=1" % redirect("job_entry:options").url)


def system_value_save(request):
    if request.method != "POST":
        return redirect("job_entry:home")

    system_value = SystemValue.load()
    system_value.mail_from = text_post(request, "system_mail_from")
    system_value.mail_to = text_post(request, "system_mail_to")
    system_value.mail_cc = text_post(request, "system_mail_cc")
    system_value.starting_amount = decimal_post(request, "system_starting_amount")
    system_value.save()

    if request.POST.get("system_send_email_action"):
        messages.success(request, "System value saved. Email offline mode me send nahi hoga.")
    else:
        messages.success(request, "System value saved successfully.")
    return redirect(request.POST.get("next") or "job_entry:home")


def job_list(request):
    query = (request.GET.get("q") or "").strip()
    jobs = PrintingJobSheet.objects.all()
    if query:
        filters = Q(name__icontains=query)
        if query.isdigit():
            filters |= Q(job_no=int(query))
        try:
            amount = Decimal(query.replace(",", ""))
            filters |= Q(binding_total_of_this_job=amount)
        except InvalidOperation:
            pass
        jobs = jobs.filter(filters)

    context = {
        "jobs": jobs[:200],
        "query": query,
        "total_jobs": jobs.count(),
    }
    return render(request, "job_entry/job_list.html", context)


def job_next(request, pk):
    current_job = get_object_or_404(PrintingJobSheet, pk=pk)
    next_job = PrintingJobSheet.objects.filter(job_no__gt=current_job.job_no).order_by("job_no").first()
    if not next_job:
        messages.error(request, "Next job nahi mila.")
        return redirect("job_entry:job_edit", pk=current_job.pk)
    return redirect("job_entry:job_edit", pk=next_job.pk)


def job_previous(request, pk):
    current_job = get_object_or_404(PrintingJobSheet, pk=pk)
    previous_job = PrintingJobSheet.objects.filter(job_no__lt=current_job.job_no).order_by("-job_no").first()
    if not previous_job:
        messages.error(request, "Previous job nahi mila.")
        return redirect("job_entry:job_edit", pk=current_job.pk)
    return redirect("job_entry:job_edit", pk=previous_job.pk)


def job_first(request):
    first_job = PrintingJobSheet.objects.order_by("job_no").first()
    if not first_job:
        messages.error(request, "First job nahi mila.")
        return redirect("job_entry:home")
    return redirect("job_entry:job_edit", pk=first_job.pk)


def job_last(request):
    last_job = PrintingJobSheet.objects.order_by("-job_no").first()
    if not last_job:
        messages.error(request, "Last job nahi mila.")
        return redirect("job_entry:home")
    return redirect("job_entry:job_edit", pk=last_job.pk)


def build_job_sheet_pdf(job):
    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    teal = colors.HexColor("#0f766e")
    border = colors.HexColor("#0f766e")
    label_color = colors.HexColor("#111827")
    value_color = colors.HexColor("#111827")

    def text_fit(value, max_chars=34):
        value = str(value or "").upper()
        return value if len(value) <= max_chars else value[:max_chars - 3] + "..."

    def field(label, value, x, y, label_w=78, value_w=178, h=25, max_chars=34):
        page.setStrokeColor(border)
        page.setLineWidth(.8)
        page.setFont("Helvetica-Bold", 10)
        page.setFillColor(label_color)
        page.drawString(x, y + 7, label.upper())
        page.roundRect(x + label_w, y, value_w, h, 3, stroke=1, fill=0)
        page.setFont("Helvetica", 10)
        page.setFillColor(value_color)
        page.drawString(x + label_w + 8, y + 7, text_fit(value, max_chars))

    def underline_field(label, value, x, y, label_w=86, line_w=182, max_chars=32):
        page.setStrokeColor(border)
        page.setLineWidth(.8)
        page.setFont("Helvetica-Bold", 10)
        page.setFillColor(label_color)
        page.drawString(x, y + 5, label.upper())
        page.line(x + label_w, y + 3, x + label_w + line_w, y + 3)
        page.setFont("Helvetica", 10)
        page.drawString(x + label_w + 4, y + 7, text_fit(value, max_chars))

    page.setStrokeColor(border)
    page.setLineWidth(1.2)
    page.roundRect(28, 26, width - 56, height - 52, 8, stroke=1, fill=0)
    page.line(48, height - 96, width - 48, height - 96)

    page.setFont("Helvetica-Bold", 22)
    page.setFillColor(teal)
    page.drawCentredString(width / 2, height - 70, "EMAIL Pub.")

    left_x = 58
    right_x = 318
    y = height - 136
    row_gap = 36

    left_fields = [
        ("JOB NO", job.job_no),
        ("DATE", display_date(job.job_date)),
        ("NAME", job.name),
        ("SIZE", job.size),
        ("PAGE", job.page),
        ("COPIES", job.copies),
        ("INK", job.ink),
        ("S/S  F/B", job.ss_fb),
        ("PLATES", pdf_amount(job.printing_plates_qty)),
        ("PTG", pdf_amount(job.printing_ptg_qty)),
        ("LAM/UV", job.printing_lam_uv),
    ]
    for index, (label, value) in enumerate(left_fields):
        field(label, value, left_x, y - (index * row_gap), label_w=82, value_w=150, max_chars=25)

    right_fields = [
        ("QTY", job.paper_qty),
        ("SIZE", job.paper_size),
        ("QUALITY", job.paper_quality),
        ("GSM", job.paper_gsm),
        ("BDG STYLE", job.job_style),
        ("OTHER", job.printing_other_gst),
        ("GST", pdf_amount(job.printing_other_gst_price)),
    ]
    for index, (label, value) in enumerate(right_fields):
        field(label, value, right_x, y - (index * row_gap), label_w=92, value_w=150, max_chars=25)

    system_value = SystemValue.load()
    summary_running = running_summary_balance_until(job, system_value)
    payment_y = y - len(left_fields) * row_gap
    payment_rows = [
        ("PAID RS", pdf_amount(job.printing_paid_rs)),
        ("DATE", display_date(job.printing_paid_date)),
        ("REFERENCE", job.printing_reference),
        ("THRU", job.printing_thru),
        ("PREV BAL", pdf_amount(summary_running["prev"])),
        ("BALANCE", pdf_amount(summary_running["balance"])),
    ]
    for index, (label, value) in enumerate(payment_rows):
        field(label, value, left_x, payment_y - (index * row_gap), label_w=82, value_w=150, max_chars=25)

    page.showPage()
    page.save()
    return buffer.getvalue()


def job_sheet_pdf(request, pk):
    job = get_object_or_404(PrintingJobSheet, pk=pk)
    response = HttpResponse(build_job_sheet_pdf(job), content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="job-%s-sheet.pdf"' % job.job_no
    return response


def job_send_email(request, pk):
    if request.method != "POST":
        return redirect("job_entry:job_edit", pk=pk)

    job = get_object_or_404(PrintingJobSheet, pk=pk)
    system_value = SystemValue.load()
    system_value.mail_from = text_post(request, "system_mail_from")
    system_value.mail_to = text_post(request, "system_mail_to")
    system_value.mail_cc = text_post(request, "system_mail_cc")
    system_value.starting_amount = decimal_post(request, "system_starting_amount")
    system_value.save()

    if not system_value.mail_from or not system_value.mail_to:
        messages.error(request, "MAIL FROM aur MAIL TO fill karein.")
        return redirect("job_entry:job_edit", pk=job.pk)

    to_emails = [email.strip() for email in system_value.mail_to.split(",") if email.strip()]
    cc_emails = [email.strip() for email in system_value.mail_cc.split(",") if email.strip()]
    pdf_bytes = build_job_sheet_pdf(job)
    email = EmailMessage(
        subject="Printing Job Sheet #%s" % job.job_no,
        body="Printing Job Sheet #%s PDF attached hai." % job.job_no,
        from_email=system_value.mail_from,
        to=to_emails,
        cc=cc_emails,
    )
    email.attach("job-%s-sheet.pdf" % job.job_no, pdf_bytes, "application/pdf")
    try:
        email.send(fail_silently=False)
    except Exception as exc:
        messages.error(request, "Email send nahi hua: %s" % exc)
    else:
        messages.success(request, "Job sheet PDF email successfully send ho gaya.")
    return redirect("job_entry:job_edit", pk=job.pk)


def report_jobs_and_section(request):
    query = (request.GET.get("q") or "").strip()
    section = (request.GET.get("section") or "paper").strip().lower()
    vendor = text_post(request, "vendor")
    date_start = date_filter_value(request.GET.get("date_start"))
    date_end = date_filter_value(request.GET.get("date_end"))
    job_no_start = optional_int_value(request.GET.get("job_no_start"))
    job_no_end = optional_int_value(request.GET.get("job_no_end"))
    if section not in ("paper", "printing", "binding"):
        section = "paper"
    jobs = PrintingJobSheet.objects.all()
    if query:
        filters = Q(name__icontains=query)
        if query.isdigit():
            filters |= Q(job_no=int(query))
        try:
            amount = Decimal(query.replace(",", ""))
            filters |= Q(binding_total_of_this_job=amount)
        except InvalidOperation:
            pass
        jobs = jobs.filter(filters)
    if date_start:
        jobs = jobs.filter(job_date__gte=date_start)
    if date_end:
        jobs = jobs.filter(job_date__lte=date_end)
    if job_no_start is not None:
        jobs = jobs.filter(job_no__gte=job_no_start)
    if job_no_end is not None:
        jobs = jobs.filter(job_no__lte=job_no_end)
    if vendor and section == "paper":
        jobs = jobs.filter(paper_vendor=vendor)
    elif vendor and section == "binding":
        jobs = jobs.filter(binding_vendor=vendor)
    return jobs, {
        "query": query,
        "section": section,
        "vendor": vendor,
        "date_start": display_date(date_start) if date_start else "",
        "date_end": display_date(date_end) if date_end else "",
        "job_no_start": str(job_no_start) if job_no_start is not None else "",
        "job_no_end": str(job_no_end) if job_no_end is not None else "",
    }


def report_rows_for_jobs(jobs, section):
    rows = []
    total_amount = Decimal("0")
    total_paid = Decimal("0")
    total_balance = Decimal("0")
    system_value = SystemValue.load()
    for job in jobs:
        if section == "printing":
            running = running_summary_balance_until(job, system_value)
            total_rs = job.printing_total
            paid_rs = job.printing_paid_rs
            balance = running["balance"]
        elif section == "binding":
            vendor_totals = vendor_account_totals(job)
            bill_base = vendor_total_decimal(vendor_totals, "binding", job.binding_vendor, "bill")
            paid_base = vendor_total_decimal(vendor_totals, "binding", job.binding_vendor, "paid")
            total_rs = job.binding_total_rs
            paid_rs = paid_base + job.binding_paid_rs
            balance = (bill_base + job.binding_total_rs) - paid_rs
        else:
            vendor_totals = vendor_account_totals(job)
            bill_base = vendor_total_decimal(vendor_totals, "paper", job.paper_vendor, "bill")
            paid_base = vendor_total_decimal(vendor_totals, "paper", job.paper_vendor, "paid")
            total_rs = job.paper_total_rs
            paid_rs = paid_base + job.paper_paid_amount
            balance = (bill_base + job.paper_total_rs) - paid_rs

        total_amount += total_rs
        total_paid += paid_rs
        total_balance += balance
        rows.append({
            "job_no": job.job_no,
            "date": display_date(job.job_date),
            "total_rs": pdf_amount(total_rs),
            "paid_rs": pdf_amount(paid_rs),
            "balance": pdf_amount(balance),
        })
    return rows, {
        "total_rs": pdf_amount(total_amount),
        "paid_rs": pdf_amount(total_paid),
        "balance": pdf_amount(total_balance),
    }


def job_report(request):
    jobs, filters = report_jobs_and_section(request)
    section = filters["section"]
    rows, totals = report_rows_for_jobs(jobs, section)
    report_titles = {
        "paper": "Paper Report",
        "printing": "Printing Report",
        "binding": "Binding Report",
    }
    return render(request, "job_entry/report.html", {
        "rows": rows,
        "totals": totals,
        "filters": filters,
        "query": filters["query"],
        "section": section,
        "report_title": report_titles[section],
        "total_jobs": len(rows),
        "paper_vendor_options": active_options(PaperVendor),
        "binding_vendor_options": active_options(BindingVendor),
    })


def job_report_pdf(request):
    query_string = request.META.get("QUERY_STRING", "")
    target = reverse("job_entry:job_report")
    return redirect("%s?%s" % (target, query_string) if query_string else target)


def job_report_pdf_download(request):
    jobs, filters = report_jobs_and_section(request)
    section = filters["section"]
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="printing-job-report.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )
    styles = getSampleStyleSheet()
    report_titles = {
        "paper": "PAPER REPORT",
        "printing": "PRINTING REPORT",
        "binding": "BINDING REPORT",
    }
    story = [
        Paragraph(report_titles[section], styles["Title"]),
        Paragraph("Search: %s" % (filters["query"] or "All Jobs"), styles["Normal"]),
        Spacer(1, 10),
    ]

    rows = [["Job No", "Date", "Total Rs", "Paid Rs", "Balance"]]
    report_rows, totals = report_rows_for_jobs(jobs[:500], section)
    for row in report_rows:
        rows.append([
            str(row["job_no"]),
            row["date"],
            row["total_rs"],
            row["paid_rs"],
            row["balance"],
        ])
    rows.append(["", "TOTAL", totals["total_rs"], totals["paid_rs"], totals["balance"]])

    table = Table(rows, repeatRows=1, colWidths=[58, 78, 132, 132, 132])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4f8f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b9c6d8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(table)
    doc.build(story)
    return response
