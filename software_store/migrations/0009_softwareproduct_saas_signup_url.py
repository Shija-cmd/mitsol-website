# Generated manually to support SaaS signup flows.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            'software_store',
            '0008_product_details_content'
        ),
    ]

    operations = [
        migrations.AddField(
            model_name='softwareproduct',
            name='saas_signup_url',
            field=models.URLField(
                blank=True,
                help_text='For SaaS products, send tenants here to create an account, create a pharmacy, and subscribe.',
                max_length=1000
            ),
        ),
    ]
