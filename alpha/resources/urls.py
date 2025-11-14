from django.views.generic import TemplateView

"""
Resources app URL configuration
Place this file at: alpha/resources/urls.py
"""
"""
Resources URLs - Simple Version
Place this at: alpha/resources/urls.py
"""
from django.urls import path
from . import views

app_name = 'resources'

urlpatterns = [
    # Resources Dashboard
    path('', views.ResourcesIndexView.as_view(), name='index'),
    
    # Machines
    path('machines/', views.MachineListView.as_view(), name='machine-list'),
    path('machines/create/', views.MachineCreateView.as_view(), name='machine-create'),
    path('machines/<int:pk>/', views.MachineDetailView.as_view(), name='machine-detail'),
    path('machines/<int:pk>/update/', views.MachineUpdateView.as_view(), name='machine-update'),
    path('machines/<int:pk>/delete/', views.MachineDeleteView.as_view(), name='machine-delete'),
    
    # Rooms
    path('rooms/', views.RoomListView.as_view(), name='room-list'),
    path('rooms/create/', views.RoomCreateView.as_view(), name='room-create'),
    path('rooms/<int:pk>/', views.RoomDetailView.as_view(), name='room-detail'),
    path('rooms/<int:pk>/update/', views.RoomUpdateView.as_view(), name='room-update'),
    path('rooms/<int:pk>/delete/', views.RoomDeleteView.as_view(), name='room-delete'),
]