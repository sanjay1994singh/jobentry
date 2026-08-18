from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import IntegrityError
from django.db import OperationalError, ProgrammingError
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

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
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def text_post(request, name):
    return (request.POST.get(name) or "").strip().upper()


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
    for date_format in ("%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            pass
    return timezone.localdate()


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


def vendor_account_totals(current_job=None):
    jobs = PrintingJobSheet.objects.all()
    if current_job:
        jobs = jobs.exclude(pk=current_job.pk)
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


def next_prev_balance(system_value):
    latest_job = PrintingJobSheet.objects.order_by("-job_no").first()
    if latest_job:
        return latest_job.summary_balance
    return system_value.starting_amount


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
        job = current_job or PrintingJobSheet()
        assign_printing_job_sheet(job, request)
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
    context["summary_prev_bal_value"] = (
        current_job.summary_prev_bal if current_job else next_prev_balance(context["system_value"])
    )
    amount_source = current_job
    vendor_totals = vendor_account_totals(current_job)
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
        "paper_total_paid_display_value": display_amount(amount_source.paper_total_paid_display) if amount_source else "",
        "paper_balance_value": display_amount(amount_source.paper_balance) if amount_source else "",
        "binding_total_paid_display_value": display_amount(amount_source.binding_total_paid_display) if amount_source else "",
        "binding_balance_value": display_amount(amount_source.binding_balance) if amount_source else "",
        "summary_prev_bal_display_value": display_amount(context["summary_prev_bal_value"]),
        "summary_balance_value": display_amount(amount_source.summary_balance) if amount_source else "",
        "total_of_this_job_value": display_amount(amount_source.binding_total_of_this_job) if amount_source else "",
        "system_starting_amount_value": display_amount(context["system_value"].starting_amount),
        "first_job": first_job,
        "last_job": last_job,
        "has_previous_job": bool(previous_job),
        "has_next_job": bool(next_job),
    })
    return render(request, "job_entry/home.html", context)


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


def job_report_pdf(request):
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

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="printing-job-report.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("PRINTING JOB REPORT", styles["Title"]),
        Paragraph("Search: %s" % (query or "All Jobs"), styles["Normal"]),
        Spacer(1, 10),
    ]

    rows = [["Job No", "Date", "Name", "Size", "Copies", "Printing", "Paper", "Binding", "Total Job"]]
    for job in jobs[:500]:
        rows.append([
            str(job.job_no),
            display_date(job.job_date),
            job.name or "",
            job.size or "",
            str(job.copies),
            str(job.printing_total),
            str(job.paper_total_rs),
            str(job.binding_total_rs),
            str(job.binding_total_of_this_job),
        ])

    table = Table(rows, repeatRows=1, colWidths=[45, 70, 160, 80, 55, 75, 75, 75, 85])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4f8f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b9c6d8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fb")]),
        ("ALIGN", (0, 0), (1, -1), "CENTER"),
        ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(table)
    doc.build(story)
    return response
