from django.views.generic import TemplateView


from django.urls import path
from . import views

app_name = 'visits'

urlpatterns = [
    # List
    path('', views.VisitListView.as_view(), name='list'),
    
    # Detail, update, delete
    path('<int:pk>/', views.VisitDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.VisitUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.VisitDeleteView.as_view(), name='delete'),

        # ✅ NEW: AJAX endpoint for notification bell updates
    path('api/incomplete-count/', views.get_incomplete_visits_count, name='incomplete_count'),
]