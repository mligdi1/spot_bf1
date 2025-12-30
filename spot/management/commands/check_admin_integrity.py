from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.urls import get_resolver


class Command(BaseCommand):
    help = "Vérifie l'intégrité de la configuration administrateur après migration PostgreSQL"

    def handle(self, *args, **options):
        User = get_user_model()

        self.stdout.write(self.style.MIGRATE_HEADING("=== Vérification Admin/Permissions ==="))

        # 1) Vérifier superusers
        superusers = User.objects.filter(is_superuser=True)
        if superusers.exists():
            self.stdout.write(self.style.SUCCESS(f"Superusers trouvés: {', '.join([u.username for u in superusers])}"))
        else:
            self.stdout.write(self.style.ERROR("Aucun superuser n'a été trouvé. Utilisez 'python manage.py createsuperuser'."))

        # 2) Vérifier is_staff
        staff_users = User.objects.filter(is_staff=True)
        self.stdout.write(f"Comptes staff: {staff_users.count()}")

        # 3) Groupes et permissions
        groups_count = Group.objects.count()
        perms_count = Permission.objects.count()
        self.stdout.write(f"Groupes: {groups_count} | Permissions: {perms_count}")
        if perms_count == 0:
            self.stdout.write(self.style.WARNING("Aucune permission trouvée. Assurez-vous que les migrations auth sont appliquées."))

        # 4) INSTALLED_APPS
        admin_in_apps = 'django.contrib.admin' in settings.INSTALLED_APPS
        self.stdout.write(f"django.contrib.admin dans INSTALLED_APPS: {admin_in_apps}")

        # 5) URLs admin
        try:
            resolver = get_resolver()
            patterns = [str(p.pattern) for p in resolver.url_patterns]
            admin_configured = any('admin' in p for p in patterns)
            self.stdout.write(f"URL '/admin/': {admin_configured}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Impossible de vérifier les URLs: {e}"))

        # 6) Base de données actuelle
        db = settings.DATABASES.get('default', {})
        engine = db.get('ENGINE')
        name = db.get('NAME')
        host = db.get('HOST')
        port = db.get('PORT')
        self.stdout.write(f"DB Engine: {engine} | DB Name: {name} | Host: {host} | Port: {port}")

        self.stdout.write(self.style.SUCCESS("Vérification terminée."))