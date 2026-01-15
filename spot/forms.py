from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML
from django.utils import timezone  # ← IMPORT AJOUTÉ
from .models import Campaign, Spot, TimeSlot, CoverageRequest

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    """Formulaire d'inscription personnalisé"""
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=True, label='Téléphone')
    company = forms.CharField(max_length=200, required=True, label='Entreprise')
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label='Adresse')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'company', 'address', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('username', css_class='form-group col-md-6 mb-0'),
                Column('email', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('phone', css_class='form-group col-md-6 mb-0'),
                Column('company', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'address',
            Row(
                Column('password1', css_class='form-group col-md-6 mb-0'),
                Column('password2', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', 'Créer mon compte', css_class='btn btn-primary btn-block')
        )

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            return email
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Cette adresse email est déjà utilisée par un autre compte.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            return username
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà utilisé.")
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = (self.cleaned_data.get('first_name') or '').strip()
        user.last_name = (self.cleaned_data.get('last_name') or '').strip()
        user.phone = self.cleaned_data['phone']
        user.company = self.cleaned_data['company']
        user.address = self.cleaned_data['address']
        user.role = 'client'  # Par défaut, les nouveaux utilisateurs sont des clients
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Formulaire de connexion personnalisé"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'username',
            'password',
            Submit('submit', 'Se connecter', css_class='btn btn-primary btn-block')
        )


class CampaignForm(forms.ModelForm):
    """Formulaire de création de campagne"""
    class Meta:
        model = Campaign
        fields = [
            'title', 'description', 'start_date', 'end_date', 'budget',
            'campaign_type', 'requested_creation',
            'objective', 'channel', 'preferred_time_slots', 'languages',
            'target_audience', 'key_message'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'campaign_type': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-bf1-red'}),
            'requested_creation': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-bf1-red'}),
            'objective': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-bf1-red'}),
            'channel': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-bf1-red'}),
            'preferred_time_slots': forms.SelectMultiple(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-bf1-red'}),
            'languages': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-bf1-red', 'placeholder': 'Ex: fr, en'}),
            'target_audience': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-bf1-red'}),
            'key_message': forms.Textarea(attrs={'rows': 3, 'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-bf1-red'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            'description',
            Row(
                Column('start_date', css_class='form-group col-md-6 mb-0'),
                Column('end_date', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'budget',
            Submit('submit', 'Créer la campagne', css_class='btn btn-primary')
        )
        self.fields['title'].help_text = "Intitulé clair (ex: Promo Rentrée BF1TV)."
        self.fields['description'].help_text = "Précisez l’objectif, l’audience et les canaux envisagés."
        self.fields['start_date'].help_text = "Date de début de la campagne."
        self.fields['end_date'].help_text = "Date de fin (postérieure à la date de début)."
        self.fields['budget'].help_text = "Budget indicatif (aucun paiement en ligne)."
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise forms.ValidationError("La date de fin doit être postérieure à la date de début.")
            
            if start_date < timezone.now().date():
                raise forms.ValidationError("La date de début ne peut pas être dans le passé.")
        
        return cleaned_data


class SpotForm(forms.ModelForm):
    """Formulaire de téléchargement de spot"""
    class Meta:
        model = Spot
        fields = ['title', 'description', 'media_type', 'image_file', 'video_file', 'duration_seconds']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['media_type'].label = 'Type de média'
        self.fields['image_file'].label = 'Image (JPEG/PNG)'
        self.fields['video_file'].label = 'Vidéo (MP4/AVI/MOV/WMV)'
        self.fields['duration_seconds'].label = 'Durée (en secondes, pour vidéo)'
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            'description',
            'media_type',
            'image_file',
            'video_file',
            'duration_seconds',
            Submit('submit', 'Télécharger le spot', css_class='btn btn-primary')
        )
    
    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get('media_type')
        image_file = cleaned_data.get('image_file')
        video_file = cleaned_data.get('video_file')
        duration_seconds = cleaned_data.get('duration_seconds')

        if media_type == 'image':
            if not image_file:
                raise forms.ValidationError("Veuillez sélectionner une image pour le type 'Image'.")
            cleaned_data['video_file'] = None
            cleaned_data['duration_seconds'] = None

        elif media_type == 'video':
            if not video_file:
                raise forms.ValidationError("Veuillez sélectionner une vidéo pour le type 'Vidéo'.")
            if not duration_seconds:
                raise forms.ValidationError("Veuillez indiquer la durée (en secondes) pour la vidéo.")
        else:
            raise forms.ValidationError("Type de média invalide.")

        return cleaned_data

    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')
        if video_file:
            # Vérifier la taille du fichier (max 100MB)
            if video_file.size > 100 * 1024 * 1024:
                raise forms.ValidationError("Le fichier vidéo ne doit pas dépasser 100MB.")
            
            # Vérifier l'extension
            allowed_extensions = ['mp4', 'avi', 'mov', 'wmv']
            file_extension = video_file.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(f"Format non supporté. Formats acceptés: {', '.join(allowed_extensions)}")
        
        return video_file

class CostSimulatorForm(forms.Form):
    """Formulaire du simulateur de coût"""
    duration = forms.IntegerField(
        min_value=5,
        max_value=300,
        label='Durée (secondes)',
        help_text='Durée du spot en secondes (5-300s)'
    )
    time_slot = forms.ModelChoiceField(
        queryset=TimeSlot.objects.filter(is_active=True),
        label='Créneau horaire',
        help_text='Sélectionnez le créneau de diffusion'
    )
    broadcast_count = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=1,
        label='Nombre de diffusions',
        help_text='Nombre de fois que le spot sera diffusé'
    )
    campaign_duration = forms.IntegerField(
        min_value=1,
        max_value=365,
        initial=30,
        label='Durée de campagne (jours)',
        help_text='Durée totale de la campagne en jours'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('duration', css_class='form-group col-md-6 mb-0'),
                Column('time_slot', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('broadcast_count', css_class='form-group col-md-6 mb-0'),
                Column('campaign_duration', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', 'Calculer le coût', css_class='btn btn-primary')
        )


class CampaignSpotForm(forms.Form):
    """Formulaire unifié pour créer campagne et uploader le spot en une fois"""
    
    # Champs de campagne
    title = forms.CharField(
        max_length=200,
        label='Titre de la campagne',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Ex: Promotion Été 2024'
        })
    )
    
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Décrivez votre campagne publicitaire...'
        }),
        label='Description'
    )
    
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        }),
        label='Date de début'
    )
    
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
        }),
        label='Date de fin'
    )
    
    budget = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bf1-red focus:border-bf1-red',
            'placeholder': '0.00',
            'step': '0.01'
        }),
        label='Budget (FCFA)'
    )
    # Nouveaux champs (conformes et requis selon ta consigne)
    objective = forms.ChoiceField(
        choices=[('notoriete', 'Notoriété'), ('promotion', 'Promotion'), ('sensibilisation', 'Sensibilisation')],
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bf1-red focus:border-bf1-red'}),
        label='Objectif de la campagne'
    )
    channel = forms.ChoiceField(
        choices=[('tv', 'Télévision'), ('urban', 'Écran urbain'), ('online', 'En ligne')],
        widget=forms.Select(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bf1-red focus:border-bf1-red'}),
        label='Canal de diffusion'
    )
    preferred_time_slots = forms.ModelMultipleChoiceField(
        required=False,
        queryset=TimeSlot.objects.filter(is_active=True),
        widget=forms.SelectMultiple(attrs={'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bf1-red focus:border-bf1-red'}),
        label='Créneaux horaires préférés'
    )
    languages = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bf1-red focus:border-bf1-red',
            'placeholder': 'Ex: fr, en'
        }),
        label='Langues de diffusion/production'
    )
    # Champs détaillés (optionnels, conformes au modèle) — MODE DÉTAILLÉ
    campaign_type = forms.ChoiceField(
        required=False,
        choices=[('spot_upload', "Je fournis mon spot"), ('spot_creation', "Je demande la création d'un spot")],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bf1-red focus:border-bf1-red'
        }),
        label='Type de campagne'
    )
    requested_creation = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-bf1-red focus:ring-bf1-red border-gray-300 rounded'}),
        label='Demander la création du spot'
    )
    target_audience = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bf1-red focus:border-bf1-red',
            'placeholder': 'Ex: Jeunes adultes 18-35 ans'
        }),
        label='Public cible'
    )
    key_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-bf1-red focus:border-bf1-red',
            'placeholder': 'Message publicitaire principal'
        }),
        label='Message clé'
    )
    spot_title = forms.CharField(
        required=False,
        max_length=200,
        label='Titre du spot',
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Ex: Spot Promotion Été'
        })
    )
    
    spot_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Description du spot (optionnel)...'
        }),
        label='Description du spot'
    )
    
    media_type = forms.ChoiceField(
        required=False,
        choices=[('image', 'Image'), ('video', 'Vidéo')],
        widget=forms.RadioSelect(attrs={
            'class': 'media-type-radio'
        }),
        label='Type de média'
    )
    
    image_file = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'id': 'image-upload',
            'accept': 'image/*'
        }),
        label='Image du spot'
    )
    
    video_file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'id': 'video-upload',
            'accept': 'video/*'
        }),
        label='Vidéo du spot'
    )
    
    duration_seconds = forms.IntegerField(
        required=False,
        min_value=5,
        max_value=300,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Durée en secondes (pour vidéo)'
        }),
        label='Durée (secondes)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        media_type = cleaned_data.get('media_type')
        image_file = cleaned_data.get('image_file')
        video_file = cleaned_data.get('video_file')
        duration_seconds = cleaned_data.get('duration_seconds')
        spot_title = cleaned_data.get('spot_title')
        # Validation des dates
        if start_date and end_date:
            if start_date < timezone.now().date():
                raise forms.ValidationError("La date de début ne peut pas être dans le passé.")
            if end_date <= start_date:
                raise forms.ValidationError("La date de fin doit être après la date de début.")
        # Validation du média: uniquement si l’utilisateur a commencé à remplir la section spot
        if spot_title or image_file or video_file:
            if not spot_title:
                self.add_error('spot_title', "Veuillez saisir le titre du spot.")
            if media_type == 'image':
                if not image_file:
                    self.add_error('image_file', "Veuillez sélectionner une image.")
            elif media_type == 'video':
                if not video_file:
                    self.add_error('video_file', "Veuillez sélectionner une vidéo.")
                if not duration_seconds:
                    self.add_error('duration_seconds', "Veuillez indiquer la durée de la vidéo.")
        # Champs obligatoires côté campagne
        if not cleaned_data.get('objective'):
            self.add_error('objective', "Veuillez sélectionner l’objectif.")
        if not cleaned_data.get('channel'):
            self.add_error('channel', "Veuillez sélectionner le canal.")
        return cleaned_data

    def clean_video_file(self):
        video_file = self.cleaned_data.get('video_file')
        if video_file:
            # Vérifier la taille du fichier (max 100MB)
            if video_file.size > 100 * 1024 * 1024:
                raise forms.ValidationError("Le fichier vidéo ne doit pas dépasser 100MB.")
            
            # Vérifier l'extension
            allowed_extensions = ['mp4', 'avi', 'mov', 'wmv']
            file_extension = video_file.name.split('.')[-1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(f"Format non supporté. Formats acceptés: {', '.join(allowed_extensions)}")
        
        return video_file


class AdvisorWizardForm(forms.Form):
    channel = forms.ChoiceField(choices=[('tv', 'Télévision'), ('urban', 'Écran urbain'), ('online', 'En ligne')], label="Support de diffusion souhaité")
    has_spot_ready = forms.ChoiceField(choices=[('yes', 'Oui'), ('no', 'Non')], widget=forms.RadioSelect, label="Votre spot est-il prêt ?")
    objective = forms.ChoiceField(choices=[('notoriete', 'Notoriété'), ('promotion', 'Promotion'), ('sensibilisation', 'Sensibilisation')], label="Objectif principal")
    budget_estimate = forms.DecimalField(required=False, min_value=0, label="Budget estimé (optionnel)")

class ContactRequestForm(forms.Form):
    name = forms.CharField(max_length=200, label="Nom complet")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(max_length=50, required=False, label="Téléphone")
    subject = forms.CharField(max_length=255, label="Objet")
    message = forms.CharField(widget=forms.Textarea, label="Votre besoin")
    preferred_contact_time = forms.CharField(max_length=100, required=False, label="Préférence de contact")
    # Options détaillées (facultatives) - pour cohérence backend
    campaign_type = forms.ChoiceField(
        required=False,
        choices=[('spot_upload', "Je fournis mon spot"), ('spot_creation', "Je demande la création d'un spot")],
        widget=forms.Select(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600'
        }),
        label='Type de campagne (optionnel)'
    )


