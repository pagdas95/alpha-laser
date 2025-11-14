import os
import random
from datetime import timedelta

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from django.db import transaction

from alpha.clients.models import Client
from alpha.resources.models import Room, Machine
from alpha.catalog.models import (
    ServiceCategory, Service, Package, PackageItem,
    ClientPackage, ClientPackageItem,
)
from alpha.appointments.models import Appointment
from alpha.visits.models import Visit

class Command(BaseCommand):
    help = "Seed ALPHA LASER demo data (rooms, machines, services, clients, packages, appointments, visits)."

    def add_arguments(self, parser):
        parser.add_argument("--with-users", action="store_true",
                            help="Create demo admin/staff users and groups.")
        parser.add_argument("--days", type=int, default=2,
                            help="How many days to populate appointments for (default: 2 = today+tomorrow).")

    @transaction.atomic
    def handle(self, *args, **opts):
        tz = timezone.get_current_timezone()
        self.stdout.write(self.style.MIGRATE_HEADING("Seeding ALPHA LASER demo data..."))

        if opts["with_users"]:
            self._seed_users()

        self._seed_rooms_and_machines()
        self._seed_services_and_packages()
        clients = self._seed_clients()

        # Give first client a package and seed remaining_sessions
        self._seed_client_packages(clients)

        # Appointments (no overlaps per room)
        self._seed_appointments(clients, days=opts["days"], tz=tz)

        # Create visits for some past appointments
        self._seed_visits()

        self.stdout.write(self.style.SUCCESS("Done!"))

    # ---------- helpers ----------

    def _seed_users(self):
        User = get_user_model()
        admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@alphalaserc.com")
        admin_pass = os.getenv("SEED_ADMIN_PASSWORD", "Admin123!")
        staff_email = os.getenv("SEED_STAFF_EMAIL", "staff@alphalaserc.com")
        staff_pass = os.getenv("SEED_STAFF_PASSWORD", "Staff123!")

        # Groups
        admin_group, _ = Group.objects.get_or_create(name="Admin")
        staff_group, _ = Group.objects.get_or_create(name="Staff")

        # Admin user
        admin, created = User.objects.get_or_create(
            email=admin_email,
            defaults={"name": "Admin User", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password(admin_pass)
            admin.save()
        admin.groups.add(admin_group)

        # Staff user
        staff, created = User.objects.get_or_create(
            email=staff_email,
            defaults={"name": "Staff User", "is_staff": True, "is_superuser": False},
        )
        if created:
            staff.set_password(staff_pass)
            staff.save()
        staff.groups.add(staff_group)

        self.stdout.write(self.style.SUCCESS(
            f"Users ready. Admin: {admin_email}/{admin_pass}  Staff: {staff_email}/{staff_pass}"
        ))

    def _seed_rooms_and_machines(self):
        for i in range(1, 5):
            Room.objects.get_or_create(name=f"Room {i}")
        Machine.objects.get_or_create(name="Laser A", defaults={"notes": "Diode 808"})
        Machine.objects.get_or_create(name="Laser B", defaults={"notes": "Alexandrite"})
        self.stdout.write(self.style.SUCCESS("Rooms 1–4 and 2 machines created."))

    def _seed_services_and_packages(self):
        laser_cat, _ = ServiceCategory.objects.get_or_create(name="Laser")
        nails_cat, _ = ServiceCategory.objects.get_or_create(name="Nails")
        other_cat, _ = ServiceCategory.objects.get_or_create(name="Other")

        # Services
        laser_underarm, _ = Service.objects.get_or_create(
            category=laser_cat, name="Laser Μασχάλες",
            defaults={"gender": "any", "default_price": Decimal("25.00"), "duration_min": 20},
        )
        laser_bikini, _ = Service.objects.get_or_create(
            category=laser_cat, name="Laser Bikini",
            defaults={"gender": "female", "default_price": Decimal("35.00"), "duration_min": 30},
        )
        manicure, _ = Service.objects.get_or_create(
            category=nails_cat, name="Manicure",
            defaults={"gender": "any", "default_price": Decimal("20.00"), "duration_min": 45},
        )
        lash_lift, _ = Service.objects.get_or_create(
            category=other_cat, name="Lash Lift",
            defaults={"gender": "any", "default_price": Decimal("30.00"), "duration_min": 40},
        )

        # Package with items
        pkg, _ = Package.objects.get_or_create(
            name="Laser Small Areas – 6 Sessions",
            defaults={"price": Decimal("120.00"), "notes": "Underarm + Upper Lip"},
        )
        # Ensure items exist
        PackageItem.objects.get_or_create(package=pkg, service=laser_underarm, defaults={"sessions": 6})
        # If you have an “Upper Lip” service add that too; use Laser Μασχάλες twice as placeholder
        PackageItem.objects.get_or_create(package=pkg, service=laser_bikini, defaults={"sessions": 6})

        self.stdout.write(self.style.SUCCESS("Service categories, services, and one package with items created."))

    def _seed_clients(self):
        clients = []
        c1, _ = Client.objects.get_or_create(
            phone="700000001",
            defaults={
                "full_name": "Maria Papadopoulou",
                "email": "maria@alphalaserc.com",
                "skin_type": "III",
                "hair_color": "dark_brown",
                "notes": "Πρώτη φορά στο laser.",
            },
        )
        clients.append(c1)

        c2, _ = Client.objects.get_or_create(
            phone="700000002",
            defaults={
                "full_name": "Andreas Christou",
                "email": "andreas@alphalaserc.com",
                "skin_type": "IV",
                "hair_color": "black",
            },
        )
        clients.append(c2)

        c3, _ = Client.objects.get_or_create(
            phone="700000003",
            defaults={
                "full_name": "Eleni Georgiou",
                "email": "eleni@alphalaserc.com",
            },
        )
        clients.append(c3)

        self.stdout.write(self.style.SUCCESS(f"{len(clients)} clients created."))
        return clients

    def _seed_client_packages(self, clients):
        pkg = Package.objects.first()
        if not pkg:
            self.stdout.write(self.style.WARNING("No Package found; skipping client packages."))
            return

        # Give first client a package
        cp, created = ClientPackage.objects.get_or_create(
            client=clients[0], package=pkg,
            defaults={"price_paid": pkg.price, "notes": "Demo purchase", "active": True},
        )
        if created:
            # Copy items to ClientPackageItem with remaining sessions
            for item in pkg.items.all():
                ClientPackageItem.objects.create(
                    client_package=cp, package_item=item, remaining_sessions=item.sessions
                )
        self.stdout.write(self.style.SUCCESS("ClientPackage created for first client."))

    def _seed_appointments(self, clients, days, tz):
        User = get_user_model()
        staff = User.objects.filter(is_staff=True).first()
        if not staff:
            self.stdout.write(self.style.WARNING("No staff user found; appointments will use first superuser if available."))

        rooms = list(Room.objects.filter(is_active=True).order_by("id"))
        machines = list(Machine.objects.filter(is_active=True))
        services = list(Service.objects.all())
        if not rooms or not services:
            self.stdout.write(self.style.WARNING("Missing rooms or services; cannot create appointments."))
            return

        created = 0
        now = timezone.now().astimezone(tz)
        base_day = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # For each day, create staggered appointments per room (avoid overlaps)
        for d in range(days):
            day_start = base_day + timedelta(days=d)
            # slots: 10:00, 11:00, 12:00, 13:00
            slot_times = [10, 11, 12, 13]
            for idx, room in enumerate(rooms):
                for h in slot_times:
                    start = day_start + timedelta(hours=h + idx * 0)  # room offset if needed
                    service = random.choice(services)
                    duration = timedelta(minutes=service.duration_min)
                    end = start + duration
                    client = random.choice(clients)
                    machine = random.choice(machines) if machines and service.category.name == "Laser" else None

                    try:
                        Appointment.objects.create(
                            client=client,
                            service=service,
                            staff=staff if staff else None,
                            room=room,
                            machine=machine,
                            start=start,
                            end=end,
                            status="booked",
                            notes="Demo appointment",
                        )
                        created += 1
                    except Exception as e:
                        # If constraint blocks overlap or staff is None in your model, skip
                        self.stdout.write(self.style.WARNING(f"Skip appt @ {start}: {e}"))
                        continue

        self.stdout.write(self.style.SUCCESS(f"Created ~{created} appointments over {days} day(s)."))

    def _seed_visits(self):
        # Turn some past appointments into completed visits with energy/pulses
        past_appts = Appointment.objects.filter(start__lt=timezone.now()).order_by("-start")[:5]
        made = 0
        for appt in past_appts:
            # Skip if visit exists
            if hasattr(appt, "visit"):
                continue

            # Try to use a matching client package item (same service) if exists
            cpi = None
            for cp in appt.client.packages.filter(active=True):
                # pick a matching item with remaining sessions
                for item in cp.items.select_related("package_item__service"):
                    if item.package_item.service_id == appt.service_id and item.remaining_sessions > 0:
                        cpi = item
                        break
                if cpi:
                    break

            # Demo laser metrics if laser service, else plain visit
            is_laser = appt.machine_id is not None or appt.service.category.name.lower() == "laser"
            fluence = Decimal("12.5") if is_laser else None
            pulses = random.randint(100, 350) if is_laser else None

            charge = appt.service.default_price
            paid = charge if not cpi else Decimal("0.00")

            try:
                Visit.objects.create(
                    appointment=appt,
                    staff=appt.staff,
                    machine=appt.machine if is_laser else None,
                    area="Μασχάλες" if is_laser else "",
                    spot_size_mm=Decimal("12.0") if is_laser else None,
                    fluence_j_cm2=fluence,
                    pulse_count=pulses,
                    remarks="Demo visit",
                    charge_amount=charge,
                    paid_amount=paid,
                    payment_method="cash" if paid > 0 else "other",
                    client_package_item=cpi,
                )
                appt.status = "completed"
                appt.save(update_fields=["status"])
                made += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Skip visit for appt {appt.id}: {e}"))
                continue

        self.stdout.write(self.style.SUCCESS(f"Created {made} visit(s)."))
