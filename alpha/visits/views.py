"""
Visits Views - UPDATED with notification count endpoint
Place this at: alpha/visits/views.py
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Sum, F, OuterRef, Subquery, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.contrib import messages
from django.utils.translation import gettext as _
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from .models import Visit, annotate_totals, recent_incomplete_visits

# Kept as an alias for existing callers
_annotate_grand_total = annotate_totals


class VisitListView(LoginRequiredMixin, ListView):
    """Display all visits with filtering and search"""
    model = Visit
    template_name = 'visits/visit_list.html'
    context_object_name = 'visits'
    

    def get_queryset(self):
        queryset = _annotate_grand_total(
            Visit.objects.select_related(
                'appointment', 'appointment__client',
                'appointment__service', 'staff', 'machine',
                'client_package_item',
            )
        )

        staff_id = self.request.GET.get('staff')
        if staff_id:
            queryset = queryset.filter(staff_id=staff_id)

        machine_id = self.request.GET.get('machine')
        if machine_id:
            queryset = queryset.filter(machine_id=machine_id)

        # Payment filter now compares paid_amount against grand_total_db
        payment_status = self.request.GET.get('payment_status')
        if payment_status == 'paid':
            queryset = queryset.filter(paid_amount__gte=F('grand_total_db'))
        elif payment_status == 'partial':
            queryset = queryset.filter(
                paid_amount__gt=0,
                paid_amount__lt=F('grand_total_db'),
            )
        elif payment_status == 'unpaid':
            queryset = queryset.filter(paid_amount=0)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(appointment__client__full_name__icontains=search) |
                Q(appointment__service__name__icontains=search) |
                Q(area__icontains=search) |
                Q(remarks__icontains=search)
            )

        return queryset.order_by('-appointment__start')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Use annotated queryset for accurate revenue stats
        stats_qs = _annotate_grand_total(Visit.objects.all())
        revenue = stats_qs.aggregate(
            total_grand=Sum('grand_total_db'),
            total_paid=Sum('paid_amount'),
        )

        context['total_count'] = Visit.objects.count()
        context['unpaid_count'] = Visit.objects.filter(paid_amount=0).count()
        context['total_revenue'] = revenue['total_paid'] or 0
        context['pending_revenue'] = (revenue['total_grand'] or 0) - (revenue['total_paid'] or 0)

        context['current_staff'] = self.request.GET.get('staff', '')
        context['current_machine'] = self.request.GET.get('machine', '')
        context['current_payment_status'] = self.request.GET.get('payment_status', '')
        context['current_search'] = self.request.GET.get('search', '')

        return context


class VisitDetailView(LoginRequiredMixin, DetailView):
    """View visit details with full treatment record"""
    model = Visit
    template_name = 'visits/visit_detail.html'
    context_object_name = 'visit'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Products on this visit
        visit_products = self.object.visit_products.select_related('product', 'product__category')
        context['visit_products'] = visit_products
        context['products_total'] = self.object.products_total
        context['grand_total'] = self.object.grand_total
        context['balance'] = self.object.grand_total - self.object.paid_amount
        context['is_paid'] = context['balance'] <= 0

        # Available products for the add-product dropdown (in stock only)
        from alpha.products.models import Product
        context['available_products'] = Product.objects.filter(
            is_active=True, stock__gt=0
        ).select_related('category').order_by('name')
        
        # Get client's visit history
        if self.object.appointment.client:
            context['client_visit_count'] = Visit.objects.filter(
                appointment__client=self.object.appointment.client
            ).count()
        
        return context


class VisitUpdateView(LoginRequiredMixin, UpdateView):
    """Edit visit information - treatment parameters, payment, and products"""
    model = Visit
    template_name = 'visits/visit_form.html'
    fields = [
        'area', 'spot_size_mm', 'fluence_j_cm2', 'pulse_count',
        'charge_amount', 'paid_amount', 'payment_method',
        'remarks'
    ]

    def get_success_url(self):
        messages.success(self.request, _('Visit updated successfully!'))
        return reverse_lazy('visits:detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from alpha.products.models import Product, VisitProduct
        from django.contrib.auth import get_user_model
        User = get_user_model()

        context['visit_products'] = self.object.visit_products.select_related(
            'product', 'product__category', 'sold_by'
        )
        context['available_products'] = Product.objects.filter(
            is_active=True
        ).select_related('category').order_by('name')
        context['products_total'] = self.object.products_total
        context['grand_total'] = self.object.grand_total
        context['balance'] = self.object.grand_total - self.object.paid_amount
        context['staff_list'] = User.objects.filter(is_active=True).order_by('username')
        return context

    def form_valid(self, form):
        from alpha.products.models import Product, VisitProduct
        from django.contrib.auth import get_user_model
        from django.db import transaction
        User = get_user_model()

        with transaction.atomic():
            self.object = form.save()

            # ── Handle deletions ──────────────────────────────────────────
            delete_ids = self.request.POST.getlist('delete_visit_product')
            if delete_ids:
                to_delete = VisitProduct.objects.filter(
                    pk__in=delete_ids, visit=self.object
                ).select_related('product')
                for vp in to_delete:
                    vp.product.adjust_stock(vp.quantity)
                    vp.delete()

            # ── Handle price + sold_by edits on existing products ─────────
            for vp in VisitProduct.objects.filter(visit=self.object):
                updated_fields = []

                new_price_str = self.request.POST.get(f'existing_price_{vp.pk}')
                if new_price_str is not None:
                    try:
                        new_price = max(0, float(new_price_str))
                        if new_price != float(vp.price_at_time):
                            vp.price_at_time = new_price
                            updated_fields.append('price_at_time')
                    except (ValueError, TypeError):
                        pass

                sold_by_id = self.request.POST.get(f'existing_sold_by_{vp.pk}')
                if sold_by_id:
                    try:
                        vp.sold_by_id = int(sold_by_id)
                        updated_fields.append('sold_by_id')
                    except (ValueError, TypeError):
                        pass

                if updated_fields:
                    vp.save(update_fields=updated_fields)

            # ── Handle new products ───────────────────────────────────────
            new_product_ids = self.request.POST.getlist('new_product_id')
            new_quantities  = self.request.POST.getlist('new_quantity')
            new_prices      = self.request.POST.getlist('new_price')
            new_sold_bys    = self.request.POST.getlist('new_sold_by')
            new_notes       = self.request.POST.getlist('new_notes')

            for product_id, qty_str, price_str, sold_by_id, note in zip(
                new_product_ids, new_quantities, new_prices, new_sold_bys, new_notes
            ):
                if not product_id:
                    continue
                qty = max(1, int(qty_str or 1))
                try:
                    product = Product.objects.get(pk=product_id, is_active=True)
                except Product.DoesNotExist:
                    continue

                if product.stock < qty:
                    messages.warning(
                        self.request,
                        _(f'"{product.name}" skipped — only {product.stock} in stock.')
                    )
                    continue

                try:
                    price_at_time = max(0, float(price_str)) if price_str else product.price
                except (ValueError, TypeError):
                    price_at_time = product.price

                # sold_by: use selected, fall back to visit's own staff
                sold_by = None
                if sold_by_id:
                    try:
                        sold_by = User.objects.get(pk=int(sold_by_id))
                    except (User.DoesNotExist, ValueError):
                        pass
                if not sold_by:
                    sold_by = self.object.staff

                VisitProduct.objects.create(
                    visit=self.object,
                    product=product,
                    quantity=qty,
                    price_at_time=price_at_time,
                    sold_by=sold_by,
                    notes=note,
                )
                product.adjust_stock(-qty)

        return redirect(self.get_success_url())



class VisitDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a visit"""
    model = Visit
    template_name = 'visits/visit_confirm_delete.html'
    success_url = reverse_lazy('visits:list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Visit deleted successfully.'))
        return super().delete(request, *args, **kwargs)


