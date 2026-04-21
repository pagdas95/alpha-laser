from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify


class Category(models.Model):
    """Product category (e.g. Skincare, Tools, Retail)"""

    name = models.CharField(_("Name"), max_length=100, unique=True)
    slug = models.SlugField(_("Slug"), max_length=120, unique=True, blank=True)
    description = models.TextField(_("Description"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """A product that can be sold or used during a visit"""

    name = models.CharField(_("Name"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("Category"),
    )
    price = models.DecimalField(
        _("Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    stock = models.PositiveIntegerField(
        _("Stock"),
        default=0,
        help_text=_("Current units in stock"),
    )
    low_stock_threshold = models.PositiveIntegerField(
        _("Low Stock Alert Threshold"),
        default=5,
        help_text=_("You will be warned when stock falls to or below this number"),
    )
    image = models.ImageField(
        _("Image"),
        upload_to="products/images/",
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        help_text=_("Inactive products are hidden from selection lists"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_in_stock(self):
        return self.stock > 0

    @property
    def is_low_stock(self):
        return 0 < self.stock <= self.low_stock_threshold

    def adjust_stock(self, quantity: int):
        """
        Adjust stock by a signed integer.
        Positive = restock, Negative = usage/sale.
        Raises ValueError if it would go below zero.
        """
        new_stock = self.stock + quantity
        if new_stock < 0:
            raise ValueError(
                f"Not enough stock for '{self.name}'. "
                f"Available: {self.stock}, requested: {abs(quantity)}"
            )
        self.stock = new_stock
        self.save(update_fields=["stock", "updated_at"])


class VisitProduct(models.Model):
    """
    Links a product purchased/used during a visit.
    Stores quantity and price snapshot at the time of the visit.
    Stock is decremented when added and restored when removed.
    """

    visit = models.ForeignKey(
        "visits.Visit",
        on_delete=models.CASCADE,
        related_name="visit_products",
        verbose_name=_("Visit"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,  # Never silently delete a product used in a visit
        related_name="visit_products",
        verbose_name=_("Product"),
    )
    quantity = models.PositiveIntegerField(
        _("Quantity"),
        default=1,
        validators=[MinValueValidator(1)],
    )
    price_at_time = models.DecimalField(
        _("Price at Time of Visit"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Snapshot of product price — unaffected by future price changes"),
    )
    notes = models.CharField(_("Notes"), max_length=255, blank=True)
    sold_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products_sold",
        verbose_name=_("Sold By"),
        help_text=_("Staff member who sold this product — defaults to the visit's staff"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Visit Product")
        verbose_name_plural = _("Visit Products")

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"

    @property
    def line_total(self):
        return self.price_at_time * self.quantity

    def save(self, *args, **kwargs):
        if not self.price_at_time:
            self.price_at_time = self.product.price
        super().save(*args, **kwargs)