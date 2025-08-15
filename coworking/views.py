from django.shortcuts import render

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.utils import timezone
from decimal import Decimal
from .models import *
from .forms import *

def accueil(request):
    """Page d'accueil avec aperçu des espaces et événements"""
    espaces = EspaceTravail.objects.filter(disponible=True)[:6]
    evenements = Evenement.objects.filter(date_debut__gte=timezone.now())[:4]
    return render(request, 'coworking/accueil.html', {
        'espaces': espaces,
        'evenements': evenements
    })

def inscription(request):
    """Inscription d'un nouveau membre"""
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        profil_form = ProfilMembreForm(request.POST)
        
        if user_form.is_valid() and profil_form.is_valid():
            user = user_form.save()  # le rôle est déjà assigné automatiquement
            profil = profil_form.save(commit=False)
            profil.user = user
            profil.save()
            login(request, user)
            messages.success(request, 'Inscription réussie ! Bienvenue dans notre espace de coworking.')
            return redirect('dashboard')
    
    else:
        user_form = CustomUserCreationForm()
        profil_form = ProfilMembreForm()
    
    return render(request, 'registration/inscription.html', {
        'user_form': user_form,
        'profil_form': profil_form
    })


@login_required
def dashboard(request):
    """Tableau de bord personnalisé selon le type d'utilisateur"""
    profil = getattr(request.user, 'profilmembre', None)
    
    try:
        role = request.user.roleutilisateur.role
    except RoleUtilisateur.DoesNotExist:
        role = 'membre'
    
    if role == 'gestionnaire':
        # Dashboard gestionnaire
        stats = {
            'membres_total': ProfilMembre.objects.count(),
            'reservations_jour': Reservation.objects.filter(
                date_debut__date=timezone.now().date()
            ).count(),
            'evenements_a_venir': Evenement.objects.filter(
                date_debut__gte=timezone.now()
            ).count(),
            'factures_impayees': Facture.objects.filter(statut='en_attente').count()
        }
        return render(request, 'coworking/dashboard_gestionnaire.html', {'stats': stats})
    else:
        # Dashboard membre
        mes_reservations = Reservation.objects.filter(
            membre=request.user,
            date_debut__gte=timezone.now()
        )[:5]
        mes_evenements = request.user.evenements_participes.filter(
            date_debut__gte=timezone.now()
        )[:3]
        notifications_non_lues = Notification.objects.filter(
            destinataire=request.user,
            lue=False
        ).count()
        
        return render(request, 'coworking/dashboard_membre.html', {
            'profil': profil,
            'mes_reservations': mes_reservations,
            'mes_evenements': mes_evenements,
            'notifications_non_lues': notifications_non_lues
        })


# === VUES ESPACES ===
def liste_espaces(request):
    """Liste des espaces avec recherche et filtre par disponibilité"""
    form = RechercheEspaceForm(request.GET)
    espaces = EspaceTravail.objects.filter(disponible=True)
    
    if form.is_valid():
        type_espace = form.cleaned_data.get('type_espace')
        capacite_min = form.cleaned_data.get('capacite_min')
        date_debut = form.cleaned_data.get('date_debut')
        date_fin = form.cleaned_data.get('date_fin')
        
        if type_espace:
            espaces = espaces.filter(type_espace=type_espace)
        if capacite_min:
            espaces = espaces.filter(capacite__gte=capacite_min)
        if date_debut and date_fin:
            espaces = espaces.exclude(
                reservation__date_debut__lt=date_fin,
                reservation__date_fin__gt=date_debut,
                reservation__statut='confirmee'
            )
    
    return render(request, 'coworking/liste_espaces.html', {
        'espaces': espaces,
        'form': form
    })


def detail_espace(request, espace_id):
    """Détail d'un espace de travail"""
    espace = get_object_or_404(EspaceTravail, id=espace_id)
    reservations_recentes = Reservation.objects.filter(
        espace=espace,
        statut='confirmee',
        date_debut__gte=timezone.now()
    ).order_by('date_debut')[:5]
    
    return render(request, 'coworking/detail_espace.html', {
        'espace': espace,
        'reservations_recentes': reservations_recentes
    })
