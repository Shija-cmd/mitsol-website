from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


SAFE_DOCUMENT_EXTENSIONS = [
    'pdf',
    'doc',
    'docx',
    'ppt',
    'pptx',
    'xls',
    'xlsx',
    'txt',
    'zip',
]

SAFE_VIDEO_EXTENSIONS = [
    'mp4',
    'mov',
    'webm',
    'm4v',
]


class CourseCategory(models.Model):

    name = models.CharField(
        max_length=150,
        unique=True
    )

    slug = models.SlugField(
        max_length=170,
        unique=True,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = (
            'name',
        )

        verbose_name_plural = 'Course categories'

    def __str__(self):

        return self.name

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = self.generate_unique_slug()

        super().save(*args, **kwargs)

    def generate_unique_slug(self):

        base_slug = slugify(self.name) or 'category'
        slug = base_slug
        counter = 2

        while CourseCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        return slug

    def get_absolute_url(self):

        return reverse(
            'learning:category',
            args=[
                self.slug,
            ]
        )


class InstructorProfile(models.Model):

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='instructor_profile'
    )

    title = models.CharField(
        max_length=150,
        blank=True
    )

    bio = models.TextField(
        blank=True
    )

    expertise = models.CharField(
        max_length=255,
        blank=True,
        help_text='Separate multiple values using commas.'
    )

    photo = models.ImageField(
        upload_to='learning/instructors/',
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
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
            'user__first_name',
            'user__last_name',
            'user__username',
        )

    def __str__(self):

        return self.display_name

    @property
    def display_name(self):

        full_name = self.user.get_full_name()

        return full_name or self.user.username


class Course(models.Model):

    class Level(models.TextChoices):

        BEGINNER = 'Beginner', 'Beginner'
        INTERMEDIATE = 'Intermediate', 'Intermediate'
        ADVANCED = 'Advanced', 'Advanced'
        ALL_LEVELS = 'All Levels', 'All Levels'

    class DeliveryMode(models.TextChoices):

        SELF_PACED = 'Self-Paced', 'Self-Paced'
        LIVE_ONLINE = 'Live Online', 'Live Online'
        BLENDED = 'Blended', 'Blended'
        FACE_TO_FACE = 'Face-to-Face', 'Face-to-Face'

    class Status(models.TextChoices):

        DRAFT = 'Draft', 'Draft'
        PENDING_REVIEW = 'Pending Review', 'Pending Review'
        PUBLISHED = 'Published', 'Published'
        ARCHIVED = 'Archived', 'Archived'

    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='learning_courses'
    )

    category = models.ForeignKey(
        CourseCategory,
        on_delete=models.PROTECT,
        related_name='courses'
    )

    title = models.CharField(
        max_length=220
    )

    slug = models.SlugField(
        max_length=240,
        unique=True,
        blank=True
    )

    short_description = models.CharField(
        max_length=300
    )

    full_description = models.TextField()

    cover_image = models.ImageField(
        upload_to='learning/course_covers/',
        blank=True,
        null=True
    )

    promotional_video_url = models.URLField(
        max_length=1000,
        blank=True
    )

    level = models.CharField(
        max_length=30,
        choices=Level.choices,
        default=Level.ALL_LEVELS
    )

    language = models.CharField(
        max_length=80,
        default='English'
    )

    delivery_mode = models.CharField(
        max_length=40,
        choices=DeliveryMode.choices,
        default=DeliveryMode.SELF_PACED
    )

    estimated_duration = models.CharField(
        max_length=100,
        blank=True,
        help_text='Example: 6 weeks, 20 hours, or 12 lessons.'
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    is_free = models.BooleanField(
        default=True
    )

    learning_outcomes = models.TextField(
        blank=True,
        help_text='One outcome per line.'
    )

    requirements = models.TextField(
        blank=True,
        help_text='One requirement per line.'
    )

    target_audience = models.TextField(
        blank=True,
        help_text='One audience group per line.'
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT
    )

    is_featured = models.BooleanField(
        default=False
    )

    is_published = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            '-is_featured',
            '-created_at',
        )

        indexes = (
            models.Index(fields=('slug',)),
            models.Index(fields=('category',)),
            models.Index(fields=('instructor',)),
            models.Index(fields=('status',)),
            models.Index(fields=('is_published',)),
            models.Index(fields=('is_featured',)),
            models.Index(fields=('created_at',)),
        )

    def __str__(self):

        return self.title

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = self.generate_unique_slug()

        if self.status == self.Status.PUBLISHED:

            self.is_published = True

        else:

            self.is_published = False

        super().save(*args, **kwargs)

    def generate_unique_slug(self):

        base_slug = slugify(self.title) or 'course'
        slug = base_slug
        counter = 2

        while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        return slug

    def get_absolute_url(self):

        return reverse(
            'learning:course_detail',
            args=[
                self.slug,
            ]
        )

    @property
    def display_price(self):

        if self.is_free:

            return 'Free'

        active_price = self.discount_price or self.price

        return f'TSh {active_price:,.0f}'

    @property
    def outcome_list(self):

        return self._split_lines(self.learning_outcomes)

    @property
    def requirement_list(self):

        return self._split_lines(self.requirements)

    @property
    def target_audience_list(self):

        return self._split_lines(self.target_audience)

    def _split_lines(self, value):

        return [
            item.strip()
            for item in value.splitlines()
            if item.strip()
        ]


class Module(models.Model):

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='modules'
    )

    title = models.CharField(
        max_length=220
    )

    description = models.TextField(
        blank=True
    )

    order = models.PositiveIntegerField(
        default=1
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
            'order',
            'title',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'course',
                    'order',
                ),
                name='unique_module_order_per_course'
            ),
        )

    def __str__(self):

        return f'{self.course.title} - {self.title}'


