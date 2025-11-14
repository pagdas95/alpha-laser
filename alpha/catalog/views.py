"""
Catalog Views - Services & Categories
Place this at: alpha/catalog/views.py
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count, Prefetch
from django.contrib import messages
from django.utils.translation import gettext as _
from .models import ServiceCategory, Service, Package, PackageItem, ClientPackage, ClientPackageItem


# ===== SERVICE CATEGORIES =====

class ServiceCategoryListView(LoginRequiredMixin, ListView):
    """List all service categories"""
    model = ServiceCategory
    template_name = 'catalog/category_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return ServiceCategory.objects.annotate(
            service_count=Count('services')
        ).order_by('name')


class ServiceCategoryCreateView(LoginRequiredMixin, CreateView):
    """Create a new category"""
    model = ServiceCategory
    template_name = 'catalog/category_form.html'
    fields = ['name']
    success_url = reverse_lazy('catalog:category-list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Category created successfully!'))
        return super().form_valid(form)


class ServiceCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """Edit a category"""
    model = ServiceCategory
    template_name = 'catalog/category_form.html'
    fields = ['name']
    success_url = reverse_lazy('catalog:category-list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Category updated successfully!'))
        return super().form_valid(form)


class ServiceCategoryDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a category"""
    model = ServiceCategory
    template_name = 'catalog/category_confirm_delete.html'
    success_url = reverse_lazy('catalog:category-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Category deleted successfully.'))
        return super().delete(request, *args, **kwargs)


# ===== SERVICES =====

class ServiceListView(LoginRequiredMixin, ListView):
    """List all services with filtering"""
    model = Service
    template_name = 'catalog/service_list.html'
    context_object_name = 'services'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Service.objects.select_related('category').all()
        
        # Filter by category
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by gender
        gender = self.request.GET.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(notes__icontains=search)
            )
        
        return queryset.order_by('category__name', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ServiceCategory.objects.all()
        context['total_count'] = Service.objects.count()
        context['current_category'] = self.request.GET.get('category', '')
        context['current_gender'] = self.request.GET.get('gender', '')
        context['current_search'] = self.request.GET.get('search', '')
        context['gender_choices'] = Service.GENDER_CHOICES
        return context


class ServiceCreateView(LoginRequiredMixin, CreateView):
    """Create a new service"""
    model = Service
    template_name = 'catalog/service_form.html'
    fields = ['category', 'name', 'gender', 'default_price', 'duration_min', 'notes']
    success_url = reverse_lazy('catalog:service-list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Service created successfully!'))
        return super().form_valid(form)


class ServiceDetailView(LoginRequiredMixin, DetailView):
    """View service details"""
    model = Service
    template_name = 'catalog/service_detail.html'
    context_object_name = 'service'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get packages that include this service
        context['packages'] = Package.objects.filter(
            items__service=self.object
        ).distinct()
        return context


class ServiceUpdateView(LoginRequiredMixin, UpdateView):
    """Edit a service"""
    model = Service
    template_name = 'catalog/service_form.html'
    fields = ['category', 'name', 'gender', 'default_price', 'duration_min', 'notes']
    
    def get_success_url(self):
        messages.success(self.request, _('Service updated successfully!'))
        return reverse_lazy('catalog:service-detail', kwargs={'pk': self.object.pk})


class ServiceDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a service"""
    model = Service
    template_name = 'catalog/service_confirm_delete.html'
    success_url = reverse_lazy('catalog:service-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Service deleted successfully.'))
        return super().delete(request, *args, **kwargs)


# ===== PACKAGES =====

class PackageListView(LoginRequiredMixin, ListView):
    """List all packages"""
    model = Package
    template_name = 'catalog/package_list.html'
    context_object_name = 'packages'
    
    def get_queryset(self):
        return Package.objects.prefetch_related(
            Prefetch('items', queryset=PackageItem.objects.select_related('service'))
        ).all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_count'] = Package.objects.count()
        return context


class PackageDetailView(LoginRequiredMixin, DetailView):
    """View package details"""
    model = Package
    template_name = 'catalog/package_detail.html'
    context_object_name = 'package'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get items with services
        context['items'] = self.object.items.select_related('service').all()
        # Calculate total sessions
        context['total_sessions'] = sum(item.sessions for item in context['items'])
        # Get clients who purchased this package
        context['client_packages'] = ClientPackage.objects.filter(
            package=self.object
        ).select_related('client').order_by('-purchased_at')[:10]
        return context


class PackageCreateView(LoginRequiredMixin, CreateView):
    """Create a new package"""
    model = Package
    template_name = 'catalog/package_form.html'
    fields = ['name', 'price', 'notes']
    
    def get_success_url(self):
        messages.success(self.request, _('Package created! Now add services to it.'))
        return reverse_lazy('catalog:package-detail', kwargs={'pk': self.object.pk})


class PackageUpdateView(LoginRequiredMixin, UpdateView):
    """Edit a package"""
    model = Package
    template_name = 'catalog/package_form.html'
    fields = ['name', 'price', 'notes']
    
    def get_success_url(self):
        messages.success(self.request, _('Package updated successfully!'))
        return reverse_lazy('catalog:package-detail', kwargs={'pk': self.object.pk})


class PackageDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a package"""
    model = Package
    template_name = 'catalog/package_confirm_delete.html'
    success_url = reverse_lazy('catalog:package-list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Package deleted successfully.'))
        return super().delete(request, *args, **kwargs)


# ===== PACKAGE ITEMS =====

class PackageItemCreateView(LoginRequiredMixin, CreateView):
    """Add a service to a package"""
    model = PackageItem
    template_name = 'catalog/packageitem_form.html'
    fields = ['service', 'sessions']
    
    def dispatch(self, request, *args, **kwargs):
        self.package = Package.objects.get(pk=kwargs['package_pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.package = self.package
        messages.success(self.request, _('Service added to package!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('catalog:package-detail', kwargs={'pk': self.package.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['package'] = self.package
        return context


class PackageItemDeleteView(LoginRequiredMixin, DeleteView):
    """Remove a service from a package"""
    model = PackageItem
    template_name = 'catalog/packageitem_confirm_delete.html'
    
    def get_success_url(self):
        messages.success(self.request, _('Service removed from package.'))
        return reverse_lazy('catalog:package-detail', kwargs={'pk': self.object.package.pk})