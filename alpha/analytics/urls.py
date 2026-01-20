"""
Analytics URLs
Place this at: alpha/analytics/urls.py
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    
    path('', views.AnalyticsDashboardView.as_view(), name='dashboard'),
    path('api/chart-data/', views.AnalyticsDataAPIView.as_view(), name='chart-data'),
    path('export/monthly-report/', views.ExportMonthlyReportView.as_view(), name='export-monthly'),
]