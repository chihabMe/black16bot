from django.urls import path

from dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.dashboard_view, name="index"),
    path("api/sales/", views.sales_chart_data, name="sales_chart"),
    path("api/users/", views.user_growth_chart_data, name="user_growth_chart"),
    path("api/activities/", views.activity_chart_data, name="activity_chart"),
]
