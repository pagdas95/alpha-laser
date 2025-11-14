from django.contrib import admin

# Register your models here.
from .models import Appointment

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("start","end","client","service","staff","room","status")
    list_filter = ("status","room","staff","service")
    search_fields = ("client__full_name","client__phone","service__name")