from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import *

urlpatterns = [
    # Pages principales
    path('', views.accueil, name='accueil'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Authentification
    path('login/', views.connexion, name='login'),
    path('logout/', views.deconnexion, name='logout'),
    path('inscription/', views.inscription, name='inscription'),
    
    # Gestion des espaces
    path('espaces/', views.liste_espaces, name='liste_espaces'),
    path('espaces/<int:espace_id>/', views.detail_espace, name='detail_espace'),
    path('reserver/', views.reserver_espace, name='reserver_espace'),
    path('reserver/<int:espace_id>/', views.reserver_espace, name='reserver_espace_direct'),
    
    # Gestion des réservations
    path('mes-reservations/', views.mes_reservations, name='mes_reservations'),
    path('reservation/<int:reservation_id>/annuler/', views.annuler_reservation, name='annuler_reservation'),
    
    # Gestion des événements
    path('evenements/', views.liste_evenements, name='liste_evenements'),
    path('evenements/<int:evenement_id>/', views.detail_evenement, name='detail_evenement'),
    path('evenements/<int:evenement_id>/inscription/', views.inscription_evenement, name='inscription_evenement'),
    
  
    # API AJAX
    path('api/notifications/', views.api_notifications, name='api_notifications'),
    path('api/notifications/<int:notification_id>/lue/', views.marquer_notification_lue, name='marquer_notification_lue'),



  
    # === Admin personnalisé / Gestionnaire ===
    # Préfixe : gestion/

    # Dashboard admin
    
    path('gestion/dashboard/', dashboard_admin, name='dashboard_admin'),

    # Gestion des membres
    path('gestion/membres/', liste_membres_admin, name='liste_membres_admin'),
    path('gestion/membres/creer/', creer_membre_admin, name='creer_membre_admin'),
    path('gestion/membres/<int:membre_id>/', detail_membre_admin, name='detail_membre_admin'),
    path('gestion/membres/<int:membre_id>/modifier/', modifier_membre_admin, name='modifier_membre_admin'),
    path('gestion/membres/<int:membre_id>/supprimer/', supprimer_membre_admin, name='supprimer_membre_admin'),

    # Gestion des espaces
    path('gestion/espaces/', liste_espaces_admin, name='liste_espaces_admin'),
    path('gestion/espaces/creer/', creer_espace_admin, name='creer_espace_admin'),
    path('gestion/espaces/<int:espace_id>/', detail_espace_admin, name='detail_espace_admin'),
    path('gestion/espaces/<int:espace_id>/modifier/', modifier_espace_admin, name='modifier_espace_admin'),
    path('gestion/espaces/<int:espace_id>/supprimer/', supprimer_espace_admin, name='supprimer_espace_admin'),

    # Gestion des types d'espaces
    path('gestion/types-espaces/', liste_types_espaces_admin, name='liste_types_espaces_admin'),
    path('gestion/types-espaces/creer/', creer_type_espace_admin, name='creer_type_espace_admin'),
    path('gestion/types-espaces/<int:type_id>/modifier/', modifier_type_espace_admin, name='modifier_type_espace_admin'),
    path('gestion/types-espaces/supprimer/<int:type_id>/', supprimer_type_espace_admin, name='supprimer_type_espace_admin'),

    
    # Gestion des réservations
    path('gestion/reservations/', liste_reservations_admin, name='liste_reservations_admin'),
    path('gestion/reservations/<int:reservation_id>/', detail_reservation_admin, name='detail_reservation_admin'),
    path('gestion/reservations/<int:reservation_id>/statut/', modifier_statut_reservation, name='modifier_statut_reservation_admin'),

    # Gestion des événements
    path('gestion/evenements/', liste_evenements_admin, name='liste_evenements_admin'),
    path('gestion/evenements/creer/', creer_evenement_admin, name='creer_evenement_admin'),
    path('gestion/evenements/<int:evenement_id>/', detail_evenement_admin, name='detail_evenement_admin'),
    path('gestion/evenements/<int:evenement_id>/modifier/', modifier_evenement_admin, name='modifier_evenement_admin'),

    # Gestion des factures
    path('gestion/factures/', liste_factures_admin, name='liste_factures_admin'),
    path('gestion/factures/creer/', creer_facture_admin, name='creer_facture_admin'),
    path('gestion/factures/<int:facture_id>/', detail_facture_admin, name='detail_facture_admin'),

    # Notifications admin
    path('gestion/notifications/envoyer/', envoyer_notification_admin, name='envoyer_notification_admin'),

    path('paiement/', views.choisir_paiement, name='choisir_paiement'),
    path('paiement/page/', views.page_paiement, name='page_paiement'),


]