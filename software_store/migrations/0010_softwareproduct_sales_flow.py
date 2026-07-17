# Generated manually to distinguish one-time orders from SaaS subscriptions.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            'software_store',
            '0009_softwareproduct_saas_signup_url'
        ),
    ]

    operations = [
        migrations.AddField(
            model_name='softwareproduct',
            name='sales_flow',
            field=models.CharField(
                choices=[
                    (
                        'Order Form',
                        'Order Form'
                    ),
                    (
                        'SaaS Subscription',
                        'SaaS Subscription'
                    ),
                ],
                default='Order Form',
                max_length=50
            ),
        ),
    ]