class CoverageRequestForm(forms.ModelForm):
    """Formulaire multi-étapes pour la Demande de couverture"""
    # Les pièces jointes sont gérées directement dans la vue via request.FILES.getlist('attachments')

    class Meta:
        model = CoverageRequest
        fields = [
            'event_title', 'event_type', 'event_type_other', 'description',
            'event_date', 'start_time', 'end_time', 'address', 'meeting_point',
            'contact_name', 'contact_phone', 'contact_email', 'other_contacts',
            'coverage_type', 'coverage_objective',
            'urgency_level', 'response_deadline', 'confirm_info'
        ]
        widgets = {
            'event_title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent',
                'placeholder': "Titre de l’événement"
            }),
            'event_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent'
            }),
            'event_type_other': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600',
                'placeholder': 'Précisez le type d’événement'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent',
                'placeholder': 'Décrivez brièvement l’événement et le contexte'
            }),
            'event_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent'
            }),
            'start_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent'
            }),
            'end_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent'
            }),
            'address': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent',
                'placeholder': 'Adresse complète du lieu'
            }),
            'meeting_point': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent',
                'placeholder': 'Point de rendez-vous (optionnel)'
            }),
            'contact_name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent',
                'placeholder': 'Nom et prénom du contact presse'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent',
                'placeholder': 'Téléphone'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent',
                'placeholder': 'Email (optionnel)'
            }),
            'other_contacts': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent',
                'placeholder': 'Autres personnes à contacter (optionnel)'
            }),
            'coverage_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent'
            }),
            'coverage_objective': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent',
                'placeholder': 'Ex: reportage vidéo, article web, interview…'
            }),
            'urgency_level': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent'
            }),
            'response_deadline': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-transparent'
            }),
            'confirm_info': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-blue-600 focus:ring-blue-600 border-gray-300 rounded'
            }),
        }
        labels = {
            'event_title': "Titre de l’événement",
            'event_type': "Type d’événement",
            'event_type_other': "Type d’événement (autre)",
            'description': "Description",
            'event_date': "Date de l’événement",
            'start_time': "Heure de début",
            'end_time': "Heure de fin",
            'address': "Adresse",
            'meeting_point': "Point de rendez-vous",
            'contact_name': "Contact presse",
            'contact_phone': "Téléphone du contact",
            'contact_email': "Email du contact",
            'other_contacts': "Autres contacts",
            'coverage_type': "Type de couverture",
            'coverage_objective': "Objectif de la couverture",
            'urgency_level': "Urgence",
            'response_deadline': "Date limite de réponse",
            'confirm_info': "Confirmation des informations",
        }

    def clean(self):
        cleaned = super().clean()
        # Exiger event_type_other si 'Autre'
        if cleaned.get('event_type') == 'other' and not cleaned.get('event_type_other'):
            self.add_error('event_type_other', "Veuillez préciser le type d’événement.")
        return cleaned

    def clean_confirm_info(self):
        val = self.cleaned_data.get('confirm_info')
        if not val:
            raise forms.ValidationError("Vous devez confirmer l’exactitude des informations.")
        return val
    requested_creation = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-blue-600 focus:ring-blue-600 border-gray-300 rounded'}),
        label='Demander la création de spot'
    )
    target_audience = forms.CharField(
        required=False,
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600',
            'placeholder': 'Ex: Jeunes adultes 18-35 ans'
        }),
        label='Public cible (optionnel)'
    )
    key_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600',
            'placeholder': 'Message publicitaire principal'
        }),
        label='Message clé (optionnel)'
    )
