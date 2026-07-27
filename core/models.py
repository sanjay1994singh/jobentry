from django.db import models


class BindingType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Vendor(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PaymentThrough(models.Model):
    name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Payment through options"
        ordering = ["name"]

    def __str__(self):
        return self.name


class JobEntry(models.Model):
    job_no = models.CharField(max_length=50, unique=True)
    job_date = models.CharField(max_length=20)
    copies = models.CharField(max_length=50)
    ink = models.CharField(max_length=100)
    customer_name = models.CharField(max_length=100)
    binding_type = models.CharField(max_length=100)

    item_name = models.CharField(max_length=150)
    item_size = models.CharField(max_length=100)
    page = models.DecimalField(max_digits=12, decimal_places=2)
    page_amount = models.DecimalField(max_digits=12, decimal_places=2)
    page_total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    plates = models.DecimalField(max_digits=12, decimal_places=2)
    plates_amount = models.DecimalField(max_digits=12, decimal_places=2)
    plates_total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    qty_amount = models.DecimalField(max_digits=12, decimal_places=2)
    qty_total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    other_name = models.CharField(max_length=150)
    other_amount = models.DecimalField(max_digits=12, decimal_places=2)

    sheets = models.CharField(max_length=100)
    paper_size = models.CharField(max_length=100)
    quality = models.CharField(max_length=100)
    gsm = models.CharField(max_length=100)
    vendor = models.CharField(max_length=150)
    paper_amount = models.DecimalField(max_digits=12, decimal_places=2)
    lamination = models.DecimalField(max_digits=12, decimal_places=2)
    other_paper = models.DecimalField(max_digits=12, decimal_places=2)

    grand_total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2)
    received_by = models.CharField(max_length=100)
    paid_date = models.CharField(max_length=20)
    through = models.CharField(max_length=50)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return "%s - %s" % (self.job_no, self.item_name)

    @classmethod
    def next_job_no(cls):
        last_job = cls.objects.order_by("-id").first()
        next_number = 1
        if last_job and last_job.job_no:
            digits = "".join(ch for ch in last_job.job_no if ch.isdigit())
            if digits:
                next_number = int(digits) + 1
            else:
                next_number = last_job.id + 1
        return "JOB-%05d" % next_number

    def save(self, *args, **kwargs):
        if not self.job_no:
            self.job_no = self.next_job_no()
        super().save(*args, **kwargs)
