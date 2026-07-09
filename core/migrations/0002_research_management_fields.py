# Generated manually to extend research publication management.

from django.db import migrations, models
import django.utils.text


def populate_research_slugs(apps, schema_editor):

    ResearchPublication = apps.get_model(
        'core',
        'ResearchPublication'
    )

    used_slugs = set()

    for publication in ResearchPublication.objects.all().order_by('id'):

        base_slug = django.utils.text.slugify(
            publication.title
        ) or 'research'

        slug = base_slug
        counter = 2

        while (
            slug in used_slugs
            or ResearchPublication.objects.filter(
                slug=slug
            ).exclude(
                pk=publication.pk
            ).exists()
        ):

            slug = f'{base_slug}-{counter}'
            counter += 1

        publication.slug = slug
        publication.save(
            update_fields=[
                'slug',
            ]
        )
        used_slugs.add(
            slug
        )


class Migration(migrations.Migration):

    dependencies = [
        (
            'core',
            '0001_initial'
        ),
    ]

    operations = [
        migrations.RenameField(
            model_name='researchpublication',
            old_name='is_featured',
            new_name='featured',
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='slug',
            field=models.SlugField(
                blank=True,
                max_length=255,
                null=True,
                unique=True
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='status',
            field=models.CharField(
                choices=[
                    (
                        'Published',
                        'Published'
                    ),
                    (
                        'Accepted',
                        'Accepted'
                    ),
                    (
                        'Under Review',
                        'Under Review'
                    ),
                    (
                        'In Progress',
                        'In Progress'
                    ),
                    (
                        'Completed',
                        'Completed'
                    ),
                ],
                default='Published',
                max_length=50
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='objectives',
            field=models.TextField(
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='methodology',
            field=models.TextField(
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='results',
            field=models.TextField(
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='conclusion',
            field=models.TextField(
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='future_work',
            field=models.TextField(
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='journal',
            field=models.CharField(
                blank=True,
                max_length=255
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='conference',
            field=models.CharField(
                blank=True,
                max_length=255
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='publisher',
            field=models.CharField(
                blank=True,
                max_length=255
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='volume',
            field=models.CharField(
                blank=True,
                max_length=50
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='issue',
            field=models.CharField(
                blank=True,
                max_length=50
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='pages',
            field=models.CharField(
                blank=True,
                max_length=50
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='doi',
            field=models.CharField(
                blank=True,
                max_length=255
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='isbn',
            field=models.CharField(
                blank=True,
                max_length=100
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='research_area',
            field=models.TextField(
                blank=True,
                help_text='Separate multiple values using commas.'
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='keywords',
            field=models.TextField(
                blank=True,
                help_text='Separate multiple values using commas.'
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='technologies_used',
            field=models.TextField(
                blank=True,
                help_text='Separate multiple values using commas.'
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='featured_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='research/images/'
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='presentation_slides',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='research/slides/'
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='poster_image',
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to='research/posters/'
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='dataset_link',
            field=models.URLField(
                blank=True,
                max_length=1000
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='youtube_url',
            field=models.URLField(
                blank=True,
                max_length=1000
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='github_url',
            field=models.URLField(
                blank=True,
                max_length=1000
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='demo_url',
            field=models.URLField(
                blank=True,
                max_length=1000
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='views',
            field=models.PositiveIntegerField(
                default=0
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='downloads',
            field=models.PositiveIntegerField(
                default=0
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='citations',
            field=models.PositiveIntegerField(
                default=0
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='institution',
            field=models.CharField(
                blank=True,
                max_length=255
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='supervisors',
            field=models.TextField(
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='collaborators',
            field=models.TextField(
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='researchpublication',
            name='funding_source',
            field=models.CharField(
                blank=True,
                max_length=255
            ),
        ),
        migrations.AlterField(
            model_name='researchpublication',
            name='abstract',
            field=models.TextField(
                blank=True
            ),
        ),
        migrations.AlterField(
            model_name='researchpublication',
            name='category',
            field=models.CharField(
                choices=[
                    (
                        'Publication',
                        'Publication'
                    ),
                    (
                        'Research Project',
                        'Research Project'
                    ),
                    (
                        'Academic Work',
                        'Academic Work'
                    ),
                    (
                        'Case Study',
                        'Case Study'
                    ),
                    (
                        'Conference Paper',
                        'Conference Paper'
                    ),
                    (
                        'Technical Report',
                        'Technical Report'
                    ),
                    (
                        'White Paper',
                        'White Paper'
                    ),
                    (
                        'Thesis',
                        'Thesis'
                    ),
                ],
                default='Research Project',
                max_length=50
            ),
        ),
        migrations.AlterModelOptions(
            name='researchpublication',
            options={
                'ordering': (
                    '-featured',
                    '-publication_date',
                    '-created_at',
                ),
            },
        ),
        migrations.RunPython(
            populate_research_slugs,
            migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name='researchpublication',
            name='slug',
            field=models.SlugField(
                blank=True,
                max_length=255,
                unique=True
            ),
        ),
    ]
