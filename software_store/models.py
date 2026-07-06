import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


def default_license_expiry_date():

    return timezone.localdate() + timedelta(days=365)


class SoftwareProduct(models.Model):

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

    proton_drive_link = models.URLField(
        max_length=1000,
        blank=True
    )

    release_notes = models.TextField(
        blank=True
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
            'name',
        )

    def __str__(self):

        return self.name


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
