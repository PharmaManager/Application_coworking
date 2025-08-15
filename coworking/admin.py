from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import (
    TypeEspace, EspaceTravail, ProfilMembre, Reservation,
    Evenement, Inscription, Facture, Notification,
    HistoriqueReservation, HistoriquePaiement, RoleUtilisateur
)

# -------------------
# TypeEspace
# -------------------
@admin.register(TypeEspace)
class TypeEspaceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'description')
    search_fields = ('nom',)

# -------------------
# EspaceTravail
# -------------------
@admin.register(EspaceTravail)
class EspaceTravailAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type_espace', 'capacite', 'prix_heure', 'disponible')
    list_filter = ('type_espace', 'disponible')
    search_fields = ('nom', 'equipements')

# -------------------
# ProfilMembre
# -------------------
@admin.register(ProfilMembre)
class ProfilMembreAdmin(admin.ModelAdmin):
    list_display = ('user', 'telephone', 'entreprise', 'type_abonnement', 'abonnement_actif', 'date_adhesion')
    list_filter = ('type_abonnement', 'abonnement_actif')
    search_fields = ('user__username', 'entreprise', 'telephone')

# -------------------
# Reservation
# -------------------
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('membre', 'espace', 'date_debut', 'date_fin', 'statut', 'prix_total', 'date_creation')
    list_filter = ('statut', 'espace')
    search_fields = ('membre__username', 'espace__nom')

# -------------------
# Evenement
# -------------------
@admin.register(Evenement)
class EvenementAdmin(admin.ModelAdmin):
    list_display = ('nom', 'date_debut', 'date_fin', 'lieu', 'prix', 'places_max', 'organisateur')
    search_fields = ('nom', 'lieu', 'organisateur__username')

# -------------------
# Inscription
# -------------------
@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ('membre', 'evenement', 'date_inscription', 'presente')
    list_filter = ('presente',)
    search_fields = ('membre__username', 'evenement__nom')

# -------------------
# Facture
# -------------------
@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ('numero', 'membre', 'date_creation', 'date_echeance', 'montant_total', 'statut', 'reservation')
    list_filter = ('statut',)
    search_fields = ('numero', 'membre__username')

# -------------------
# Notification
# -------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'destinataire', 'type_notification', 'date_creation', 'lue')
    list_filter = ('type_notification', 'lue')
    search_fields = ('titre', 'destinataire__username')

# -------------------
# HistoriqueReservation
# -------------------
@admin.register(HistoriqueReservation)
class HistoriqueReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'action', 'date_action')
    search_fields = ('reservation__membre__username', 'action')

# -------------------
# HistoriquePaiement
# -------------------
@admin.register(HistoriquePaiement)
class HistoriquePaiementAdmin(admin.ModelAdmin):
    list_display = ('facture', 'date_paiement', 'montant')
    search_fields = ('facture__numero',)

# -------------------
# RoleUtilisateur
# -------------------
@admin.register(RoleUtilisateur)
class RoleUtilisateurAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username',)
