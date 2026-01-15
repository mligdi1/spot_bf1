from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('spot', '0025_user_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='email_error',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='notification',
            name='email_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='notification',
            name='email_status',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='notification',
            name='whatsapp_error',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='notification',
            name='whatsapp_message_id',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='notification',
            name='whatsapp_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='notification',
            name='whatsapp_status',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
