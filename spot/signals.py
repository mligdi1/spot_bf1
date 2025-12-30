from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Campaign, CampaignHistory, Notification, Spot, CorrespondenceThread
from django.utils import timezone
from decimal import Decimal
from .models import SpotSchedule, TimeSlot  # Ajouté
from datetime import timedelta              # Ajouté
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()


def _pending_counts():
    return {
        'count_campaigns_pending': Campaign.objects.filter(status='pending').count(),
        'count_spots_pending': Spot.objects.filter(status='pending_review').count(),
        'count_messages_pending': CorrespondenceThread.objects.filter(status='pending').count(),
    }


def broadcast_pending_counts():
    layer = get_channel_layer()
    if not layer:
        return
    async_to_sync(layer.group_send)(
        'admin_pending_counts',
        {
            'type': 'counts_update',
            'data': _pending_counts(),
        }
    )


@receiver(post_save, sender=Campaign)
def create_campaign_history(sender, instance, created, **kwargs):
    """Créer un historique automatique pour les campagnes"""
    if created:
        CampaignHistory.objects.create(
            campaign=instance,
            action='created',
            description=f'Campagne "{instance.title}" créée',
            user=instance.client
        )
    else:
        # Détecter les changements de statut
        if instance.status == 'approved':
            CampaignHistory.objects.create(
                campaign=instance,
                action='approved',
                description=f'Campagne "{instance.title}" approuvée',
                user=instance.approved_by
            )
            # Anti-doublon: éviter plusieurs notifications pour la même campagne approuvée
            if not Notification.objects.filter(
                user=instance.client,
                related_campaign=instance,
                title='Campagne approuvée'
            ).exists():
                Notification.objects.create(
                    user=instance.client,
                    title='Campagne approuvée',
                    message=f'Votre campagne "{instance.title}" a été approuvée.',
                    type='success',
                    related_campaign=instance
                )
            # === Programmations automatiques dans la grille de diffusion ===
            # Spot approuvé (priorité au plus récemment approuvé)
            approved_spot = instance.spots.filter(status='approved').order_by('-approved_at').first()
            if approved_spot:
                # Créneaux préférés actifs
                preferred_slots = list(instance.preferred_time_slots.filter(is_active=True))
                created_count = 0
                if preferred_slots:
                    current_date = instance.start_date
                    while current_date <= instance.end_date:
                        for ts in preferred_slots:
                            base_time = ts.start_time
                            # Éviter les conflits (contrainte unique: time_slot/date/heure)
                            already_exists = SpotSchedule.objects.filter(
                                time_slot=ts,
                                broadcast_date=current_date,
                                broadcast_time=base_time
                            ).exists()
                            if not already_exists:
                                SpotSchedule.objects.create(
                                    spot=approved_spot,
                                    time_slot=ts,
                                    broadcast_date=current_date,
                                    broadcast_time=base_time,
                                    price=Decimal('0')
                                )
                                created_count += 1
                        current_date += timedelta(days=1)
                    if created_count > 0:
                        CampaignHistory.objects.create(
                            campaign=instance,
                            action='updated',
                            description=f'{created_count} programmation(s) créée(s) automatiquement à l’approbation.',
                            user=instance.approved_by
                        )
            # === Fin programmation auto ===
        elif instance.status == 'rejected':
            CampaignHistory.objects.create(
                campaign=instance,
                action='rejected',
                description=f'Campagne "{instance.title}" rejetée: {instance.rejection_reason}',
                user=instance.approved_by
            )
            # Anti-doublon: éviter plusieurs notifications rejet pour la même campagne
            if not Notification.objects.filter(
                user=instance.client,
                related_campaign=instance,
                title='Campagne rejetée'
            ).exists():
                Notification.objects.create(
                    user=instance.client,
                    title='Campagne rejetée',
                    message=f'Votre campagne "{instance.title}" a été rejetée. Raison: {instance.rejection_reason}',
                    type='error',
                    related_campaign=instance
                )

    # Diffuser les nouveaux compteurs après toute sauvegarde de campagne
    broadcast_pending_counts()


@receiver(post_save, sender=Spot)
def create_spot_notification(sender, instance, created, **kwargs):
    """Créer des notifications pour les spots"""
    if created:
        CampaignHistory.objects.create(
            campaign=instance.campaign,
            action='spot_uploaded',
            description=f'Spot "{instance.title}" téléchargé',
            user=instance.campaign.client
        )
        # Notifier les administrateurs
        admins = User.objects.filter(role='admin')
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title='Nouveau spot téléchargé',
                message=f'Un nouveau spot "{instance.title}" a été téléchargé pour la campagne "{instance.campaign.title}".',
                type='info',
                related_campaign=instance.campaign,
                related_spot=instance
            )
    else:
        if instance.status == 'approved':
            CampaignHistory.objects.create(
                campaign=instance.campaign,
                action='spot_approved',
                description=f'Spot "{instance.title}" approuvé',
                user=instance.approved_by
            )
            # Anti-doublon: éviter plusieurs notifications spot approuvé pour le même spot
            if not Notification.objects.filter(
                user=instance.campaign.client,
                related_campaign=instance.campaign,
                title='Spot approuvé'
            ).exists():
                Notification.objects.create(
                    user=instance.campaign.client,
                    title='Spot approuvé',
                    message=f'Votre spot "{instance.title}" a été approuvé.',
                    type='success',
                    related_campaign=instance.campaign,
                    related_spot=instance
                )

            # Notifier les diffuseurs (interface diffusion)
            UserModel = get_user_model()
            diffusers = UserModel.objects.filter(role='diffuser')
            for diffuser in diffusers:
                if not Notification.objects.filter(
                    user=diffuser,
                    related_spot=instance,
                    title='Spot approuvé (Diffusion)'
                ).exists():
                    Notification.objects.create(
                        user=diffuser,
                        title='Spot approuvé (Diffusion)',
                        message=f'Le spot "{instance.title}" a été approuvé et est prêt à la programmation.',
                        type='success',
                        related_campaign=instance.campaign,
                        related_spot=instance
                    )
    # Diffuser les nouveaux compteurs après toute sauvegarde de spot
    broadcast_pending_counts()


# Émissions complémentaires sur suppression
@receiver(post_delete, sender=Campaign)
def broadcast_on_campaign_delete(sender, instance, **kwargs):
    broadcast_pending_counts()


@receiver(post_delete, sender=Spot)
def broadcast_on_spot_delete(sender, instance, **kwargs):
    broadcast_pending_counts()


@receiver(post_save, sender=CorrespondenceThread)
def broadcast_on_thread_save(sender, instance, created, **kwargs):
    broadcast_pending_counts()


@receiver(post_delete, sender=CorrespondenceThread)
def broadcast_on_thread_delete(sender, instance, **kwargs):
    broadcast_pending_counts()
