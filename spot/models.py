from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.dateparse import parse_date
from decimal import Decimal
import uuid


class User(AbstractUser):
    """Modèle utilisateur étendu pour clients et administrateurs"""
    ROLE_CHOICES = [
        ('client', 'Client'),
        ('admin', 'Administrateur'),
        ('diffuser', 'Diffuseur'),
        ('editorial_manager', 'Responsable Rédaction'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    phone = models.CharField(max_length=20, blank=True, null=True)
    company = models.CharField(max_length=200, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def is_client(self):
        return self.role == 'client'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_diffuser(self):
        return self.role == 'diffuser'

    def is_editorial_manager(self):
        return self.role == 'editorial_manager'


class TimeSlot(models.Model):
    """Créneaux horaires pour la diffusion"""
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    price_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_prime = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"


class Campaign(models.Model):
    """Campagnes publicitaires"""
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée'),
        ('active', 'Active'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    campaign_type = models.CharField(
        max_length=20,
        choices=[('spot_upload', 'Je fournis mon spot'), ('spot_creation', "Je demande la création d'un spot")],
        default='spot_upload'
    )
    requested_creation = models.BooleanField(default=False)
    target_audience = models.CharField(max_length=255, blank=True)
    key_message = models.TextField(blank=True)
    # Nouveaux champs
    objective = models.CharField(
        max_length=20,
        choices=[('notoriete', 'Notoriété'), ('promotion', 'Promotion'), ('sensibilisation', 'Sensibilisation')],
        blank=True,
        null=True
    )
    channel = models.CharField(
        max_length=20,
        choices=[('tv', 'Télévision'), ('urban', 'Écran urbain'), ('online', 'En ligne')],
        blank=True,
        null=True
    )
    preferred_time_slots = models.ManyToManyField('TimeSlot', blank=True, related_name='preferred_in_campaigns')
    languages = models.CharField(max_length=200, blank=True)  # CSV: ex "fr,en"
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_campaigns')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.client.username}"
    
    @property
    def duration_days(self):
        start = self.start_date
        end = self.end_date
        if isinstance(start, str):
            start = parse_date(start)
        if isinstance(end, str):
            end = parse_date(end)
        if not start or not end:
            return 0
        return (end - start).days + 1


class Spot(models.Model):
    """Spots publicitaires"""
    STATUS_CHOICES = [
        ('uploaded', 'Téléchargé'),
        ('pending_review', 'En attente de validation'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('scheduled', 'Programmé'),
        ('broadcasted', 'Diffusé'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='spots')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # Nouveau: type de média (image ou vidéo)
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Vidéo'),
    ]
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    
    # Nouveau: fichier image
    image_file = models.ImageField(
        upload_to='spots/images/',
        null=True,
        blank=True
    )
    
    # Fichier vidéo existant
    video_file = models.FileField(
        upload_to='spots/videos/',
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'avi', 'mov', 'wmv'])],
        null=True,
        blank=True
    )
    
    # Rendre optionnelle (utile uniquement pour vidéo)
    duration_seconds = models.IntegerField(
        validators=[MinValueValidator(5), MaxValueValidator(300)],
        null=True,
        blank=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_spots')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.campaign.title}"


class SpotSchedule(models.Model):
    """Programmation des spots"""
    spot = models.ForeignKey(Spot, on_delete=models.CASCADE, related_name='schedules')
    time_slot = models.ForeignKey(TimeSlot, on_delete=models.CASCADE)
    broadcast_date = models.DateField()
    broadcast_time = models.TimeField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_broadcasted = models.BooleanField(default=False)
    broadcasted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['broadcast_date', 'broadcast_time']
        unique_together = ['time_slot', 'broadcast_date', 'broadcast_time']
    
    def __str__(self):
        return f"{self.spot.title} - {self.broadcast_date} {self.broadcast_time}"
# Modèles Payment et Invoice supprimés
class PricingRule(models.Model):
    """Règles de tarification"""
    name = models.CharField(max_length=100)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_min = models.IntegerField(validators=[MinValueValidator(5)])
    duration_max = models.IntegerField(validators=[MaxValueValidator(300)])
    time_slot_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.base_price} FCFA"


class CampaignHistory(models.Model):
    """Historique des campagnes"""
    ACTION_CHOICES = [
        ('created', 'Créée'),
        ('updated', 'Modifiée'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée'),
        ('payment_made', 'Paiement effectué'),
        ('spot_uploaded', 'Spot téléchargé'),
        ('spot_approved', 'Spot approuvé'),
        ('broadcasted', 'Diffusé'),
    ]
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='history')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.campaign.title} - {self.action}"


class Notification(models.Model):
    """Notifications pour les utilisateurs"""
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('success', 'Succès'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, null=True, blank=True)
    # Nouvelle relation: redirection directe vers un spot spécifique
    related_spot = models.ForeignKey('Spot', on_delete=models.CASCADE, null=True, blank=True)
    # Lien direct vers une demande de couverture
    related_coverage = models.ForeignKey('CoverageRequest', on_delete=models.SET_NULL, null=True, blank=True)
    related_thread = models.ForeignKey('CorrespondenceThread', on_delete=models.SET_NULL, null=True, blank=True)
    related_contact = models.ForeignKey('ContactRequest', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"


class CorrespondenceThread(models.Model):
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('pending', 'En attente'),
        ('closed', 'Clôturé'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='correspondence_threads')
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    related_campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='correspondence_threads')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_threads')
    priority = models.CharField(max_length=10, choices=[('normal', 'Normal'), ('urgent', 'Urgent')], default='normal')
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} ({self.get_status_display()})"


class CorrespondenceMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(CorrespondenceThread, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    attachment = models.FileField(upload_to='correspondence/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message de {self.author.username} - {self.created_at}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.thread.last_message_at = self.created_at
        self.thread.save(update_fields=['last_message_at', 'updated_at'])

class AdvisorySession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    channel = models.CharField(max_length=20, choices=[('tv', 'Télévision'), ('urban', 'Écran urbain'), ('online', 'En ligne')])
    has_spot_ready = models.BooleanField(default=False)
    objective = models.CharField(max_length=20, choices=[('notoriete', 'Notoriété'), ('promotion', 'Promotion'), ('sensibilisation', 'Sensibilisation')])
    budget_estimate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    recommended_medium = models.CharField(max_length=20, blank=True)
    recommended_duration_seconds = models.IntegerField(null=True, blank=True)
    recommended_budget = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Orientation {self.channel} ({self.objective})"

class ContactRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=50, blank=True)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    preferred_contact_time = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=[('new', 'Nouveau'), ('contacted', 'Contacté'), ('closed', 'Clôturé')], default='new')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='contact_requests_assigned')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} - {self.name}"

class AdvisoryArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    summary = models.TextField(blank=True)
    content = models.TextField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

class CaseStudy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    summary = models.TextField()
    content = models.TextField()
    video_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title


