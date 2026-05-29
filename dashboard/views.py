from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.models import TelegramUser
from analytics.models import UserActivity
from orders.models import Order
from payments.models import PaymentRequest


@staff_member_required
def dashboard_view(request):
    """Main dashboard view with key metrics."""
    now = timezone.now()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)

    context = {
        "title": "Dashboard",
        "total_users": TelegramUser.objects.count(),
        "active_users_7d": TelegramUser.objects.filter(last_active_at__gte=last_7_days).count(),
        "active_users_30d": TelegramUser.objects.filter(last_active_at__gte=last_30_days).count(),
        "total_orders": Order.objects.count(),
        "orders_7d": Order.objects.filter(created_at__gte=last_7_days).count(),
        "orders_30d": Order.objects.filter(created_at__gte=last_30_days).count(),
        "total_revenue": Order.objects.aggregate(total=Sum("price_paid"))["total"] or 0,
        "revenue_7d": Order.objects.filter(created_at__gte=last_7_days).aggregate(total=Sum("price_paid"))["total"] or 0,
        "revenue_30d": Order.objects.filter(created_at__gte=last_30_days).aggregate(total=Sum("price_paid"))["total"] or 0,
        "total_topups": PaymentRequest.objects.filter(status=PaymentRequest.Status.APPROVED).count(),
        "topups_7d": PaymentRequest.objects.filter(
            status=PaymentRequest.Status.APPROVED,
            created_at__gte=last_7_days,
        ).count(),
    }

    return render(request, "dashboard/index.html", context)


@staff_member_required
def sales_chart_data(request):
    """API endpoint for sales chart data."""
    days = int(request.GET.get("days", 30))
    start_date = timezone.now() - timedelta(days=days)

    sales_data = (
        Order.objects.filter(created_at__gte=start_date)
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(
            count=Count("id"),
            revenue=Sum("price_paid"),
        )
        .order_by("date")
    )

    return JsonResponse({
        "labels": [str(item["date"]) for item in sales_data],
        "datasets": [
            {
                "label": "Orders",
                "data": [item["count"] for item in sales_data],
                "yAxisID": "y",
            },
            {
                "label": "Revenue (USDT)",
                "data": [float(item["revenue"]) for item in sales_data],
                "yAxisID": "y1",
            },
        ],
    })


@staff_member_required
def user_growth_chart_data(request):
    """API endpoint for user growth chart data."""
    days = int(request.GET.get("days", 30))
    start_date = timezone.now() - timedelta(days=days)

    user_data = (
        TelegramUser.objects.filter(joined_at__gte=start_date)
        .annotate(date=TruncDate("joined_at"))
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    return JsonResponse({
        "labels": [str(item["date"]) for item in user_data],
        "datasets": [
            {
                "label": "New Users",
                "data": [item["count"] for item in user_data],
            },
        ],
    })


@staff_member_required
def activity_chart_data(request):
    """API endpoint for user activity chart data."""
    days = int(request.GET.get("days", 30))
    start_date = timezone.now() - timedelta(days=days)

    activity_data = (
        UserActivity.objects.filter(created_at__gte=start_date)
        .annotate(date=TruncDate("created_at"))
        .values("date", "activity_type")
        .annotate(count=Count("id"))
        .order_by("date")
    )

    # Group by activity type
    activity_types = {}
    for item in activity_data:
        activity_type = item["activity_type"]
        if activity_type not in activity_types:
            activity_types[activity_type] = {}
        activity_types[activity_type][str(item["date"])] = item["count"]

    # Get all dates
    all_dates = sorted(set(str(item["date"]) for item in activity_data))

    datasets = []
    for activity_type, date_counts in activity_types.items():
        datasets.append({
            "label": activity_type.replace("_", " ").title(),
            "data": [date_counts.get(date, 0) for date in all_dates],
        })

    return JsonResponse({
        "labels": all_dates,
        "datasets": datasets,
    })
