# Generated manually to point Pharmacy Cloud to the SaaS app.

from django.db import migrations


PHARMACY_SAAS_URL = 'https://mitsol-pharmacy-saas.onrender.com/'


def set_pharmacy_cloud_saas_url(apps, schema_editor):

    SoftwareProduct = apps.get_model(
        'software_store',
        'SoftwareProduct'
    )

    SoftwareProduct.objects.filter(
        name__icontains='Pharmacy Cloud'
    ).update(
        delivery_type='Web Application',
        sales_flow='SaaS Subscription',
        saas_signup_url=PHARMACY_SAAS_URL
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            'software_store',
            '0011_mark_pharmacy_cloud_as_saas'
        ),
    ]

    operations = [
        migrations.RunPython(
            set_pharmacy_cloud_saas_url,
            migrations.RunPython.noop
        ),
    ]
