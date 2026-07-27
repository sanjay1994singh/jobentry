from django import forms

from .models import JobEntry


class JobEntryForm(forms.ModelForm):
    class Meta:
        model = JobEntry
        fields = [
            "job_no",
            "job_date",
            "copies",
            "ink",
            "customer_name",
            "binding_type",
            "item_name",
            "item_size",
            "page",
            "page_amount",
            "page_total_amount",
            "plates",
            "plates_amount",
            "plates_total_amount",
            "qty",
            "qty_amount",
            "qty_total_amount",
            "other_name",
            "other_amount",
            "sheets",
            "paper_size",
            "quality",
            "gsm",
            "vendor",
            "paper_amount",
            "lamination",
            "other_paper",
            "grand_total_amount",
            "paid_amount",
            "received_by",
            "paid_date",
            "through",
        ]
