from django.contrib import admin
from .models import Visit

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ("appointment","staff","machine","fluence_j_cm2","pulse_count","charge_amount","paid_amount")
    list_filter = ("staff","machine")
    search_fields = ("appointment__client__full_name","appointment__client__phone")
