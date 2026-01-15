from django.urls import path
from django.contrib.auth.decorators import user_passes_test
from . import views_diffusion

is_diffuser_required = user_passes_test(lambda u: u.is_authenticated and hasattr(u, 'is_diffuser') and u.is_diffuser())

urlpatterns = [
    path('', is_diffuser_required(views_diffusion.home), name='diffusion_home'),
    path('profil/', is_diffuser_required(views_diffusion.profile), name='diffusion_profile'),
    # Nouveaux écrans
    path('spots/', is_diffuser_required(views_diffusion.spots_list), name='diffusion_spots'),
    path('spots/retards/', is_diffuser_required(views_diffusion.spots_late), name='diffusion_spots_late'),
    path('spots/broadcasted/', is_diffuser_required(views_diffusion.spots_broadcasted_list), name='diffusion_spots_broadcasted'),
    path('spots/<uuid:spot_id>/', is_diffuser_required(views_diffusion.spot_detail_diffusion), name='diffusion_spot_detail'),
    path('spots/bulk_schedule/<uuid:spot_id>/', is_diffuser_required(views_diffusion.bulk_schedule_spot), name='diffusion_bulk_schedule_spot'),
    path('spots/mark_broadcasted/<uuid:spot_id>/', is_diffuser_required(views_diffusion.mark_spot_broadcasted), name='diffusion_mark_broadcasted'),
    path('spots/notify_broadcast_time/<uuid:spot_id>/', is_diffuser_required(views_diffusion.notify_broadcast_time), name='diffusion_notify_broadcast_time'),
    path('spots/report/<uuid:spot_id>/', is_diffuser_required(views_diffusion.report_problem), name='diffusion_report_problem'),
    path('planning/', is_diffuser_required(views_diffusion.planning), name='diffusion_planning'),
    path('planning/move/', is_diffuser_required(views_diffusion.planning_move), name='diffusion_planning_move'),
    path('planning/delete/', is_diffuser_required(views_diffusion.planning_delete), name='diffusion_planning_delete'),
    path('planning/confirm_broadcast/', is_diffuser_required(views_diffusion.planning_confirm_broadcast), name='diffusion_planning_confirm_broadcast'),
    path('planning/undo_broadcast/', is_diffuser_required(views_diffusion.planning_undo_broadcast), name='diffusion_planning_undo_broadcast'),
    path('telechargements/spot/<uuid:spot_id>/', is_diffuser_required(views_diffusion.download_spot_media), name='diffusion_download_spot'),
    path('notifications/', is_diffuser_required(views_diffusion.notifications_diffusion), name='diffusion_notifications'),
    path('notifications/mark_read/<int:id>/', is_diffuser_required(views_diffusion.diffusion_notifications_mark_read), name='diffusion_notifications_mark_read'),
    path('notifications/mark_all_read/', is_diffuser_required(views_diffusion.diffusion_notifications_mark_all_read), name='diffusion_notifications_mark_all_read'),
    path('notifications/delete/<int:id>/', is_diffuser_required(views_diffusion.diffusion_notifications_delete), name='diffusion_notifications_delete'),
    path('chat/', is_diffuser_required(views_diffusion.diffusion_support_chat), name='diffusion_support_chat'),
    path('chat/<uuid:thread_id>/', is_diffuser_required(views_diffusion.diffusion_chat_thread), name='diffusion_chat_thread'),
    # API et exports
    path('api/notifications/list/', is_diffuser_required(views_diffusion.diffusion_notifications_list_partial), name='diffusion_notifications_list_partial'),
    path('api/kpi/', is_diffuser_required(views_diffusion.kpi_api), name='diffusion_kpi_api'),
    path('api/clients-search/', is_diffuser_required(views_diffusion.clients_search_api), name='diffusion_clients_search_api'),
    path('export/spots/csv/', is_diffuser_required(views_diffusion.export_spots_csv), name='diffusion_export_spots_csv'),
    path('export/spots/xlsx/', is_diffuser_required(views_diffusion.export_spots_xlsx), name='diffusion_export_spots_xlsx'),
    path('export/spots/broadcasted/pdf/', is_diffuser_required(views_diffusion.export_spots_broadcasted_pdf), name='diffusion_export_spots_broadcasted_pdf'),
]
