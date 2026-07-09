from urllib.parse import parse_qs, urlparse

from django.db import models
from django.utils.text import slugify


class ResearchPublication(models.Model):

    class Category(models.TextChoices):

        PUBLICATION = 'Publication', 'Publication'

        RESEARCH_PROJECT = 'Research Project', 'Research Project'

        ACADEMIC_WORK = 'Academic Work', 'Academic Work'

        CASE_STUDY = 'Case Study', 'Case Study'

        CONFERENCE_PAPER = 'Conference Paper', 'Conference Paper'

        TECHNICAL_REPORT = 'Technical Report', 'Technical Report'

        WHITE_PAPER = 'White Paper', 'White Paper'

        THESIS = 'Thesis', 'Thesis'

    class Status(models.TextChoices):

        PUBLISHED = 'Published', 'Published'

        ACCEPTED = 'Accepted', 'Accepted'

        UNDER_REVIEW = 'Under Review', 'Under Review'

        IN_PROGRESS = 'In Progress', 'In Progress'

        COMPLETED = 'Completed', 'Completed'

    title = models.CharField(
        max_length=255
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True
    )

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.RESEARCH_PROJECT
    )

    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.PUBLISHED
    )

    featured = models.BooleanField(
        default=False
    )

    abstract = models.TextField(
        blank=True
    )

    objectives = models.TextField(
        blank=True
    )

    methodology = models.TextField(
        blank=True
    )

    results = models.TextField(
        blank=True
    )

    conclusion = models.TextField(
        blank=True
    )

    future_work = models.TextField(
        blank=True
    )

    authors = models.CharField(
        max_length=255,
        blank=True
    )

    publication_date = models.DateField(
        blank=True,
        null=True
    )

    journal_or_conference = models.CharField(
        max_length=255,
        blank=True
    )

    journal = models.CharField(
        max_length=255,
        blank=True
    )

    conference = models.CharField(
        max_length=255,
        blank=True
    )

    publisher = models.CharField(
        max_length=255,
        blank=True
    )

    volume = models.CharField(
        max_length=50,
        blank=True
    )

    issue = models.CharField(
        max_length=50,
        blank=True
    )

    pages = models.CharField(
        max_length=50,
        blank=True
    )

    doi = models.CharField(
        max_length=255,
        blank=True
    )

    isbn = models.CharField(
        max_length=100,
        blank=True
    )

    research_area = models.TextField(
        blank=True,
        help_text='Separate multiple values using commas.'
    )

    keywords = models.TextField(
        blank=True,
        help_text='Separate multiple values using commas.'
    )

    technologies_used = models.TextField(
        blank=True,
        help_text='Separate multiple values using commas.'
    )

    featured_image = models.ImageField(
        upload_to='research/images/',
        blank=True,
        null=True
    )

    external_link = models.URLField(
        max_length=1000,
        blank=True
    )

    pdf_file = models.FileField(
        upload_to='research/publications/',
        blank=True,
        null=True
    )

    presentation_slides = models.FileField(
        upload_to='research/slides/',
        blank=True,
        null=True
    )

    poster_image = models.ImageField(
        upload_to='research/posters/',
        blank=True,
        null=True
    )

    dataset_link = models.URLField(
        max_length=1000,
        blank=True
    )

    youtube_url = models.URLField(
        max_length=1000,
        blank=True
    )

    github_url = models.URLField(
        max_length=1000,
        blank=True
    )

    demo_url = models.URLField(
        max_length=1000,
        blank=True
    )

    views = models.PositiveIntegerField(
        default=0
    )

    downloads = models.PositiveIntegerField(
        default=0
    )

    citations = models.PositiveIntegerField(
        default=0
    )

    institution = models.CharField(
        max_length=255,
        blank=True
    )

    supervisors = models.TextField(
        blank=True
    )

    collaborators = models.TextField(
        blank=True
    )

    funding_source = models.CharField(
        max_length=255,
        blank=True
    )

    is_published = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            '-featured',
            '-publication_date',
            '-created_at',
        )

    def __str__(self):

        return self.title

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = self.generate_unique_slug()

        super().save(*args, **kwargs)

    def generate_unique_slug(self):

        base_slug = slugify(
            self.title
        ) or 'research'

        slug = base_slug
        counter = 2

        while ResearchPublication.objects.filter(
            slug=slug
        ).exclude(
            pk=self.pk
        ).exists():

            slug = f'{base_slug}-{counter}'
            counter += 1

        return slug

    @property
    def research_area_list(self):

        return self.split_comma_values(
            self.research_area
        )

    @property
    def keyword_list(self):

        return self.split_comma_values(
            self.keywords
        )

    @property
    def technologies_list(self):

        return self.split_comma_values(
            self.technologies_used
        )

    @property
    def youtube_embed_url(self):

        if not self.youtube_url:

            return ''

        parsed_url = urlparse(
            self.youtube_url
        )
        hostname = parsed_url.hostname or ''

        if 'youtu.be' in hostname:

            video_id = parsed_url.path.strip('/')

        elif 'youtube.com' in hostname:

            if parsed_url.path.startswith('/embed/'):

                return self.youtube_url

            video_id = parse_qs(
                parsed_url.query
            ).get(
                'v',
                [
                    '',
                ]
            )[0]

        else:

            return ''

        if not video_id:

            return ''

        return f'https://www.youtube.com/embed/{video_id}'

    def split_comma_values(self, value):

        return [
            item.strip()
            for item in value.split(',')
            if item.strip()
        ]
