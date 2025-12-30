# Module imports (haut de fichier)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import (
    User, Campaign, Spot, SpotSchedule,
    TimeSlot, PricingRule, CampaignHistory, Notification,
    CorrespondenceThread, CorrespondenceMessage,  # <- corrigé ici
    AdvisorySession, ContactRequest, AdvisoryArticle, CaseStudy,
    ServiceCategory, ServiceItem, CoverageRequest, CoverageAttachment
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'company', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'company', 'phone')
    ordering = ('-date_joined',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informations BF1 TV', {
            'fields': ('role', 'phone', 'company', 'address')
        }),
    )


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'status', 'budget', 'start_date', 'end_date', 'objective', 'channel', 'created_at')
    list_filter = ('status', 'start_date', 'end_date', 'created_at')
    search_fields = ('title', 'client__username', 'client__company')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    actions = ['approve_campaigns', 'reject_campaigns']
    
    fieldsets = (
        ('Informations générales', {
            'fields': (
                'id', 'client', 'title', 'description',
                'campaign_type', 'requested_creation',
                'objective', 'channel', 'languages',
                'target_audience', 'key_message'
            )
        }),
        ('Planning', {
            'fields': ('start_date', 'end_date', 'budget', 'preferred_time_slots')
        }),
        ('Statut', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def approve_campaigns(self, request, queryset):
        updated = 0
        for campaign in queryset:
            if campaign.status == 'pending':
                campaign.status = 'approved'
                campaign.approved_by = request.user
                campaign.approved_at = timezone.now()
                campaign.save()
                updated += 1
        
        if updated == 0:
            self.message_user(request, "Aucune campagne n'a été approuvée. Vérifiez que les campagnes sont en attente.", messages.WARNING)
        else:
            self.message_user(request, f"{updated} campagne(s) approuvée(s) avec succès.", messages.SUCCESS)
    approve_campaigns.short_description = "Approuver les campagnes sélectionnées"
    
    def reject_campaigns(self, request, queryset):
        # Cette action redirige vers une page personnalisée pour saisir la raison du rejet
        selected = queryset.values_list('pk', flat=True)
        return HttpResponseRedirect(f"/admin/spot/campaign/reject/?ids={','.join(str(pk) for pk in selected)}")
    reject_campaigns.short_description = "Rejeter les campagnes sélectionnées"


@admin.register(Spot)
class SpotAdmin(admin.ModelAdmin):
    list_display = ('title', 'campaign', 'duration_seconds', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'campaign__title', 'campaign__client__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    actions = ['approve_spots', 'reject_spots']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('id', 'campaign', 'title', 'description')
        }),
        ('Fichier vidéo', {
            'fields': ('video_file', 'duration_seconds')
        }),
        ('Statut', {
            'fields': ('status', 'approved_by', 'approved_at', 'rejection_reason')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def approve_spots(self, request, queryset):
        updated = 0
        for spot in queryset:
            if spot.status == 'pending':
                spot.status = 'approved'
                spot.approved_by = request.user
                spot.approved_at = timezone.now()
                spot.save()
                updated += 1
        
        if updated == 0:
            self.message_user(request, "Aucun spot n'a été approuvé. Vérifiez que les spots sont en attente.", messages.WARNING)
        else:
            self.message_user(request, f"{updated} spot(s) approuvé(s) avec succès.", messages.SUCCESS)
    approve_spots.short_description = "Approuver les spots sélectionnés"
    
    def reject_spots(self, request, queryset):
        # Cette action redirige vers une page personnalisée pour saisir la raison du rejet
        selected = queryset.values_list('pk', flat=True)
        return HttpResponseRedirect(f"/admin/spot/spot/reject/?ids={','.join(str(pk) for pk in selected)}")
    reject_spots.short_description = "Rejeter les spots sélectionnés"


@admin.register(SpotSchedule)
class SpotScheduleAdmin(admin.ModelAdmin):
    list_display = ('spot', 'broadcast_date', 'broadcast_time', 'time_slot', 'price', 'is_broadcasted')
    list_filter = ('broadcast_date', 'time_slot', 'is_broadcasted')
    search_fields = ('spot__title', 'spot__campaign__title')
    date_hierarchy = 'broadcast_date'


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_time', 'end_time', 'price_multiplier', 'is_prime', 'is_active')
    list_filter = ('is_active',)
    ordering = ('start_time',)


@admin.register(PricingRule)
class PricingRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_price', 'duration_min', 'duration_max', 'time_slot_multiplier', 'is_active')
    list_filter = ('is_active',)
    ordering = ('base_price',)


@admin.register(CampaignHistory)
class CampaignHistoryAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'action', 'user', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('campaign__title', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(CorrespondenceThread)
class CorrespondenceThreadAdmin(admin.ModelAdmin):
    list_display = ('subject', 'client', 'status', 'priority', 'last_message_at', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('subject', 'client__username')
    date_hierarchy = 'created_at'

@admin.register(CorrespondenceMessage)
class CorrespondenceMessageAdmin(admin.ModelAdmin):
    list_display = ('thread', 'author', 'created_at')
    search_fields = ('thread__subject', 'author__username', 'content')
    date_hierarchy = 'created_at'

@admin.register(AdvisorySession)
class AdvisorySessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'channel', 'objective', 'recommended_medium', 'recommended_duration_seconds', 'created_at')
    list_filter = ('channel', 'objective', 'created_at')
    search_fields = ('user__username',)

@admin.register(ContactRequest)
class ContactRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'status', 'assigned_to', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'subject')
    actions = ['mark_contacted', 'mark_closed']

    def mark_contacted(self, request, queryset):
        queryset.update(status='contacted')
    mark_contacted.short_description = "Marquer comme contacté"

    def mark_closed(self, request, queryset):
        queryset.update(status='closed')
    mark_closed.short_description = "Marquer comme clôturé"

@admin.register(AdvisoryArticle)
class AdvisoryArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at', 'created_at')
    list_filter = ('is_published', 'published_at')
    search_fields = ('title', 'summary')

@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'published_at', 'created_at')
    list_filter = ('is_published', 'published_at')
    search_fields = ('title', 'summary')


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    ordering = ('order', 'name')


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit', 'unit_quantity', 'requires_timeslot', 'is_quote_only', 'is_active')
    list_filter = ('category', 'unit', 'requires_timeslot', 'is_quote_only', 'is_active')
    search_fields = ('name', 'code', 'description', 'category__name')
    ordering = ('category__order', 'name')


# --- Admin: Demandes de couverture ---
class CoverageAttachmentInline(admin.TabularInline):
    model = CoverageAttachment
    extra = 0
    readonly_fields = ('uploaded_at',)


@admin.register(CoverageRequest)
class CoverageRequestAdmin(admin.ModelAdmin):
    list_display = (
        'event_title', 'user', 'coverage_type', 'status',
        'event_date', 'urgency_level', 'created_at'
    )
    list_filter = ('status', 'coverage_type', 'urgency_level', 'event_date', 'created_at')
    search_fields = (
        'event_title', 'description', 'contact_name', 'contact_phone', 'contact_email'
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [CoverageAttachmentInline]
    actions = ['mark_in_review', 'validate_and_schedule', 'close_requests']

    fieldsets = (
        ('Événement', {
            'fields': (
                'id', 'user', 'event_title', 'event_type', 'event_type_other',
                'description', 'event_date', 'start_time', 'end_time',
                'address', 'meeting_point'
            )
        }),
        ('Coordonnées', {
            'fields': ('contact_name', 'contact_phone', 'contact_email', 'other_contacts')
        }),
        ('Couverture', {
            'fields': ('coverage_type', 'coverage_objective', 'urgency_level', 'response_deadline', 'confirm_info')
        }),
        ('Statut', {
            'fields': ('status',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def mark_in_review(self, request, queryset):
        updated = queryset.update(status='review')
        if updated:
            self.message_user(request, f"{updated} demande(s) passée(s) en révision.", messages.SUCCESS)
        else:
            self.message_user(request, "Aucune demande mise en révision.", messages.INFO)
    mark_in_review.short_description = "Marquer en révision"

    def validate_and_schedule(self, request, queryset):
        updated = queryset.update(status='scheduled')
        if updated:
            self.message_user(request, f"{updated} demande(s) validée(s) et planifiée(s).", messages.SUCCESS)
        else:
            self.message_user(request, "Aucune demande validée.", messages.INFO)
    validate_and_schedule.short_description = "Valider et planifier"

    def close_requests(self, request, queryset):
        updated = queryset.update(status='closed')
        if updated:
            self.message_user(request, f"{updated} demande(s) clôturée(s).", messages.SUCCESS)
        else:
            self.message_user(request, "Aucune demande clôturée.", messages.INFO)
    close_requests.short_description = "Clôturer les demandes"