from django.db import migrations


def create_missing_assignment_notification_tables(apps, schema_editor):
    existing = set(schema_editor.connection.introspection.table_names())

    campaign_model = apps.get_model('spot', 'AssignmentNotificationCampaign')
    attempt_model = apps.get_model('spot', 'AssignmentNotificationAttempt')

    if campaign_model._meta.db_table not in existing:
        schema_editor.create_model(campaign_model)
        existing.add(campaign_model._meta.db_table)

    if attempt_model._meta.db_table not in existing:
        schema_editor.create_model(attempt_model)


class Migration(migrations.Migration):
    dependencies = [
        ('spot', '0023_assignment_notifications'),
    ]

    operations = [
        migrations.RunPython(
            create_missing_assignment_notification_tables,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

