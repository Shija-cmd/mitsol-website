import uuid
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.db import models
from django.utils import timezone


def default_license_expiry_date():

    return timezone.localdate() + timedelta(days=365)


class SoftwareProduct(models.Model):

    class DeliveryType(models.TextChoices):

        DESKTOP = 'Desktop Software', 'Desktop Software'

        WEB_APP = 'Web Application', 'Web Application'

    name = models.CharField(
        max_length=200
    )

    slug = models.SlugField(
        unique=True
    )

    description = models.TextField()

    version = models.CharField(
        max_length=50
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    delivery_type = models.CharField(
        max_length=50,
        choices=DeliveryType.choices,
        default=DeliveryType.DESKTOP
    )

    proton_drive_link = models.URLField(
        max_length=1000,
        blank=True
    )
    
    proton_drive_password = models.CharField(
        max_length=255,
        blank=True
    )

    saas_signup_url = models.URLField(
        max_length=1000,
        blank=True,
        help_text='For SaaS products, send tenants here to create an account, create a pharmacy, and subscribe.'
    )

    release_notes = models.TextField(
        blank=True
    )

    key_features = models.TextField(
        blank=True,
        help_text='Optional fallback features, one per line. Use product feature rows for richer entries.'
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
    
    youtube_overview_url = models.URLField(
        max_length=1000,
        blank=True
    )

    youtube_installation_url = models.URLField(
        max_length=1000,
        blank=True
    )

    youtube_activation_url = models.URLField(
        max_length=1000,
        blank=True
    )

    class Meta:

        ordering = (
            'name',
        )

    def __str__(self):

        return self.name

    @property
    def is_desktop(self):

        return self.delivery_type == self.DeliveryType.DESKTOP

    @property
    def is_web_app(self):

        return self.delivery_type == self.DeliveryType.WEB_APP

    @property
    def uses_saas_signup(self):

        return self.is_web_app and bool(
            self.saas_signup_url
        )

    @property
    def fallback_feature_list(self):

        return [
            feature.strip()
            for feature in self.key_features.splitlines()
            if feature.strip()
        ]

    @property
    def youtube_demo_videos(self):

        videos = []

        video_fields = (
            (
                'Product Overview',
                self.youtube_overview_url,
            ),
            (
                'Installation Guide',
                self.youtube_installation_url,
            ),
            (
                'License Activation',
                self.youtube_activation_url,
            ),
        )

        for title, url in video_fields:

            embed_url = self.get_youtube_embed_url(
                url
            )

            if embed_url:

                videos.append(
                    {
                        'title': title,
                        'embed_url': embed_url,
                    }
                )

        return videos

    def get_youtube_embed_url(self, url):

        if not url:

            return ''

        parsed_url = urlparse(
            url
        )

        hostname = parsed_url.hostname or ''

        if 'youtu.be' in hostname:

            video_id = parsed_url.path.strip('/')

        elif 'youtube.com' in hostname:

            if parsed_url.path.startswith('/embed/'):

                return url

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


class SoftwareProductFeature(models.Model):

    product = models.ForeignKey(
        SoftwareProduct,
        on_delete=models.CASCADE,
        related_name='features'
    )

    title = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True
    )

    sort_order = models.PositiveIntegerField(
        default=0
    )

    class Meta:

        ordering = (
            'sort_order',
            'title',
        )

    def __str__(self):

        return self.title


class SoftwareProductScreenshot(models.Model):

    product = models.ForeignKey(
        SoftwareProduct,
        on_delete=models.CASCADE,
        related_name='screenshots'
    )

    image = models.ImageField(
        upload_to='software/screenshots/'
    )

    caption = models.CharField(
        max_length=200,
        blank=True
    )

    sort_order = models.PositiveIntegerField(
        default=0
    )

    class Meta:

        ordering = (
            'sort_order',
            'id',
        )

    def __str__(self):

        return self.caption or f'{self.product.name} screenshot'


class SoftwareProductFAQ(models.Model):

    product = models.ForeignKey(
        SoftwareProduct,
        on_delete=models.CASCADE,
        related_name='faqs'
    )

    question = models.CharField(
        max_length=255
    )

    answer = models.TextField()

    sort_order = models.PositiveIntegerField(
        default=0
    )

    class Meta:

        ordering = (
            'sort_order',
            'question',
        )

    def __str__(self):

        return self.question


class SoftwareOrder(models.Model):

    class PaymentStatus(models.TextChoices):

        PENDING = 'Pending', 'Pending'

        PAID = 'Paid', 'Paid'

        REJECTED = 'Rejected', 'Rejected'

    customer_name = models.CharField(
        max_length=200
    )

    customer_phone = models.CharField(
        max_length=50
    )

    customer_email = models.EmailField()

    business_name = models.CharField(
        max_length=200,
        blank=True
    )

    product = models.ForeignKey(
        SoftwareProduct,
        on_delete=models.PROTECT,
        related_name='orders'
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=100
    )

    payment_reference = models.CharField(
        max_length=200,
        blank=True
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )
    
    license_email_sent = models.BooleanField(
        default=False
    )

    class Meta:

        ordering = (
            '-created_at',
        )

    def __str__(self):

        return f'{self.customer_name} - {self.product.name}'


class SoftwareLicense(models.Model):

    license_key = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    order = models.ForeignKey(
        SoftwareOrder,
        on_delete=models.CASCADE,
        related_name='licenses'
    )

    product = models.ForeignKey(
        SoftwareProduct,
        on_delete=models.PROTECT,
        related_name='licenses'
    )

    customer_name = models.CharField(
        max_length=200
    )

    customer_email = models.EmailField()

    allowed_devices = models.PositiveIntegerField(
        default=1
    )

    expiry_date = models.DateField(
        default=default_license_expiry_date
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = (
            '-created_at',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'order',
                ),
                name='unique_license_per_order'
            ),
        )

    def __str__(self):

        return str(self.license_key)


