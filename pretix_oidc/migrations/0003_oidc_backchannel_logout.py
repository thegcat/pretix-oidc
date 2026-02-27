import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("pretix_oidc", "0002_auto_20200919_2030"),
    ]

    operations = [
        migrations.CreateModel(
            name="OIDCSession",
            fields=[
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="pretixbase.User",
                    ),
                ),
                ("session_id", models.CharField(max_length=255, db_index=True)),
                ("oidc_session_id", models.CharField(max_length=255, db_index=True)),
                ("oidc_user_id", models.CharField(max_length=255, db_index=True)),
                ("oidc_issuer", models.CharField(max_length=255, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["oidc_issuer", "oidc_user_id"], name="oidc_issuer_user_idx"),
                    models.Index(fields=["oidc_issuer", "oidc_session_id"], name="oidc_issuer_sess_idx"),
                ],
            },
        ),
    ]