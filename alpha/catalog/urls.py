from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = 'catalog'

urlpatterns = [
    # Service Categories
    path('categories/', views.ServiceCategoryListView.as_view(), name='category-list'),
    path('categories/create/', views.ServiceCategoryCreateView.as_view(), name='category-create'),
    path('categories/<int:pk>/edit/', views.ServiceCategoryUpdateView.as_view(), name='category-edit'),
    path('categories/<int:pk>/delete/', views.ServiceCategoryDeleteView.as_view(), name='category-delete'),
    
    # Services
    path('services/', views.ServiceListView.as_view(), name='service-list'),
    path('services/create/', views.ServiceCreateView.as_view(), name='service-create'),
    path('services/<int:pk>/', views.ServiceDetailView.as_view(), name='service-detail'),
    path('services/<int:pk>/edit/', views.ServiceUpdateView.as_view(), name='service-edit'),
    path('services/<int:pk>/delete/', views.ServiceDeleteView.as_view(), name='service-delete'),
    
    # Packages
    path('packages/', views.PackageListView.as_view(), name='package-list'),
    path('packages/create/', views.PackageCreateView.as_view(), name='package-create'),
    path('packages/<int:pk>/', views.PackageDetailView.as_view(), name='package-detail'),
    path('packages/<int:pk>/edit/', views.PackageUpdateView.as_view(), name='package-edit'),
    path('packages/<int:pk>/delete/', views.PackageDeleteView.as_view(), name='package-delete'),
    
    # Package Items
    path('packages/<int:package_pk>/add-service/', views.PackageItemCreateView.as_view(), name='packageitem-create'),
    path('package-items/<int:pk>/delete/', views.PackageItemDeleteView.as_view(), name='packageitem-delete'),
]
