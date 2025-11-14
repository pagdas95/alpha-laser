from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = 'clients'  # ← THIS IS CRITICAL!

urlpatterns = [
    # path('', TemplateView.as_view(template_name="pages/home.html"), name='list'),
    # path('create/', TemplateView.as_view(template_name="pages/home.html"), name='create'),

    path('', views.ClientListView.as_view(), name='list'),
    path('create/', views.ClientCreateView.as_view(), name='create'),

        # Detail, update, delete
    path('<int:pk>/', views.ClientDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.ClientUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.ClientDeleteView.as_view(), name='delete'),
]