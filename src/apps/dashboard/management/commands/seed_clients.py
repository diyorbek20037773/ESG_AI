from django.core.management.base import BaseCommand

from src.apps.dashboard.models import Client

SAMPLE = [
    ("Green Steppe Energy LLC", "301234567", "Renewable energy", "Toshkent"),
    ("Nur Solar Systems", "302345678", "Solar power", "Samarqand"),
    ("Amudaryo Hydro", "303456789", "Hydropower", "Xorazm"),
    ("EcoBuild Uzbekistan", "304567890", "Construction", "Toshkent"),
    ("Zamin Agro Cluster", "305678901", "Agriculture", "Buxoro"),
    ("Silk Road Logistics", "306789012", "Transport", "Toshkent"),
    ("Farg'ona Textile Group", "307890123", "Textile", "Farg'ona"),
    ("Qizilqum Mining Co", "308901234", "Mining", "Navoiy"),
]


class Command(BaseCommand):
    help = "Seed a few sample bank clients for the dashboard demo."

    def handle(self, *args, **options):
        created = 0
        for name, stir, industry, region in SAMPLE:
            _, made = Client.objects.get_or_create(
                name=name, defaults={"stir": stir, "industry": industry, "region": region})
            created += int(made)
        self.stdout.write(self.style.SUCCESS(f"Seeded clients: {created} new, "
                                             f"{Client.objects.count()} total."))
