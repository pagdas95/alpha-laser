from django.db import models

# Create your models here.
class Client(models.Model):
    full_name  = models.CharField("Ονοματεπώνυμο", max_length=120)
    phone      = models.CharField("Τηλέφωνο", max_length=32, db_index=True)
    email      = models.EmailField("Email", blank=True)
    birth_date = models.DateField("Ημ/νία γέννησης", null=True, blank=True)
    notes      = models.TextField("Σημειώσεις", blank=True)

    SKIN_TYPE_CHOICES = [
        ("light", "Ανοιχτό"), 
        ("medium", "Μεσαίο"), 
        ("medium_dark", "Μεσαίο-Σκούρο"),
        ("dark", "Σκούρο"), 
        ("black", "Μαύρο"), 
        ("sensitive", "Ευαίσθητο"), 
        ("other", "Άλλο"),
    ]
    HAIR_COLOR_CHOICES = [
        ("black","Μαύρο"), ("dark_brown","Σκούρο καστανό"), ("brown","Καστανό"),
        ("light_brown","Ανοιχτό καστανό"), ("blonde","Ξανθό"), ("red","Κόκκινο"),
        ("grey","Γκρι"), ("white","Άσπρο"), ("other","Άλλο"), ("unknown","Άγνωστο"),
    ]
    skin_type  = models.CharField("Τύπος δέρματος", max_length=15, choices=SKIN_TYPE_CHOICES, blank=True, null=True)
    hair_color = models.CharField("Χρώμα τριχών", max_length=12, choices=HAIR_COLOR_CHOICES, blank=True, null=True)

    # ✨✨✨ NEW: Notification Preferences ✨✨✨
    receive_booking_sms = models.BooleanField(
        "Λήψη SMS κράτησης",
        default=True,
        help_text="Αποστολή SMS επιβεβαίωσης κράτησης"
    )
    receive_booking_email = models.BooleanField(
        "Λήψη Email κράτησης",
        default=True,
        help_text="Αποστολή email επιβεβαίωσης κράτησης"
    )
    receive_reminder_sms = models.BooleanField(
        "Λήψη SMS υπενθύμισης",
        default=True,
        help_text="Αποστολή SMS υπενθύμισης 24 ώρες πριν το ραντεβού"
    )
    receive_reminder_email = models.BooleanField(
        "Λήψη Email υπενθύμισης",
        default=True,
        help_text="Αποστολή email υπενθύμισης 24 ώρες πριν το ραντεβού"
    )
    # ✨✨✨ END NEW FIELDS ✨✨✨

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return f"{self.full_name} ({self.phone})"

class ClientConsent(models.Model):
    client      = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="consents")
    text_version= models.CharField(max_length=32)
    accepted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Consent {self.text_version} for {self.client}"