import django.db.models.deletion
import django.db.models.functions.text
from django.conf import settings
from django.db import migrations, models


from django.contrib.auth.hashers import make_password


def set_default_user(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Show = apps.get_model('tracker', 'Show')
    user = User.objects.first()
    if not user:
        user = User.objects.create(
            username='admin',
            email='admin@example.com',
            password=make_password('admin1234'),
            is_staff=True,
            is_superuser=True
        )
    Show.objects.filter(user__isnull=True).update(user=user)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0003_show_unique_show_title_case_insensitive'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='show',
            name='unique_show_title_case_insensitive',
        ),
        migrations.AddField(
            model_name='show',
            name='user',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='shows',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.RunPython(set_default_user, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='show',
            name='user',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='shows',
                to=settings.AUTH_USER_MODEL,
                db_index=True
            ),
        ),
        migrations.AddIndex(
            model_name='show',
            index=models.Index(fields=['user', 'status', '-updated_at'], name='tracker_sho_user_id_0f0556_idx'),
        ),
        migrations.AddIndex(
            model_name='show',
            index=models.Index(fields=['user', '-updated_at'], name='tracker_sho_user_id_4ba4b7_idx'),
        ),
        migrations.AddConstraint(
            model_name='show',
            constraint=models.UniqueConstraint(
                models.F('user'),
                django.db.models.functions.text.Lower('title'),
                name='unique_user_show_title_case_insensitive'
            ),
        ),
    ]
