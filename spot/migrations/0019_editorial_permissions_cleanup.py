from django.db import migrations


def cleanup_editorial_permissions(apps, schema_editor):
    User = apps.get_model('spot', 'User')
    for u in User.objects.filter(role='editorial_manager'):
        u.is_staff = False
        u.is_superuser = False
        try:
            u.user_permissions.clear()
        except Exception:
            pass
        u.save(update_fields=['is_staff', 'is_superuser'])


class Migration(migrations.Migration):
    dependencies = [
        ('spot', '0018_driver_journalist_alter_user_role_coverageassignment_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_editorial_permissions, migrations.RunPython.noop),
    ]