@login_required
def reserver_espace(request, espace_id=None):
    """Formulaire de réservation"""
    espace = None
    if espace_id:
        espace = get_object_or_404(EspaceTravail, id=espace_id)
    
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.membre = request.user
            
            # Vérifier conflits
            conflits = Reservation.objects.filter(
                espace=reservation.espace,
                statut='confirmee',
                date_debut__lt=reservation.date_fin,
                date_fin__gt=reservation.date_debut
            )
            if conflits.exists():
                messages.error(request, 'Cet espace est déjà réservé pour cette période.')
                return redirect('reserver_espace', espace_id=espace.id if espace else None)
            
            # Calcul du prix
            duree = reservation.date_fin - reservation.date_debut
            heures = duree.total_seconds() / 3600
            reservation.prix_total = Decimal(heures) * reservation.espace.prix_heure
            
            reservation.save()
            messages.success(request, 'Réservation créée avec succès !')
            return redirect('mes_reservations')
    else:
        initial_data = {}
        if espace:
            initial_data['espace'] = espace
        form = ReservationForm(initial=initial_data)
    
    return render(request, 'coworking/reserver_espace.html', {
        'form': form,
        'espace': espace
    })


# === VUES RÉSERVATIONS ===
@login_required
def mes_reservations(request):
    """Liste des réservations du membre connecté"""
    reservations = Reservation.objects.filter(
        membre=request.user
    ).order_by('-date_creation', '-date_debut')
    
    now = timezone.now()
    return render(request, 'coworking/mes_reservations.html', {
        'reservations': reservations,
        'now': now,
    })

@login_required
def annuler_reservation(request, reservation_id):
    """Annuler une réservation"""
    reservation = get_object_or_404(
        Reservation,
        id=reservation_id,
        membre=request.user,
        
    )
    
    if reservation.date_debut > timezone.now():
        reservation.statut = 'annulee'
        reservation.save()
        messages.success(request, 'Réservation annulée avec succès.')
    else:
        messages.error(request, 'Impossible d\'annuler une réservation passée.')
    
    return redirect('mes_reservations')


# === VUES ÉVÉNEMENTS ===
def liste_evenements(request):
    """Liste des événements à venir"""
    evenements = Evenement.objects.filter(
        date_debut__gte=timezone.now()
    ).order_by('date_debut')
    
    return render(request, 'coworking/liste_evenements.html', {
        'evenements': evenements
    })


def detail_evenement(request, evenement_id):
    """Détail d'un événement"""
    evenement = get_object_or_404(Evenement, id=evenement_id)
    inscrit = False
    if request.user.is_authenticated:
        inscrit = Inscription.objects.filter(
            membre=request.user,
            evenement=evenement
        ).exists()
    
    return render(request, 'coworking/detail_evenement.html', {
        'evenement': evenement,
        'inscrit': inscrit
    })

@login_required
def inscription_evenement(request, evenement_id):
    """S'inscrire à un événement"""
    evenement = get_object_or_404(Evenement, id=evenement_id)
    
    if evenement.places_restantes > 0:
        inscription, created = Inscription.objects.get_or_create(
            membre=request.user,
            evenement=evenement
        )
        
        if created:
            messages.success(request, f'Inscription confirmée pour "{evenement.nom}"')
        else:
            messages.info(request, 'Vous êtes déjà inscrit à cet événement.')
    else:
        messages.error(request, 'Aucune place disponible pour cet événement.')
    
    return redirect('detail_evenement', evenement_id=evenement_id)


# === VUES GESTIONNAIRE ===@login_required
def gestion_membres(request):
    """Vue gestionnaire - Liste des membres (staff uniquement)"""
    if not request.user.is_staff:
        messages.error(request, 'Accès non autorisé.')
        return redirect('dashboard')
    
    membres = ProfilMembre.objects.select_related('user').all()
    return render(request, 'coworking/gestion_membres.html', {
        'membres': membres
    })

@login_required
def gestion_reservations(request):
    """Vue gestionnaire - Toutes les réservations"""
    if not request.user.is_staff:
        messages.error(request, 'Accès non autorisé.')
        return redirect('dashboard')
    
    reservations = Reservation.objects.select_related('membre', 'espace').order_by('-date_creation')
    return render(request, 'coworking/gestion_reservations.html', {
        'reservations': reservations
    })
