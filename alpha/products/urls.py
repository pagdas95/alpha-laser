from django.urls import path
from . import views

app_name = "products"

urlpatterns = [
    # Products
    path("", views.ProductListView.as_view(), name="list"),
    path("add/", views.product_create_view, name="create"),
    path("<int:pk>/", views.ProductDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.product_edit_view, name="edit"),
    path("<int:pk>/delete/", views.product_delete_view, name="delete"),
    path("<int:pk>/stock/", views.product_adjust_stock_view, name="adjust-stock"),

    # Categories
    path("categories/", views.category_list_view, name="categories"),
    path("categories/add/", views.category_create_view, name="category-create"),
    path("categories/<int:pk>/edit/", views.category_edit_view, name="category-edit"),
    path("categories/<int:pk>/delete/", views.category_delete_view, name="category-delete"),

    # API
    path("api/<int:pk>/", views.product_get_api, name="api-detail"),
]