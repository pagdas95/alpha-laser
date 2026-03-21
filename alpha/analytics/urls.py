"""
Analytics URLs - COMPLETE AND READY TO USE
Place this at: alpha/analytics/urls.py
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Main dashboard (handles both daily and monthly)
    path('', views.AnalyticsDashboardView.as_view(), name='dashboard'),
    
    # API for chart data
    path('api/chart-data/', views.AnalyticsDataAPIView.as_view(), name='chart-data'),
    
    # Your original Excel export (KEEP THIS ONE)
    path('export/monthly-report/', views.ExportMonthlyReportView.as_view(), name='export-monthly'),
]