class ServiceCategory(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class ServiceItem(models.Model):
    UNIT_CHOICES = [
        ('JOUR', 'Jour'), ('SEMAINE', 'Semaine'), ('MOIS', 'Mois'),
        ('HEURE', 'Heure'), ('MINUTE', 'Minute'), ('SPOT', 'Spot'),
        ('FORFAIT', 'Forfait'),
    ]
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, blank=True)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES)
    unit_quantity = models.PositiveIntegerField(default=1)
    min_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    max_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    requires_timeslot = models.BooleanField(default=False)
    timeslot_notes = models.CharField(max_length=200, blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_quote_only = models.BooleanField(default=False)  # “Sur devis”
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category__order', 'name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"

# --- Nouvelle fonctionnalité: Demande de couverture ---
class CoverageRequest(models.Model):
    EVENT_TYPE_CHOICES = [
        ('press_conference', 'Conférence de presse'),
        ('seminar_workshop', 'Séminaire / Atelier'),
        ('inauguration', 'Inauguration'),
        ('public_event', 'Manifestation publique'),
        ('government_activity', 'Activité gouvernementale'),
        ('product_launch', 'Lancement de produit'),
        ('interviews', 'Interviews'),
        ('cultural_sport', 'Événement culturel / sportif'),
        ('other', 'Autre'),
    ]

    COVERAGE_TYPE_CHOICES = [
        ('video_report', 'Reportage vidéo'),
        ('photo_report', 'Reportage photo'),
        ('interview', 'Interview'),
        ('voiceover_micro', 'Voix off / Micro-trottoir'),
        ('live', 'Direct / Live'),
        ('web_article', 'Article web'),
        ('mix_video_interview', 'Mix vidéo + interview'),
        ('editorial_defined', 'À définir par la rédaction'),
    ]

    URGENCY_CHOICES = [
        ('normal', 'Normal'),
        ('priority', 'Prioritaire'),
        ('urgent_24h', 'Urgent (dans les 24h)'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    event_title = models.CharField(max_length=255)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    event_type_other = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(null=True, blank=True)
    address = models.CharField(max_length=255)
    meeting_point = models.CharField(max_length=255, blank=True)

    contact_name = models.CharField(max_length=200)
    contact_phone = models.CharField(max_length=50)
    contact_email = models.EmailField(blank=True)
    other_contacts = models.TextField(blank=True)

    coverage_type = models.CharField(max_length=50, choices=COVERAGE_TYPE_CHOICES)
    coverage_objective = models.TextField(blank=True)

    urgency_level = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='normal')
    response_deadline = models.DateField(null=True, blank=True)
    confirm_info = models.BooleanField(default=False)

    status = models.CharField(max_length=20, choices=[('new', 'Nouveau'), ('review', 'En révision'), ('scheduled', 'Planifié'), ('closed', 'Clôturé')], default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Couverture: {self.event_title} ({self.event_date})"


class CoverageAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(CoverageRequest, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='coverage_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pièce jointe {self.id}"


class Journalist(models.Model):
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('on_mission', 'En mission'),
        ('resting', 'En repos'),
        ('offline', 'Hors ligne'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    photo = models.ImageField(upload_to='journalists/', blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    specialties = models.TextField(blank=True)
    workload_score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Driver(models.Model):
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('on_mission', 'En mission'),
        ('resting', 'En repos'),
        ('offline', 'Hors ligne'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    photo = models.ImageField(upload_to='drivers/', blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    vehicle_status = models.CharField(max_length=100, blank=True, help_text="État du véhicule attribué (ex: Bon état, En maintenance)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CoverageAssignment(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigné'),
        ('in_field', 'Sur le terrain'),
        ('delivered', 'Contenu livré'),
        ('done', 'Terminé'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coverage = models.ForeignKey(CoverageRequest, on_delete=models.CASCADE, related_name='assignments')
    journalist = models.ForeignKey(Journalist, on_delete=models.SET_NULL, null=True, blank=True)
    driver = models.ForeignKey(Driver, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Assignation {self.id} — {self.coverage.event_title}"


class AssignmentLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(CoverageAssignment, on_delete=models.CASCADE, related_name='logs')
    label = models.CharField(max_length=100)
    note = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.label}"


class AssignmentNotificationCampaign(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('confirmed', 'Confirmée'),
        ('expired', 'Expirée'),
        ('cancelled', 'Annulée'),
    ]
    RECIPIENT_CHOICES = [
        ('journalist', 'Journaliste'),
        ('driver', 'Chauffeur'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(CoverageAssignment, on_delete=models.CASCADE, related_name='notification_campaigns')
    recipient_kind = models.CharField(max_length=20, choices=RECIPIENT_CHOICES)
    to_email = models.EmailField(blank=True, null=True)
    to_phone = models.CharField(max_length=50, blank=True, null=True)
    confirm_code = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    reminder_count = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(blank=True, null=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    confirmed_via = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notif {self.recipient_kind} — {self.assignment_id}"


class AssignmentNotificationAttempt(models.Model):
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('web', 'Web'),
    ]
    STATUS_CHOICES = [
        ('queued', 'En file'),
        ('sent', 'Envoyé'),
        ('delivered', 'Délivré'),
        ('failed', 'Échec'),
        ('skipped', 'Ignoré'),
        ('confirmed', 'Confirmé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(AssignmentNotificationCampaign, on_delete=models.CASCADE, related_name='attempts')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    to = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    provider = models.CharField(max_length=50, blank=True)
    provider_message_id = models.CharField(max_length=120, blank=True)
    error = models.TextField(blank=True)
    meta = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.channel} — {self.status}"