@login_required
def creer_evenement(request):
    """Créer un nouvel événement (gestionnaire)"""
    if not request.user.is_staff:
        messages.error(request, 'Accès non autorisé.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = EvenementForm(request.POST)
        if form.is_valid():
            evenement = form.save(commit=False)
            evenement.organisateur = request.user
            evenement.save()
            messages.success(request, 'Événement créé avec succès !')
            return redirect('gestion_evenements')
    else:
        form = EvenementForm()
    
    return render(request, 'coworking/creer_evenement.html', {'form': form})
@login_required
def gestion_evenements(request):
    """Vue gestionnaire - Liste des événements"""
    if not request.user.is_staff:
        messages.error(request, 'Accès non autorisé.')
        return redirect('dashboard')
    
    evenements = Evenement.objects.annotate(
        nb_participants=Count('participants')
    ).order_by('date_debut')
    
    return render(request, 'coworking/gestion_evenements.html', {
        'evenements': evenements
    })

# === API AJAX ===
@login_required
def api_notifications(request):
    """API pour récupérer les notifications non lues"""
    notifications = Notification.objects.filter(
        destinataire=request.user,
        lue=False
    ).values('id', 'titre', 'message', 'type_notification', 'date_creation')
    
    return JsonResponse(list(notifications), safe=False)

@login_required
def marquer_notification_lue(request, notification_id):
    """Marquer une notification comme lue"""
    if request.method == 'POST':
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            destinataire=request.user
        )
        notification.lue = True
        notification.save()
        return JsonResponse({'success': True})
    
    return JsonResponse({'success': False})




from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.shortcuts import render, redirect

def connexion(request):
    form = AuthenticationForm(request, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, "Connexion réussie.")
                return redirect('accueil')  # Mets la page d'accueil de ton app
            else:
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")

    return render(request, 'registration/login.html', {'form': form})










#LES VUES D'ADMINISTRATEUR 

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from .models import *
from .forms import *

def est_gestionnaire(user):
    """Vérifie si l'utilisateur est un gestionnaire"""
    try:
        return user.roleutilisateur.role == 'gestionnaire'
    except:
        return False

@login_required
@user_passes_test(est_gestionnaire)
def dashboard_admin(request):
    """Dashboard principal pour les administrateurs"""
    # Statistiques générales
    total_membres = User.objects.filter(roleutilisateur__role='membre').count()
    total_espaces = EspaceTravail.objects.count()
    reservations_aujourd_hui = Reservation.objects.filter(
        date_debut__date=timezone.now().date(),
        statut='confirmee'
    ).count()
    
    # Revenus du mois
    debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenus_mois = Facture.objects.filter(
        date_creation__gte=debut_mois,
        statut='payee'
    ).aggregate(total=Sum('montant_total'))['total'] or 0
    
    # Réservations récentes
    reservations_recentes = Reservation.objects.select_related(
        'membre', 'espace'
    ).order_by('-date_creation')[:5]
    
    # Factures en attente
    factures_en_attente = Facture.objects.filter(
        statut='en_attente'
    ).count()
    
    # Événements à venir
    evenements_a_venir = Evenement.objects.filter(
        date_debut__gte=timezone.now()
    ).order_by('date_debut')[:3]
    
    context = {
        'total_membres': total_membres,
        'total_espaces': total_espaces,
        'reservations_aujourd_hui': reservations_aujourd_hui,
        'revenus_mois': revenus_mois,
        'reservations_recentes': reservations_recentes,
        'factures_en_attente': factures_en_attente,
        'evenements_a_venir': evenements_a_venir,
    }
    
    return render(request, 'admin/dashboard_admin.html', context)

# ============== GESTION DES MEMBRES ==============

