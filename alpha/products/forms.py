from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Category, Product, VisitProduct


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": _("e.g. Skincare")}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "description",
            "category",
            "price",
            "stock",
            "low_stock_threshold",
            "image",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "low_stock_threshold": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].empty_label = _("— No Category —")
        self.fields["category"].queryset = Category.objects.all()


class StockAdjustmentForm(forms.Form):
    """Quick form to add or remove stock units"""

    ADJUSTMENT_CHOICES = [
        ("add", _("Add stock (restock)")),
        ("remove", _("Remove stock (usage / correction)")),
    ]

    direction = forms.ChoiceField(
        choices=ADJUSTMENT_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        label=_("Adjustment Type"),
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
        label=_("Quantity"),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": _("Optional reason")}),
        label=_("Notes"),
    )


class VisitProductForm(forms.ModelForm):
    """Inline form for adding products to a visit"""

    class Meta:
        model = VisitProduct
        fields = ["product", "quantity", "price_at_time", "notes"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "price_at_time": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_active=True, stock__gt=0)
        self.fields["price_at_time"].required = False
        self.fields["price_at_time"].help_text = _("Leave blank to use current product price")