class LicenseActivation(models.Model):

    license = models.ForeignKey(
        SoftwareLicense,
        on_delete=models.CASCADE,
        related_name='activations'
    )

    device_id = models.CharField(
        max_length=255
    )

    device_name = models.CharField(max_length=255, blank=True)
    windows_user = models.CharField(max_length=255, blank=True)
    os_name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    
    activated_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = (
            '-activated_at',
        )

        constraints = (
            models.UniqueConstraint(
                fields=(
                    'license',
                    'device_id',
                ),
                name='unique_activation_per_license_device'
            ),
        )

    def __str__(self):

        return f'{self.license_id} - {self.device_id}'


class SoftwareDownloadLog(models.Model):

    order = models.ForeignKey(
        SoftwareOrder,
        on_delete=models.CASCADE,
        related_name='download_logs'
    )

    product = models.ForeignKey(
        SoftwareProduct,
        on_delete=models.CASCADE,
        related_name='download_logs'
    )

    customer_email = models.EmailField()

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )

    downloaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = (
            '-downloaded_at',
        )

    def __str__(self):

        return f'{self.customer_email} - {self.product.name}'


class PaymentSetting(models.Model):

    mpesa_business_number = models.CharField(
        max_length=100,
        blank=True
    )

    mpesa_account_name = models.CharField(
        max_length=200,
        blank=True
    )

    airtel_money_number = models.CharField(
        max_length=100,
        blank=True
    )

    airtel_money_name = models.CharField(
        max_length=200,
        blank=True
    )

    mixx_number = models.CharField(
        max_length=100,
        blank=True
    )

    mixx_name = models.CharField(
        max_length=200,
        blank=True
    )

    bank_name = models.CharField(
        max_length=200,
        blank=True
    )

    bank_account_number = models.CharField(
        max_length=100,
        blank=True
    )

    bank_account_name = models.CharField(
        max_length=200,
        blank=True
    )

    instructions = models.TextField(
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return "Payment Settings"
