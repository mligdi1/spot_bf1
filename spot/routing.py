from django.urls import re_path
from .consumers import AdminPendingCountsConsumer, PlanningUpdatesConsumer

websocket_urlpatterns = [
    re_path(r"^ws/admin/pending-counts/$", AdminPendingCountsConsumer.as_asgi()),
    re_path(r"^ws/diffusion/planning/$", PlanningUpdatesConsumer.as_asgi()),
]