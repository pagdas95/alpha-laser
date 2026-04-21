from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Category, Product, VisitProduct


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "product_count"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = _("Products")


class VisitProductInline(admin.TabularInline):
    model = VisitProduct
    extra = 0
    readonly_fields = ["price_at_time", "line_total"]
    fields = ["product", "quantity", "price_at_time", "sold_by", "notes", "line_total"]

    def line_total(self, obj):
        return f"€{float(obj.line_total):.2f}" if obj.pk else "—"
    line_total.short_description = _("Line Total")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "price_display",
        "stock_display",
        "is_active",
        "thumbnail",
    ]
    list_filter = ["is_active", "category"]
    search_fields = ["name", "description"]
    list_editable = ["is_active"]
    readonly_fields = ["created_at", "updated_at", "thumbnail"]
    inlines = [VisitProductInline]

    fieldsets = (
        (None, {
            "fields": ("name", "description", "category", "is_active"),
        }),
        (_("Pricing & Stock"), {
            "fields": ("price", "stock", "low_stock_threshold"),
        }),
        (_("Image"), {
            "fields": ("image", "thumbnail"),
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def price_display(self, obj):
        return f"€{float(obj.price):.2f}"
    price_display.short_description = _("Price")
    price_display.admin_order_field = "price"

    def stock_display(self, obj):
        if obj.stock == 0:
            color = "red"
            label = _("Out of stock")
        elif obj.is_low_stock:
            color = "orange"
            label = f"{obj.stock} ⚠️"
        else:
            color = "green"
            label = str(obj.stock)
        return format_html('<span style="color: {};">{}</span>', color, label)
    stock_display.short_description = _("Stock")
    stock_display.admin_order_field = "stock"

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="height: 60px; border-radius: 4px;" />',
                obj.image.url
            )
        return "—"
    thumbnail.short_description = _("Preview")


@admin.register(VisitProduct)
class VisitProductAdmin(admin.ModelAdmin):
    list_display = [
        "product",
        "client_display",
        "visit_date_display",
        "quantity",
        "price_at_time",
        "line_total_display",
        "sold_by_display",
        "discount_display",
    ]
    list_filter = [
        "product__category",
        "sold_by",
        "visit__appointment__service",
        "created_at",
    ]
    search_fields = [
        "product__name",
        "visit__appointment__client__full_name",
        "sold_by__username",
        "notes",
    ]
    readonly_fields = [
        "price_at_time",
        "client_display",
        "visit_date_display",
        "original_price_display",
        "line_total_display",
        "discount_display",
        "created_at",
    ]
    date_hierarchy = "created_at"

    fieldsets = (
        (_("Sale"), {
            "fields": ("visit", "product", "quantity", "sold_by", "notes"),
        }),
        (_("Pricing"), {
            "fields": (
                "original_price_display",
                "price_at_time",
                "line_total_display",
                "discount_display",
            ),
        }),
        (_("Context"), {
            "fields": ("client_display", "visit_date_display", "created_at"),
            "classes": ("collapse",),
        }),
    )

    # ── List display helpers ───────────────────────────────────────────

    def client_display(self, obj):
        try:
            client = obj.visit.appointment.client
            return format_html(
                '<a href="/admin/clients/client/{}/change/">{}</a>',
                client.pk, client.full_name
            )
        except Exception:
            return "—"
    client_display.short_description = _("Client")

    def visit_date_display(self, obj):
        try:
            return obj.visit.appointment.start.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return "—"
    visit_date_display.short_description = _("Visit Date")
    visit_date_display.admin_order_field = "visit__appointment__start"

    def sold_by_display(self, obj):
        if obj.sold_by:
            name = getattr(obj.sold_by, 'name', None) or obj.sold_by.username
            return name
        return format_html('<span style="color: #aaa;">—</span>')
    sold_by_display.short_description = _("Sold By")
    sold_by_display.admin_order_field = "sold_by"

    def line_total_display(self, obj):
        if obj.pk:
            return format_html(
                "<strong>€{}</strong>",
                f"{float(obj.line_total):.2f}"
            )
        return "—"
    line_total_display.short_description = _("Line Total")

    def original_price_display(self, obj):
        if obj.pk:
            return f"€{float(obj.product.price):.2f}"
        return "—"
    original_price_display.short_description = _("Catalogue Price")

    def discount_display(self, obj):
        if not obj.pk:
            return "—"
        diff = obj.product.price - obj.price_at_time
        if diff > 0:
            pct = (diff / obj.product.price) * 100
            return format_html(
                '<span style="color: orange;">-€{} ({}%)</span>',
                f"{float(diff):.2f}",
                f"{pct:.0f}",
            )
        return format_html('<span style="color: green;">—</span>')
    discount_display.short_description = _("Discount")