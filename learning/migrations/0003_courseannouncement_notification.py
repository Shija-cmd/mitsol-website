# Generated manually for MITSOL Learn Phase II Stage 1.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            'learning',
            '0002_initial_categories_and_groups'
        ),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=180)),
                ('message', models.TextField()),
                ('notification_type', models.CharField(choices=[('Enrolment', 'Enrolment'), ('Payment', 'Payment'), ('Quiz', 'Quiz'), ('Assignment', 'Assignment'), ('Announcement', 'Announcement'), ('Course Completion', 'Course Completion'), ('Certificate', 'Certificate'), ('System', 'System')], default='System', max_length=40)),
                ('related_url', models.CharField(blank=True, max_length=1000)),
                ('dedupe_key', models.CharField(blank=True, help_text='Optional key used by services to avoid duplicate notifications.', max_length=255)),
                ('is_read', models.BooleanField(default=False)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='learning_notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-created_at',),
                'indexes': [
                    models.Index(fields=['recipient', 'is_read'], name='learning_no_recipie_e8673c_idx'),
                    models.Index(fields=['notification_type'], name='learning_no_notific_7d05e5_idx'),
                    models.Index(fields=['created_at'], name='learning_no_created_3c962e_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(condition=~models.Q(dedupe_key=''), fields=('recipient', 'dedupe_key'), name='unique_learning_notification_dedupe'),
                ],
            },
        ),
        migrations.CreateModel(
            name='CourseAnnouncement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=220)),
                ('message', models.TextField()),
                ('is_published', models.BooleanField(default=False)),
                ('published_at', models.DateTimeField(blank=True, null=True)),
                ('notifications_sent', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='learning_announcements', to=settings.AUTH_USER_MODEL)),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='announcements', to='learning.course')),
            ],
            options={
                'ordering': ('-published_at', '-created_at'),
            },
        ),
    ]
