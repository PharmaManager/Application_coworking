from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import *
from datetime import timedelta

from django.core.exceptions import ValidationError

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    # facultatif : visible seulement si include_role=True
    role = forms.ChoiceField(
        choices=[('membre', 'Membre'), ('gestionnaire', 'Gestionnaire')],
        required=False
    )

    class Meta:
        model = User
        # NE PAS mettre "role" ici
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, include_role=False, fixed_role=None, **kwargs):
        """
        include_role=False : le champ 'role' n'est pas visible (cas public)
        fixed_role='membre' : force la valeur côté serveur (sécurisé)
        """
        super().__init__(*args, **kwargs)
        self.include_role = include_role
        self.fixed_role = fixed_role

        if not self.include_role:
            # On retire complètement le champ : impossible de le poster côté public
            self.fields.pop('role', None)

    def clean_email(self):
        # Optionnel : s'assurer que l'email est unique si tu l'exiges
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Cet e-mail est déjà utilisé.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()

            # Déterminer la valeur du rôle
            if self.fixed_role is not None:
                # Cas public : on force 'membre' (ou ce que tu passes)
                role_value = self.fixed_role
            elif self.include_role:
                # Cas admin : on respecte le choix fait dans le formulaire
                role_value = self.cleaned_data.get('role') or 'membre'
            else:
                # Fallback (ne devrait pas arriver si fixed_role est passé côté public)
                role_value = 'membre'

            RoleUtilisateur.objects.create(user=user, role=role_value)

        return user



class ProfilMembreForm(forms.ModelForm):
    class Meta:
        model = ProfilMembre
        fields = ['telephone', 'entreprise', 'type_abonnement']
        widgets = {
            'telephone': forms.TextInput(attrs={'placeholder': '+33 1 23 45 67 89'}),
            'entreprise': forms.TextInput(attrs={'placeholder': 'Nom de votre entreprise'}),
        }

    def save(self, commit=True):
        profil = super().save(commit=False)
        now = timezone.now()
        if self.cleaned_data['type_abonnement'] == 'jour':
            profil.date_adhesion = now
        elif self.cleaned_data['type_abonnement'] == 'semaine':
            profil.date_adhesion = now
        elif self.cleaned_data['type_abonnement'] == 'mois':
            profil.date_adhesion = now
        elif self.cleaned_data['type_abonnement'] == 'annuel':
            profil.date_adhesion = now
        if commit:
            profil.save()
        return profil


class ReservationForm(forms.ModelForm):
    
    date_debut = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'step': 60}),
        required=True,
        label="Date et heure de début",
    )
    date_fin = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'step': 60}),
        required=True,
        label="Date et heure de fin",
    )
    class Meta:
        model = Reservation
        fields = ['espace', 'date_debut', 'date_fin']
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['espace'].queryset = EspaceTravail.objects.filter(disponible=True)
       

    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin:
            # 1) Si la date de fin est identique ou avant la date de début
            if date_fin <= date_debut:
                if date_fin == date_debut:
                    self.add_error('date_fin', "L'heure de fin ne peut pas être identique à l'heure de début.")
                else:
                    self.add_error('date_fin', "L'heure de fin doit être après l'heure de début.")
                    
            # 2) Si la durée est inférieure à 1 heure
            elif date_fin - date_debut < timedelta(hours=1):
                minutes_diff = int((date_fin - date_debut).total_seconds() // 60)
                self.add_error(
                    'date_fin',
                    f"La réservation doit durer au moins 1 heure (durée actuelle : {minutes_diff} minutes)."
                )

            
            # Vérifier les conflits de réservation
            espace = cleaned_data.get('espace')
            if espace:
                conflits = Reservation.objects.filter(
                    espace=espace,
                    statut='confirmee',
                    date_debut__lt=date_fin,
                    date_fin__gt=date_debut
                )
                if self.instance.pk:
                    conflits = conflits.exclude(pk=self.instance.pk)
                
                if conflits.exists():
                    raise forms.ValidationError("Cet espace est déjà réservé pour cette période")
        
        return cleaned_data

class EvenementForm(forms.ModelForm):
    class Meta:
        model = Evenement
        fields = ['nom', 'description', 'date_debut', 'date_fin', 'lieu', 'prix', 'places_max']
        widgets = {
            'date_debut': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'date_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if date_debut and date_fin and date_fin <= date_debut:
            raise forms.ValidationError("La date de fin doit être après la date de début")
        
        return cleaned_data

class EspaceTravailForm(forms.ModelForm):
    class Meta:
        model = EspaceTravail
        fields = ['nom', 'type_espace', 'capacite', 'prix_heure', 'equipements', 'disponible']
        widgets = {
            'equipements': forms.Textarea(attrs={'rows': 3, 'placeholder': 'WiFi, Écran, Tableau blanc...'}),
        }

class TypeEspaceForm(forms.ModelForm):
    class Meta:
        model = TypeEspace
        fields = ['nom', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class FactureForm(forms.ModelForm):
    class Meta:
        model = Facture
        fields = ['membre', 'date_echeance', 'montant_total', 'statut']
        widgets = {
            'date_echeance': forms.DateInput(attrs={'type': 'date'}),
        }

class NotificationForm(forms.ModelForm):
    destinataires_multiples = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Destinataires (optionnel - sinon tous les membres)"
    )
    
    class Meta:
        model = Notification
        fields = ['titre', 'message', 'type_notification']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4}),
        }
        
    def save(self, commit=True):
        destinataires = self.cleaned_data.get('destinataires_multiples')
        for user in destinataires:
            Notification.objects.create(
                destinataire=user,
                titre=self.cleaned_data['titre'],
                message=self.cleaned_data['message'],
                type_notification=self.cleaned_data['type_notification']
            )


class RechercheEspaceForm(forms.Form):
    date_debut = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    date_fin = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    type_espace = forms.ModelChoiceField(
        queryset=TypeEspace.objects.all(),
        required=False,
        empty_label="Tous les types"
    )
    capacite_min = forms.IntegerField(
        min_value=1,
        required=False,
        label="Capacité minimale"
    )