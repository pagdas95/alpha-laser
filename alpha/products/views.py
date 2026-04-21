from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Q, Sum, F
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView
from django.http import JsonResponse

from .forms import CategoryForm, ProductForm, StockAdjustmentForm
from .models import Category, Product


# ─────────────────────────────────────────────
# PRODUCT VIEWS
# ─────────────────────────────────────────────

class ProductListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Product
    template_name = "products/product_list.html"
    context_object_name = "products"
    paginate_by = 25
    permission_required = "products.view_product"

    def get_queryset(self):
        queryset = Product.objects.select_related("category")

        search = self.request.GET.get("search", "")
        category = self.request.GET.get("category", "")
        status = self.request.GET.get("status", "")

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )
        if category:
            queryset = queryset.filter(category__slug=category)
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)
        elif status == "low_stock":
            queryset = queryset.filter(
                is_active=True,
                stock__gt=0,
                stock__lte=F("low_stock_threshold"),
            )
        elif status == "out_of_stock":
            queryset = queryset.filter(stock=0)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_products = Product.objects.all()
        context["categories"] = Category.objects.all()
        context["total_count"] = all_products.count()
        context["active_count"] = all_products.filter(is_active=True).count()
        context["low_stock_count"] = all_products.filter(
            is_active=True, stock__gt=0, stock__lte=F("low_stock_threshold")
        ).count()
        context["out_of_stock_count"] = all_products.filter(stock=0).count()
        return context


class ProductDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Product
    template_name = "products/product_detail.html"
    context_object_name = "product"
    permission_required = "products.view_product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["stock_form"] = StockAdjustmentForm()
        return context


@login_required
@permission_required("products.add_product", raise_exception=True)
def product_create_view(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, _(f'Product "{product.name}" created successfully!'))
            return redirect("products:detail", pk=product.pk)
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
    else:
        form = ProductForm()

    return render(request, "products/product_form.html", {
        "form": form,
        "title": _("Add Product"),
        "submit_text": _("Create Product"),
    })


@login_required
@permission_required("products.change_product", raise_exception=True)
def product_edit_view(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, _(f'Product "{product.name}" updated successfully!'))
            return redirect("products:detail", pk=product.pk)
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)
    else:
        form = ProductForm(instance=product)

    return render(request, "products/product_form.html", {
        "form": form,
        "product": product,
        "title": _(f"Edit: {product.name}"),
        "submit_text": _("Save Changes"),
    })


@login_required
@permission_required("products.delete_product", raise_exception=True)
def product_delete_view(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        name = product.name
        product.delete()
        messages.success(request, _(f'Product "{name}" deleted successfully.'))
        return redirect("products:list")

    return render(request, "products/product_confirm_delete.html", {"product": product})


@login_required
@permission_required("products.change_product", raise_exception=True)
def product_adjust_stock_view(request, pk):
    """Handle stock adjustment from product detail page"""
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            direction = form.cleaned_data["direction"]
            quantity = form.cleaned_data["quantity"]
            signed_qty = quantity if direction == "add" else -quantity

            try:
                product.adjust_stock(signed_qty)
                action = _("Added") if direction == "add" else _("Removed")
                messages.success(request, _(f"{action} {quantity} units for '{product.name}'. New stock: {product.stock}"))
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, _("Invalid stock adjustment."))

    return redirect("products:detail", pk=pk)


# ─────────────────────────────────────────────
# CATEGORY VIEWS
# ─────────────────────────────────────────────

@login_required
@permission_required("products.view_category", raise_exception=True)
def category_list_view(request):
    categories = Category.objects.all()
    return render(request, "products/category_list.html", {"categories": categories})


@login_required
@permission_required("products.add_category", raise_exception=True)
def category_create_view(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, _(f'Category "{category.name}" created!'))
            return redirect("products:categories")
    else:
        form = CategoryForm()

    return render(request, "products/category_form.html", {
        "form": form,
        "title": _("Add Category"),
        "submit_text": _("Create Category"),
    })


@login_required
@permission_required("products.change_category", raise_exception=True)
def category_edit_view(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, _(f'Category "{category.name}" updated!'))
            return redirect("products:categories")
    else:
        form = CategoryForm(instance=category)

    return render(request, "products/category_form.html", {
        "form": form,
        "category": category,
        "title": _(f"Edit: {category.name}"),
        "submit_text": _("Save Changes"),
    })


@login_required
@permission_required("products.delete_category", raise_exception=True)
def category_delete_view(request, pk):
    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        name = category.name
        category.delete()
        messages.success(request, _(f'Category "{name}" deleted.'))
        return redirect("products:categories")

    return render(request, "products/category_confirm_delete.html", {"category": category})


# ─────────────────────────────────────────────
# AJAX / API
# ─────────────────────────────────────────────

@login_required
def product_get_api(request, pk):
    """Return product data as JSON — used when adding a product to a visit"""
    product = get_object_or_404(Product, pk=pk, is_active=True)
    return JsonResponse({
        "id": product.id,
        "name": product.name,
        "price": str(product.price),
        "stock": product.stock,
        "is_in_stock": product.is_in_stock,
        "is_low_stock": product.is_low_stock,
        "category": product.category.name if product.category else None,
    })