from django.contrib import admin

# Register your models here.
from .models import ServiceCategory, Service, Package, PackageItem, ClientPackage, ClientPackageItem

class PackageItemInline(admin.TabularInline):
    model = PackageItem
    extra = 0

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name","price")
    inlines = [PackageItemInline]

class ClientPackageItemInline(admin.TabularInline):
    model = ClientPackageItem
    extra = 0
    readonly_fields = ("package_item",)

@admin.register(ClientPackage)
class ClientPackageAdmin(admin.ModelAdmin):
    list_display = ("client","package","purchased_at","price_paid","active")
    inlines = [ClientPackageItemInline]

admin.site.register(ServiceCategory)
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name","category","gender","default_price","duration_min")
    list_filter = ("category","gender")
    search_fields = ("name",)