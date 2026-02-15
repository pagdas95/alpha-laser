# alpha/staff/urls.py
from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    # Staff list and detail
    path('', views.StaffListView.as_view(), name='list'),
    path('leaves/all/', views.AllLeavesView.as_view(), name='all-leaves'),  # All leaves view
    path('<str:username>/', views.StaffDetailView.as_view(), name='detail'),
    path('<str:username>/edit/', views.StaffProfileUpdateView.as_view(), name='edit'),
    
    # Day-offs
    path('<str:username>/dayoffs/', views.DayOffListView.as_view(), name='dayoff-list'),
    path('<str:username>/dayoffs/add/', views.DayOffCreateView.as_view(), name='dayoff-add'),
    path('dayoff/<int:pk>/edit/', views.DayOffUpdateView.as_view(), name='dayoff-edit'),
    path('dayoff/<int:pk>/delete/', views.DayOffDeleteView.as_view(), name='dayoff-delete'),
    path('dayoff/<int:pk>/approve/', views.DayOffApproveView.as_view(), name='dayoff-approve'),
    path('dayoff/<int:pk>/reject/', views.DayOffRejectView.as_view(), name='dayoff-reject'),
]