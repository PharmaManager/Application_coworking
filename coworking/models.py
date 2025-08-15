from django.db import models
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class TypeEspace(models.Model):
    nom = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.nom

class EspaceTravail(models.Model):
    nom = models.CharField(max_length=100)
    type_espace = models.ForeignKey(TypeEspace, on_delete=models.CASCADE)
    capacite = models.IntegerField()
    prix_heure = models.DecimalField(max_digits=6, decimal_places=2)
    equipements = models.TextField(blank=True)
    disponible = models.BooleanField(default=True)
    
    
    def est_disponible(self, date_debut, date_fin):
        return not Reservation.objects.filter(
            espace=self,
            statut='confirmee',
            date_debut__lt=date_fin,
            date_fin__gt=date_debut
        ).exists()
        
    def __str__(self):
        return self.nom

class ProfilMembre(models.Model):
    TYPES_ABONNEMENT = [
        ('jour', 'Journalier'),
        ('semaine', 'Hebdomadaire'),
        ('mois', 'Mensuel'),
        ('annuel', 'Annuel'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telephone = models.CharField(max_length=15, blank=True)
    entreprise = models.CharField(max_length=100, blank=True)
    type_abonnement = models.CharField(max_length=10, choices=TYPES_ABONNEMENT, default='jour')
    date_adhesion = models.DateTimeField(default=timezone.now)
    abonnement_actif = models.BooleanField(default=True)
    
    
    def abonnement_valide(self):
        return self.abonnement_actif and self.date_adhesion <= timezone.now()
    
    def __str__(self):
        return f"{self.user.username} - {self.get_type_abonnement_display()}"

class Reservation(models.Model):
    STATUTS = [
        ('confirmee', 'Confirmée'),
        ('en_attente', 'En attente'),
        ('annulee', 'Annulée'),
    ]
    
    membre = models.ForeignKey(User, on_delete=models.CASCADE)
    espace = models.ForeignKey(EspaceTravail, on_delete=models.CASCADE)
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    statut = models.CharField(max_length=15, choices=STATUTS, default='en_attente')
    prix_total = models.DecimalField(max_digits=8, decimal_places=2)
    date_creation = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.membre.username} - {self.espace.nom} - {self.date_debut.strftime('%d/%m/%Y')}"

class Evenement(models.Model):
    nom = models.CharField(max_length=100)
    description = models.TextField()
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    lieu = models.CharField(max_length=100)
    prix = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    places_max = models.IntegerField()
    organisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evenements_organises')
    participants = models.ManyToManyField(User, through='Inscription', related_name='evenements_participes')
    
    def __str__(self):
        return self.nom
    
    @property
    def places_restantes(self):
        return self.places_max - self.participants.count()

class Inscription(models.Model):
    membre = models.ForeignKey(User, on_delete=models.CASCADE)
    evenement = models.ForeignKey(Evenement, on_delete=models.CASCADE)
    date_inscription = models.DateTimeField(default=timezone.now)
    presente = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['membre', 'evenement']

class Facture(models.Model):
    STATUTS_FACTURE = [
        ('en_attente', 'En attente'),
        ('payee', 'Payée'),
        ('en_retard', 'En retard'),
        ('annulee', 'Annulée'),
    ]
    
    membre = models.ForeignKey(User, on_delete=models.CASCADE)
    numero = models.CharField(max_length=20, unique=True)
    date_creation = models.DateTimeField(default=timezone.now)
    date_echeance = models.DateTimeField()
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    statut = models.CharField(max_length=15, choices=STATUTS_FACTURE, default='en_attente')
    reservation = models.ForeignKey(Reservation, on_delete=models.SET_NULL, null=True, blank=True)
    
    
    def mise_a_jour_statut(self):
        if self.statut != 'payee' and timezone.now() > self.date_echeance:
            self.statut = 'en_retard'
            self.save()
    def __str__(self):
        return f"Facture {self.numero} - {self.membre.username}"

class Notification(models.Model):
    TYPES = [
        ('reservation', 'Réservation'),
        ('evenement', 'Événement'),
        ('facture', 'Facture'),
        ('general', 'Général'),
    ]
    
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE)
    titre = models.CharField(max_length=100)
    message = models.TextField()
    type_notification = models.CharField(max_length=15, choices=TYPES, default='general')
    date_creation = models.DateTimeField(default=timezone.now)
    lue = models.BooleanField(default=False)
    
    def marquer_comme_lue(self):
        self.lue = True
        self.save()

    def __str__(self):
        return f"{self.titre} - {self.destinataire.username}"
    
    
class HistoriqueReservation(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    date_action = models.DateTimeField(default=timezone.now)
    action = models.CharField(max_length=50)  # Exemple: "Création", "Annulation"

class HistoriquePaiement(models.Model):
    facture = models.ForeignKey(Facture, on_delete=models.CASCADE)
    date_paiement = models.DateTimeField(default=timezone.now)
    montant = models.DecimalField(max_digits=10, decimal_places=2)



class RoleUtilisateur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    ROLE_CHOICES = [
        ('membre', 'Membre'),
        ('gestionnaire', 'Gestionnaire'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='membre')
