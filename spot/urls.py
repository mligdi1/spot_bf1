from django.urls import path
from . import views
from . import views_additional
from . import views_editorial_people

urlpatterns = [
    # Accueil et session
    path('', views.home, name='root'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('home/', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Campagnes & spots
    path('campaigns/', views.campaign_list, name='campaign_list'),
    path('campaigns/create/', views.campaign_create, name='campaign_create'),
    path('campaigns/<uuid:campaign_id>/', views.campaign_detail, name='campaign_detail'),
    path('campaigns/<uuid:campaign_id>/upload/', views.spot_upload, name='spot_upload'),
    path('spots/<uuid:spot_id>/', views.spot_detail, name='spot_detail'),
    path('spots/', views.spot_list, name='spot_list'),

    # Grille de diffusion
    path('broadcasts/', views.broadcast_grid, name='broadcast_grid'),

    # Correspondance (tickets)
    path('correspondence/', views.correspondence_list, name='correspondence_list'),
    path('correspondence/new/', views.correspondence_new, name='correspondence_new'),
    path('correspondence/admin/new/', views.admin_correspondence_new, name='admin_correspondence_new'),
    path('correspondence/<uuid:thread_id>/', views.correspondence_thread, name='correspondence_thread'),

    # API compteurs admin
    path('api/admin/pending-counts/', views_additional.pending_counts_api, name='pending_counts_api'),

    # Conseils, inspiration, tarifs
    path('advisory/wizard/', views.advisor_wizard, name='advisory_wizard'),
    path('guides/', views.guides_list, name='guides_list'),
    path('guides/<slug:slug>/', views.guide_detail, name='guide_detail'),
    path('inspiration/', views.inspiration, name='inspiration'),
    path('pricing/', views.pricing_overview, name='pricing_overview'),
    path('contact/', views.contact_advisor, name='contact_advisor'),
    # Bilan intelligent
    path('reports/overview/', views.report_overview, name='report_overview'),

    # Simulateur de coût (dans views_additional)
    path('cost-simulator/', views_additional.cost_simulator, name='cost_simulator'),

    # Notifications & profil
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark_read/<int:id>/', views.notifications_mark_read, name='notifications_mark_read'),
    path('notifications/mark_all_read/', views.notifications_mark_all_read, name='notifications_mark_all_read'),
    path('notifications/delete/<int:id>/', views.notifications_delete, name='notifications_delete'),
    path('api/notifications/list/', views.notifications_list_partial, name='notifications_list_partial'),
    path('profile/', views.profile, name='profile'),
    # Excel intégration supprimée (export/import activités)

    # Admin
    path('console/login/', views.admin_login, name='admin_login'),
    path('console/logout/', views.admin_logout, name='admin_logout'),
    path('console/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('console/campaigns/<uuid:campaign_id>/approve/', views.admin_campaign_approve, name='admin_campaign_approve'),
    path('console/spots/<uuid:spot_id>/approve/', views.admin_spot_approve, name='admin_spot_approve'),
    path('console/campaigns/', views.admin_campaign_list, name='admin_campaign_list'),
    path('console/coverage/', views.admin_coverage_list, name='admin_coverage_list'),
    path('console/coverage/<uuid:coverage_id>/', views.admin_coverage_detail, name='admin_coverage_detail'),
    # Ajouter le détail des demandes de contact (admin)
    path('console/contacts/<uuid:request_id>/', views.admin_contact_request_detail, name='admin_contact_request_detail'),
    path('admin/spot/campaign/reject/', views_additional.admin_campaign_reject, name='admin_campaign_reject'),
    path('admin/spot/spot/reject/', views_additional.admin_spot_reject, name='admin_spot_reject'),

    # Alias de création combinée (si utilisé)
    path('campaign/create/', views.campaign_spot_create, name='campaign_spot_create'),
    # Demande de couverture médiatique
    path('coverage/request/', views.coverage_request_create, name='coverage_request_create'),
    path('coverage/<uuid:coverage_id>/', views.coverage_request_detail, name='coverage_detail'),
    path('reports/export/', views.excel_export_report, name='report_export'),
    path('reports/export/pdf/', views.pdf_export_report, name='report_export_pdf'),
    # UI styleguide (documentation des composants Tailwind)
    path('ui/styleguide/', views.ui_styleguide, name='ui_styleguide'),

    # API Chatbot (local provider)
    path('api/chat/query/', views_additional.chat_query, name='chat_query'),
    # Interface Rédaction
    path('editorial/dashboard/', views.editorial_dashboard, name='editorial_dashboard'),
    path('editorial/coverages/', views.editorial_coverages, name='editorial_coverages'),
    path('editorial/coverage/<uuid:coverage_id>/', views.editorial_coverage_detail, name='editorial_coverage_detail'),
    path('editorial/coverage/<uuid:coverage_id>/assign/', views.editorial_assign_coverage, name='editorial_assign_coverage'),
    path('editorial/assignments/', views.editorial_assignments, name='editorial_assignments'),
    path('editorial/notifications/', views.editorial_notifications, name='editorial_notifications'),
    path('editorial/planning/', views.editorial_planning, name='editorial_planning'),
    path('editorial/planning/move/', views.editorial_planning_move, name='editorial_planning_move'),
    path('editorial/journalists/', views_editorial_people.journalists_page, name='editorial_journalists'),
    path('editorial/drivers/', views_editorial_people.drivers_page, name='editorial_drivers'),
    path('editorial/api/journalists/', views_editorial_people.api_journalists, name='editorial_api_journalists'),
    path('editorial/api/journalists/<uuid:journalist_id>/', views_editorial_people.api_journalist_detail, name='editorial_api_journalist_detail'),
    path('editorial/api/drivers/', views_editorial_people.api_drivers, name='editorial_api_drivers'),
    path('editorial/api/drivers/<uuid:driver_id>/', views_editorial_people.api_driver_detail, name='editorial_api_driver_detail'),
    path('assignments/confirm/<uuid:campaign_id>/<str:code>/', views.assignment_confirm, name='assignment_confirm'),
    path('assignments/pdf/<uuid:campaign_id>/<str:code>/', views.assignment_pdf, name='assignment_pdf'),
    path('assignments/notify/email/<uuid:campaign_id>/', views.assignment_notify_email, name='assignment_notify_email'),
    path('assignments/notify/whatsapp/<uuid:campaign_id>/', views.assignment_notify_whatsapp, name='assignment_notify_whatsapp'),
    path('webhooks/sms/inbound/', views.sms_inbound, name='sms_inbound'),
]