@login_required
@user_passes_test(est_gestionnaire)
def liste_membres_admin(request):
    """Liste tous les membres avec filtres"""
    membres = User.objects.filter(roleutilisateur__role='membre').select_related('profilmembre')
    
    # Filtres
    recherche = request.GET.get('recherche')
    type_abonnement = request.GET.get('type_abonnement')
    
    if recherche:
        membres = membres.filter(
            Q(username__icontains=recherche) |
            Q(first_name__icontains=recherche) |
            Q(last_name__icontains=recherche) |
            Q(email__icontains=recherche)
        )
    
    if type_abonnement:
        membres = membres.filter(profilmembre__type_abonnement=type_abonnement)
    
    context = {
        'membres': membres,
        'types_abonnement': ProfilMembre.TYPES_ABONNEMENT,
    }
    
    return render(request, 'admin/membres/liste_membres.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def detail_membre_admin(request, membre_id):
    """Détail d'un membre avec ses statistiques"""
    membre = get_object_or_404(User, id=membre_id, roleutilisateur__role='membre')
    
    # Statistiques du membre
    total_reservations = Reservation.objects.filter(membre=membre).count()
    reservations_confirmees = Reservation.objects.filter(
        membre=membre, statut='confirmee'
    ).count()
    
    # Dernières réservations
    dernieres_reservations = Reservation.objects.filter(
        membre=membre
    ).select_related('espace').order_by('-date_creation')[:5]
    
    # Factures
    factures = Facture.objects.filter(membre=membre).order_by('-date_creation')[:5]
    
    # Événements participés
    evenements = membre.evenements_participes.all()[:5]
    
    context = {
        'membre': membre,
        'total_reservations': total_reservations,
        'reservations_confirmees': reservations_confirmees,
        'dernieres_reservations': dernieres_reservations,
        'factures': factures,
        'evenements': evenements,
    }
    
    return render(request, 'admin/membres/detail_membre.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def creer_membre_admin(request):
    """Création d'un nouveau membre par l'admin"""
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        profil_form = ProfilMembreForm(request.POST)
        
        if user_form.is_valid() and profil_form.is_valid():
            user = user_form.save()
            profil = profil_form.save(commit=False)
            profil.user = user
            profil.save()
            
            messages.success(request, f'Membre {user.get_full_name()} créé avec succès.')
            return redirect('liste_membres_admin')
    else:
        user_form = CustomUserCreationForm()
        profil_form = ProfilMembreForm()
    
    context = {
        'user_form': user_form,
        'profil_form': profil_form,
        'action': 'Créer'
    }
    
    return render(request, 'admin/membres/form_membre.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def modifier_membre_admin(request, membre_id):
    """Modification d'un membre"""
    membre = get_object_or_404(User, id=membre_id, roleutilisateur__role='membre')
    
    if request.method == 'POST':
        # Formulaire utilisateur (sans mot de passe)
        membre.username = request.POST.get('username')
        membre.first_name = request.POST.get('first_name')
        membre.last_name = request.POST.get('last_name')
        membre.email = request.POST.get('email')
        membre.save()
        
        # Profil membre
        profil_form = ProfilMembreForm(request.POST, instance=membre.profilmembre)
        if profil_form.is_valid():
            profil_form.save()
            messages.success(request, f'Membre {membre.get_full_name()} modifié avec succès.')
            return redirect('detail_membre_admin', membre_id=membre.id)
    else:
        profil_form = ProfilMembreForm(instance=membre.profilmembre)
    
    context = {
        'membre': membre,
        'profil_form': profil_form,
        'action': 'Modifier'
    }
    
    return render(request, 'admin/membres/modifier_membre.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def supprimer_membre_admin(request, membre_id):
    """Suppression d'un membre"""
    membre = get_object_or_404(User, id=membre_id, roleutilisateur__role='membre')
    
    if request.method == 'POST':
        nom_membre = membre.get_full_name()
        membre.delete()
        messages.success(request, f'Membre {nom_membre} supprimé avec succès.')
        return redirect('liste_membres_admin')
    
    context = {'membre': membre}
    return render(request, 'admin/membres/supprimer_membre.html', context)

# ============== GESTION DES ESPACES ==============

@login_required
@user_passes_test(est_gestionnaire)
def liste_espaces_admin(request):
    """Liste tous les espaces de travail"""
    espaces = EspaceTravail.objects.select_related('type_espace').all()
    
    # Filtres
    type_espace = request.GET.get('type_espace')
    disponible = request.GET.get('disponible')
    
    if type_espace:
        espaces = espaces.filter(type_espace_id=type_espace)
    
    if disponible:
        espaces = espaces.filter(disponible=disponible == 'True')
    
    types_espaces = TypeEspace.objects.all()
    
    context = {
        'espaces': espaces,
        'types_espaces': types_espaces,
    }
    
    return render(request, 'admin/espaces/liste_espaces.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def detail_espace_admin(request, espace_id):
    """Détail d'un espace de travail"""
    espace = get_object_or_404(EspaceTravail, id=espace_id)
    
    # Réservations récentes pour cet espace
    reservations_recentes = Reservation.objects.filter(
        espace=espace
    ).select_related('membre').order_by('-date_creation')[:10]
    
    # Statistiques
    total_reservations = Reservation.objects.filter(espace=espace).count()
    reservations_mois = Reservation.objects.filter(
        espace=espace,
        date_creation__month=timezone.now().month
    ).count()
    
    context = {
        'espace': espace,
        'reservations_recentes': reservations_recentes,
        'total_reservations': total_reservations,
        'reservations_mois': reservations_mois,
    }
    
    return render(request, 'admin/espaces/detail_espace.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def creer_espace_admin(request):
    """Création d'un nouvel espace de travail"""
    if request.method == 'POST':
        form = EspaceTravailForm(request.POST)
        if form.is_valid():
            espace = form.save()
            messages.success(request, f'Espace "{espace.nom}" créé avec succès.')
            return redirect('liste_espaces_admin')
    else:
        form = EspaceTravailForm()
    
    context = {
        'form': form,
        'action': 'Créer'
    }
    
    return render(request, 'admin/espaces/form_espace.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def modifier_espace_admin(request, espace_id):
    """Modification d'un espace de travail"""
    espace = get_object_or_404(EspaceTravail, id=espace_id)
    
    if request.method == 'POST':
        form = EspaceTravailForm(request.POST, instance=espace)
        if form.is_valid():
            form.save()
            messages.success(request, f'Espace "{espace.nom}" modifié avec succès.')
            return redirect('detail_espace_admin', espace_id=espace.id)
    else:
        form = EspaceTravailForm(instance=espace)
    
    context = {
        'form': form,
        'espace': espace,
        'action': 'Modifier'
    }
    
    return render(request, 'admin/espaces/form_espace.html', context)

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404
from .models import EspaceTravail

@csrf_exempt
def supprimer_espace_admin(request, espace_id):
    if request.method == 'POST':
        espace = get_object_or_404(EspaceTravail, id=espace_id)
        try:
            espace.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


# ============== GESTION DES TYPES D'ESPACES ==============

@login_required
@user_passes_test(est_gestionnaire)
def liste_types_espaces_admin(request):
    """Liste tous les types d'espaces"""
    types_espaces = TypeEspace.objects.annotate(
        nb_espaces=Count('espacetravail')
    ).all()
    
    context = {'types_espaces': types_espaces}
    return render(request, 'admin/types_espaces/liste_types.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def creer_type_espace_admin(request):
    """Création d'un nouveau type d'espace"""
    if request.method == 'POST':
        form = TypeEspaceForm(request.POST)
        if form.is_valid():
            type_espace = form.save()
            messages.success(request, f'Type d\'espace "{type_espace.nom}" créé avec succès.')
            return redirect('liste_types_espaces_admin')
    else:
        form = TypeEspaceForm()
    
    context = {
        'form': form,
        'action': 'Créer'
    }
    
    return render(request, 'admin/types_espaces/form_type.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def modifier_type_espace_admin(request, type_id):
    """Modification d'un type d'espace"""
    type_espace = get_object_or_404(TypeEspace, id=type_id)
    
    if request.method == 'POST':
        form = TypeEspaceForm(request.POST, instance=type_espace)
        if form.is_valid():
            form.save()
            messages.success(request, f'Type d\'espace "{type_espace.nom}" modifié avec succès.')
            return redirect('liste_types_espaces_admin')
    else:
        form = TypeEspaceForm(instance=type_espace)
    
    context = {
        'form': form,
        'type_espace': type_espace,
        'action': 'Modifier'
    }
    
    return render(request, 'admin/types_espaces/form_type.html', context)

from django.views.decorators.http import require_POST
@require_POST
def supprimer_type_espace_admin(request, type_id):
    from .models import TypeEspace
    type_espace = get_object_or_404(TypeEspace, id=type_id)
    try:
        type_espace.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
    
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from .models import TypeEspace

@require_POST
def supprimer_type_espace_admin(request, type_id):
    type_espace = get_object_or_404(TypeEspace, id=type_id)
    try:
        type_espace.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})



# ============== GESTION DES RÉSERVATIONS ==============

@login_required
@user_passes_test(est_gestionnaire)
def liste_reservations_admin(request):
    """Liste toutes les réservations avec filtres"""
    reservations = Reservation.objects.select_related(
        'membre', 'espace'
    ).order_by('-date_creation')
    
    # Filtres
    statut = request.GET.get('statut')
    espace = request.GET.get('espace')
    date_debut = request.GET.get('date_debut')
    
    if statut:
        reservations = reservations.filter(statut=statut)
    
    if espace:
        reservations = reservations.filter(espace_id=espace)
    
    if date_debut:
        reservations = reservations.filter(date_debut__date=date_debut)
    
    # Pagination simple
    reservations = reservations[:50]  # Limiter à 50 résultats
    
    espaces = EspaceTravail.objects.all()
    
    context = {
        'reservations': reservations,
        'espaces': espaces,
        'statuts': Reservation.STATUTS,
    }
    
    return render(request, 'admin/reservations/liste_reservations.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def detail_reservation_admin(request, reservation_id):
    """Détail d'une réservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    context = {'reservation': reservation}
    return render(request, 'admin/reservations/detail_reservation.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def modifier_statut_reservation(request, reservation_id):
    """Modification du statut d'une réservation"""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    
    if request.method == 'POST':
        nouveau_statut = request.POST.get('statut')
        if nouveau_statut in [choice[0] for choice in Reservation.STATUTS]:
            ancien_statut = reservation.statut
            reservation.statut = nouveau_statut
            reservation.save()
            
            # Créer historique
            HistoriqueReservation.objects.create(
                reservation=reservation,
                action=f'Statut changé de "{ancien_statut}" à "{nouveau_statut}"'
            )
            
            messages.success(request, f'Statut de la réservation modifié avec succès.')
            
            # Envoyer notification au membre
            Notification.objects.create(
                destinataire=reservation.membre,
                titre=f'Réservation {reservation.statut}',
                message=f'Votre réservation du {reservation.date_debut.strftime("%d/%m/%Y")} a été {reservation.get_statut_display().lower()}.',
                type_notification='reservation'
            )
            
        return redirect('detail_reservation_admin', reservation_id=reservation.id)
    
    context = {
        'reservation': reservation,
        'statuts': Reservation.STATUTS
    }
    
    return render(request, 'admin/reservations/modifier_statut.html', context)

# ============== GESTION DES ÉVÉNEMENTS ==============

@login_required
@user_passes_test(est_gestionnaire)
def liste_evenements_admin(request):
    """Liste tous les événements"""
    evenements = Evenement.objects.select_related('organisateur').annotate(
        nb_participants=Count('participants')
    ).order_by('-date_debut')
    
    context = {'evenements': evenements}
    return render(request, 'admin/evenements/liste_evenements.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def detail_evenement_admin(request, evenement_id):
    """Détail d'un événement"""
    evenement = get_object_or_404(Evenement, id=evenement_id)
    participants = evenement.participants.all()
    
    context = {
        'evenement': evenement,
        'participants': participants,
    }
    
    return render(request, 'admin/evenements/detail_evenement.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def creer_evenement_admin(request):
    """Création d'un nouvel événement"""
    if request.method == 'POST':
        form = EvenementForm(request.POST)
        if form.is_valid():
            evenement = form.save(commit=False)
            evenement.organisateur = request.user
            evenement.save()
            messages.success(request, f'Événement "{evenement.nom}" créé avec succès.')
            return redirect('liste_evenements_admin')
    else:
        form = EvenementForm()
    
    context = {
        'form': form,
        'action': 'Créer'
    }
    
    return render(request, 'admin/evenements/form_evenement.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def modifier_evenement_admin(request, evenement_id):
    """Modification d'un événement"""
    evenement = get_object_or_404(Evenement, id=evenement_id)
    
    if request.method == 'POST':
        form = EvenementForm(request.POST, instance=evenement)
        if form.is_valid():
            form.save()
            messages.success(request, f'Événement "{evenement.nom}" modifié avec succès.')
            return redirect('detail_evenement_admin', evenement_id=evenement.id)
    else:
        form = EvenementForm(instance=evenement)
    
    context = {
        'form': form,
        'evenement': evenement,
        'action': 'Modifier'
    }
    
    return render(request, 'admin/evenements/form_evenement.html', context)

# ============== GESTION DES FACTURES ==============

@login_required
@user_passes_test(est_gestionnaire)
def liste_factures_admin(request):
    """Liste toutes les factures"""
    factures = Facture.objects.select_related('membre').order_by('-date_creation')
    
    # Filtres
    statut = request.GET.get('statut')
    if statut:
        factures = factures.filter(statut=statut)
    
    context = {
        'factures': factures,
        'statuts': Facture.STATUTS_FACTURE,
    }
    
    return render(request, 'admin/factures/liste_factures.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def detail_facture_admin(request, facture_id):
    """Détail d'une facture"""
    facture = get_object_or_404(Facture, id=facture_id)
    
    context = {'facture': facture}
    return render(request, 'admin/factures/detail_facture.html', context)

@login_required
@user_passes_test(est_gestionnaire)
def creer_facture_admin(request):
    """Création d'une nouvelle facture"""
    if request.method == 'POST':
        form = FactureForm(request.POST)
        if form.is_valid():
            facture = form.save(commit=False)
            # Générer numéro unique
            facture.numero = f"FAC-{timezone.now().strftime('%Y%m%d')}-{Facture.objects.count() + 1:04d}"
            facture.save()
            messages.success(request, f'Facture {facture.numero} créée avec succès.')
            return redirect('liste_factures_admin')
    else:
        form = FactureForm()
    
    context = {
        'form': form,
        'action': 'Créer'
    }
    
    return render(request, 'admin/factures/form_facture.html', context)

# ============== GESTION DES NOTIFICATIONS ==============

@login_required
@user_passes_test(est_gestionnaire)
def envoyer_notification_admin(request):
    """Envoi de notifications aux membres"""
    if request.method == 'POST':
        form = NotificationForm(request.POST)
        if form.is_valid():
            destinataires = form.cleaned_data.get('destinataires_multiples')
            
            if not destinataires:
                # Envoyer à tous les membres
                destinataires = User.objects.filter(roleutilisateur__role='membre')
            
            for user in destinataires:
                Notification.objects.create(
                    destinataire=user,
                    titre=form.cleaned_data['titre'],
                    message=form.cleaned_data['message'],
                    type_notification=form.cleaned_data['type_notification']
                )
            
            messages.success(request, f'Notification envoyée à {destinataires.count()} membre(s).')
            return redirect('dashboard_admin')
    else:
        form = NotificationForm()
    
    context = {'form': form}
    return render(request, 'admin/notifications/form_notification.html', context)




# Tarifs des abonnements
ABONNEMENTS = {
    'jour': {
        'name': 'Abonnement Journalier',
        'price': '25€ / jour',
        'description': 'Accès complet pour une journée de travail'
    },
    'semaine': {
        'name': 'Abonnement Hebdomadaire',
        'price': '120€ / semaine',
        'description': 'Accès illimité pendant 7 jours consécutifs'
    },
    'mois': {
        'name': 'Abonnement Mensuel',
        'price': '350€ / mois',
        'description': 'Accès complet pendant 30 jours + avantages premium'
    },
    'annuel': {
        'name': 'Abonnement Annuel',
        'price': '3200€ / an',
        'description': 'Économisez 25% avec notre forfait annuel + tous les avantages'
    }
}

@login_required
def choisir_paiement(request):
    """
    Page où l'utilisateur choisit de payer sa réservation ou son abonnement.
    """
    reservations = Reservation.objects.filter(membre=request.user, statut='en_attente')
    profil = get_object_or_404(ProfilMembre, user=request.user)
    return render(request, 'paiement/choisir.html', {
        'reservations': reservations,
        'profil': profil,
        'abon_prices': ABONNEMENTS
    })

@login_required
def page_paiement(request):
    """
    Simule une page PayPal selon le type choisi.
    On récupère le paramètre GET: ?type=reservation&id=xx ou ?type=abonnement
    """
    type_paiement = request.GET.get('type')
    context = {}

    if type_paiement == 'reservation':
        reservation_id = request.GET.get('id')
        reservation = get_object_or_404(Reservation, id=reservation_id, membre=request.user)
        context['objet'] = 'Réservation'
        context['nom'] = reservation.espace.nom
        context['montant'] = reservation.prix_total
    elif type_paiement == 'abonnement':
        profil = get_object_or_404(ProfilMembre, user=request.user)
        abonnement = ABONNEMENTS.get(profil.type_abonnement)
        context['objet'] = 'Abonnement'
        context['nom'] = abonnement['name']
        context['montant'] = abonnement['price']
        context['description'] = abonnement['description']
    else:
        context['objet'] = 'Inconnu'
        context['nom'] = 'Aucun'
        context['montant'] = '0€'

    return render(request, 'paiement/page_paiement.html', context)










def deconnexion(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté.")
    return redirect('login')
