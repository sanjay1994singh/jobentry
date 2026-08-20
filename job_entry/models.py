from django.db import models
from django.db.models import Sum
from django.utils import timezone


class PaperVendor(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Paper vendors"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BindingVendor(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Binding outsource vendors"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PrintingThrough(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Printing through options"
        ordering = ["name"]

    def __str__(self):
        return self.name


class PaperThrough(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Paper through options"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BindingThrough(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Binding through options"
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobStyle(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Job styles"
        ordering = ["name"]

    def __str__(self):
        return self.name


class SystemValue(models.Model):
    mail_from = models.EmailField(max_length=254, blank=True)
    mail_to = models.EmailField(max_length=254, blank=True)
    mail_cc = models.EmailField(max_length=254, blank=True)
    smtp_host = models.CharField(max_length=150, blank=True, default="smtp.gmail.com")
    smtp_port = models.PositiveIntegerField(default=587)
    smtp_username = models.CharField(max_length=254, blank=True)
    smtp_password = models.CharField(max_length=254, blank=True)
    smtp_use_tls = models.BooleanField(default=True)
    starting_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System value"
        verbose_name_plural = "System values"

    def __str__(self):
        return "System Value"

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class PrintingJobSheet(models.Model):
    STARTING_JOB_NO = 5701

    job_no = models.PositiveIntegerField(unique=True, editable=False)
    job_date = models.DateField(default=timezone.localdate)
    name = models.CharField(max_length=150, blank=True)
    size = models.CharField(max_length=100, blank=True)
    page = models.CharField(max_length=50, blank=True)
    copies = models.CharField(max_length=50, blank=True)
    ink = models.CharField(max_length=100, blank=True)
    ss_fb = models.CharField(max_length=50, blank=True)
    binder = models.CharField(max_length=100, blank=True)
    job_style_id_snapshot = models.PositiveIntegerField(null=True, blank=True)
    job_style = models.CharField(max_length=100, blank=True)

    printing_plates_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_plates_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_plates_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_ptg_qty = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_ptg_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_ptg_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_lam_uv = models.TextField(blank=True)
    printing_lam_uv_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_bdg = models.CharField(max_length=150, blank=True)
    printing_bdg_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_other_gst = models.TextField(blank=True)
    printing_other_gst_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_paper_details = models.TextField(blank=True)
    printing_paper_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_paid_rs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    printing_paid_date = models.DateField(default=timezone.localdate)
    printing_reference = models.TextField(blank=True)
    printing_thru_id_snapshot = models.PositiveIntegerField(null=True, blank=True)
    printing_thru = models.CharField(max_length=50, blank=True)

    paper_qty = models.TextField(blank=True)
    paper_size = models.TextField(blank=True)
    paper_quality = models.TextField(blank=True)
    paper_gsm = models.TextField(blank=True)
    paper_total_rs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paper_discount_2 = models.CharField(max_length=150, blank=True)
    paper_paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paper_paid_date = models.DateField(default=timezone.localdate)
    paper_reference = models.TextField(blank=True)
    paper_vendor_id_snapshot = models.PositiveIntegerField(null=True, blank=True)
    paper_vendor = models.CharField(max_length=150, blank=True)
    paper_thru_id_snapshot = models.PositiveIntegerField(null=True, blank=True)
    paper_thru = models.CharField(max_length=50, blank=True)
    paper_total_paid_display = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    paper_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    binding_qty = models.TextField(blank=True)
    binding_rate_rate = models.TextField(blank=True)
    binding_total_rs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    binding_discount = models.CharField(max_length=150, blank=True)
    binding_paid_rs = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    binding_paid_date = models.DateField(default=timezone.localdate)
    binding_reference = models.TextField(blank=True)
    binding_vendor_id_snapshot = models.PositiveIntegerField(null=True, blank=True)
    binding_vendor = models.CharField(max_length=150, blank=True)
    binding_thru_id_snapshot = models.PositiveIntegerField(null=True, blank=True)
    binding_thru = models.CharField(max_length=50, blank=True)
    binding_total_paid_display = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    binding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    summary_prev_bal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    summary_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    binding_total_of_this_job = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-job_no"]

    def __str__(self):
        return "Job #%s - %s" % (self.job_no, self.name)

    @classmethod
    def next_job_no(cls):
        last_job = cls.objects.order_by("-job_no").first()
        if not last_job:
            return cls.STARTING_JOB_NO
        return last_job.job_no + 1

    def save(self, *args, **kwargs):
        if not self.job_no:
            self.job_no = self.next_job_no()
        self.printing_plates_total = self.printing_plates_qty * self.printing_plates_price
        self.printing_ptg_total = self.printing_ptg_qty * self.printing_ptg_price
        self.printing_total = (
            self.printing_plates_total
            + self.printing_ptg_total
            + self.printing_lam_uv_price
            + self.printing_bdg_price
            + self.printing_other_gst_price
            + self.printing_paper_amount
        )
        previous_jobs = self.__class__.objects.filter(job_no__lt=self.job_no)
        paper_vendor_jobs = previous_jobs.filter(paper_vendor=self.paper_vendor) if self.paper_vendor else previous_jobs.none()
        binding_vendor_jobs = (
            previous_jobs.filter(binding_vendor=self.binding_vendor) if self.binding_vendor else previous_jobs.none()
        )
        previous_paper_bill = paper_vendor_jobs.aggregate(total=Sum("paper_total_rs"))["total"] or 0
        previous_paper_paid = paper_vendor_jobs.aggregate(total=Sum("paper_paid_amount"))["total"] or 0
        previous_binding_bill = binding_vendor_jobs.aggregate(total=Sum("binding_total_rs"))["total"] or 0
        previous_binding_paid = binding_vendor_jobs.aggregate(total=Sum("binding_paid_rs"))["total"] or 0
        self.paper_total_paid_display = previous_paper_paid + self.paper_paid_amount
        self.paper_balance = (previous_paper_bill + self.paper_total_rs) - self.paper_total_paid_display
        self.binding_total_paid_display = previous_binding_paid + self.binding_paid_rs
        self.binding_balance = (previous_binding_bill + self.binding_total_rs) - self.binding_total_paid_display
        self.summary_balance = self.summary_prev_bal + self.printing_total - self.printing_paid_rs
        self.binding_total_of_this_job = self.printing_total + self.paper_total_rs + self.binding_total_rs
        super().save(*args, **kwargs)
