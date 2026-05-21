from django.urls import path

from api_access import views

urlpatterns = [
    path("products/", views.products),
    path("orders/", views.create_order),
]
