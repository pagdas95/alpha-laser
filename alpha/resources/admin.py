from django.contrib import admin

# Register your models here.
from .models import Room, Machine

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name","is_active")
    list_filter = ("is_active",)

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ("name","is_active")
    list_filter = ("is_active",)