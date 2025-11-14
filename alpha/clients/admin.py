from django.contrib import admin

# Register your models here.
from .models import Client, ClientConsent

class ClientConsentInline(admin.TabularInline):
    model = ClientConsent
    extra = 0

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("full_name","phone","email","skin_type","hair_color")
    search_fields = ("full_name","phone","email")
    inlines = [ClientConsentInline]