# ✅ NEW: Get incomplete visits count via AJAX
@require_http_methods(["GET"])
def get_incomplete_visits_count(request):
    """
    Return count of incomplete visits as JSON
    Used for dynamically updating notification bell
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': True,
            'count': 0,
            'visits': []
        })
    
    try:
        # 10 newest unpaid visits among the last 50 — one query
        incomplete_list = recent_incomplete_visits()
        
        # Build JSON response with visit details
        visits_data = []
        for visit in incomplete_list:
            visits_data.append({
                'id': visit.id,
                'client_name': visit.appointment.client.full_name,
                'service_name': visit.appointment.service.name,
                'area': visit.area or '',
                'missing_fields': visit.get_missing_fields(),
                'time_since': visit.time_since_creation(),
                'edit_url': f'/visits/{visit.id}/edit/'  # Adjust URL pattern as needed
            })
        
        return JsonResponse({
            'success': True,
            'count': len(incomplete_list),
            'visits': visits_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e),
            'count': 0,
            'visits': []
        }, status=500)


# ─────────────────────────────────────────────
# VISIT PRODUCTS
# ─────────────────────────────────────────────

@require_http_methods(["POST"])
def add_product_to_visit(request, visit_pk):
    """Add a product to a visit, deducting from stock"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=403)

    from alpha.products.models import Product, VisitProduct

    visit = get_object_or_404(Visit, pk=visit_pk)
    product_id = request.POST.get('product_id')
    quantity = int(request.POST.get('quantity', 1))
    notes = request.POST.get('notes', '')

    try:
        product = Product.objects.get(pk=product_id, is_active=True)
    except Product.DoesNotExist:
        messages.error(request, _('Product not found.'))
        return redirect('visits:detail', pk=visit_pk)

    if product.stock < quantity:
        messages.error(
            request,
            _(f'Not enough stock for "{product.name}". Available: {product.stock}, requested: {quantity}')
        )
        return redirect('visits:detail', pk=visit_pk)

    # Create VisitProduct and deduct stock atomically
    from django.db import transaction
    with transaction.atomic():
        VisitProduct.objects.create(
            visit=visit,
            product=product,
            quantity=quantity,
            price_at_time=product.price,
            notes=notes,
        )
        product.adjust_stock(-quantity)

    messages.success(
        request,
        _(f'Added {quantity}x "{product.name}" to this visit.')
    )
    return redirect('visits:detail', pk=visit_pk)


@require_http_methods(["POST"])
def remove_product_from_visit(request, visit_pk, visit_product_pk):
    """Remove a product from a visit, restoring stock"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=403)

    from alpha.products.models import VisitProduct
    from django.db import transaction

    visit_product = get_object_or_404(VisitProduct, pk=visit_product_pk, visit__pk=visit_pk)

    with transaction.atomic():
        product = visit_product.product
        qty = visit_product.quantity
        visit_product.delete()
        product.adjust_stock(qty)  # Restore stock

    messages.success(request, _(f'Removed "{product.name}" from this visit.'))
    return redirect('visits:detail', pk=visit_pk)