class Lesson(models.Model):

    class LessonType(models.TextChoices):

        VIDEO = 'Video', 'Video'
        TEXT = 'Text', 'Text'
        DOCUMENT = 'Document', 'Document'
        EXTERNAL_RESOURCE = 'External Resource', 'External Resource'
        QUIZ = 'Quiz', 'Quiz'
        ASSIGNMENT = 'Assignment', 'Assignment'
        LIVE_SESSION = 'Live Session', 'Live Session'

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='lessons'
    )

    title = models.CharField(
        max_length=220
    )

    slug = models.SlugField(
        max_length=240,
        blank=True
    )

    lesson_type = models.CharField(
        max_length=40,
        choices=LessonType.choices,
        default=LessonType.TEXT
    )

    written_content = models.TextField(
        blank=True
    )

    video_url = models.URLField(
        max_length=1000,
        blank=True
    )

    video_file = models.FileField(
        upload_to='learning/videos/',
        validators=[
            FileExtensionValidator(SAFE_VIDEO_EXTENSIONS),
        ],
        blank=True,
        null=True
    )

    downloadable_file = models.FileField(
        upload_to='learning/documents/',
        validators=[
            FileExtensionValidator(SAFE_DOCUMENT_EXTENSIONS),
        ],
        blank=True,
        null=True
    )

    source_code_file = models.FileField(
        upload_to='learning/documents/source_code/',
        validators=[
            FileExtensionValidator(['zip']),
        ],
        blank=True,
        null=True
    )

    external_resource_url = models.URLField(
        max_length=1000,
        blank=True
    )

    duration_minutes = models.PositiveIntegerField(
        default=0
    )

    order = models.PositiveIntegerField(
        default=1
    )

    is_preview = models.BooleanField(
        default=False
    )

    is_compulsory = models.BooleanField(
        default=True
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
            'module__order',
            'order',
            'title',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'module',
                    'slug',
                ),
                name='unique_lesson_slug_per_module'
            ),
            models.UniqueConstraint(
                fields=(
                    'module',
                    'order',
                ),
                name='unique_lesson_order_per_module'
            ),
        )

    def __str__(self):

        return f'{self.module.course.title} - {self.title}'

    def save(self, *args, **kwargs):

        if not self.slug:

            self.slug = self.generate_unique_slug()

        super().save(*args, **kwargs)

    def generate_unique_slug(self):

        base_slug = slugify(self.title) or 'lesson'
        slug = base_slug
        counter = 2

        while Lesson.objects.filter(
            module=self.module,
            slug=slug
        ).exclude(pk=self.pk).exists():
            slug = f'{base_slug}-{counter}'
            counter += 1

        return slug

    @property
    def embedded_video_url(self):

        if not self.video_url:

            return ''

        parsed_url = urlparse(
            self.video_url
        )

        hostname = parsed_url.hostname or ''

        if 'youtu.be' in hostname:

            video_id = parsed_url.path.strip('/').split('/')[0]

        elif 'youtube.com' in hostname:

            if parsed_url.path.startswith('/embed/'):

                return self.video_url

            if parsed_url.path.startswith('/shorts/'):

                video_id = parsed_url.path.split('/shorts/', 1)[1].split('/')[0]

            elif parsed_url.path.startswith('/live/'):

                video_id = parsed_url.path.split('/live/', 1)[1].split('/')[0]

            else:

                video_id = parse_qs(
                    parsed_url.query
                ).get(
                    'v',
                    [
                        '',
                    ]
                )[0]

        else:

            return self.video_url

        if not video_id:

            return ''

        video_id = video_id.split('?')[0].split('&')[0]

        return f'https://www.youtube.com/embed/{video_id}'


class Enrolment(models.Model):

    class Status(models.TextChoices):

        PENDING = 'Pending', 'Pending'
        ACTIVE = 'Active', 'Active'
        COMPLETED = 'Completed', 'Completed'
        SUSPENDED = 'Suspended', 'Suspended'
        CANCELLED = 'Cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):

        NOT_REQUIRED = 'Not Required', 'Not Required'
        PENDING = 'Pending', 'Pending'
        PAID = 'Paid', 'Paid'
        REJECTED = 'Rejected', 'Rejected'
        REFUNDED = 'Refunded', 'Refunded'

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_enrolments'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrolments'
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING
    )

    payment_status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    enrolled_at = models.DateTimeField(
        auto_now_add=True
    )

    activated_at = models.DateTimeField(
        blank=True,
        null=True
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    progress_percentage = models.PositiveIntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    )

    is_active = models.BooleanField(
        default=False
    )

    class Meta:

        ordering = (
            '-enrolled_at',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'student',
                    'course',
                ),
                name='unique_student_course_enrolment'
            ),
        )

    def __str__(self):

        return f'{self.student} - {self.course}'

    def save(self, *args, **kwargs):

        if self.course.is_free and self.status == self.Status.PENDING:

            self.status = self.Status.ACTIVE
            self.payment_status = self.PaymentStatus.NOT_REQUIRED
            self.is_active = True

            if not self.activated_at:

                self.activated_at = timezone.now()

        super().save(*args, **kwargs)


class LessonProgress(models.Model):

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='progress_records'
    )

    enrolment = models.ForeignKey(
        Enrolment,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )

    is_completed = models.BooleanField(
        default=False
    )

    started_at = models.DateTimeField(
        auto_now_add=True
    )

    completed_at = models.DateTimeField(
        blank=True,
        null=True
    )

    last_accessed_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        ordering = (
            '-last_accessed_at',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'student',
                    'lesson',
                ),
                name='unique_student_lesson_progress'
            ),
        )

    def __str__(self):

        return f'{self.student} - {self.lesson}'
