from django.contrib import admin

from .models import (
    LicenseActivation,
    SoftwareDownloadLog,
    SoftwareLicense,
    SoftwareOrder,
    SoftwareProduct,
)


@admin.register(SoftwareProduct)
class SoftwareProductAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'version',
        'price',
        'is_active',
        'updated_at',
    )

    list_filter = (
        'is_active',
        'created_at',
    )

    search_fields = (
        'name',
        'slug',
        'description',
    )

    prepopulated_fields = {
        'slug': (
            'name',
        )
    }


@admin.register(SoftwareOrder)
class SoftwareOrderAdmin(admin.ModelAdmin):

    list_display = (
        'customer_name',
        'customer_email',
        'product',
        'amount',
        'payment_method',
        'payment_status',
        'created_at',
    )

    list_filter = (
        'payment_status',
        'payment_method',
        'product',
        'created_at',
    )

    search_fields = (
        'customer_name',
        'customer_email',
        'customer_phone',
        'business_name',
        'payment_reference',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )


@admin.register(SoftwareLicense)
class SoftwareLicenseAdmin(admin.ModelAdmin):

    list_display = (
        'license_key',
        'customer_name',
        'customer_email',
        'product',
        'allowed_devices',
        'expiry_date',
        'is_active',
        'created_at',
    )

    list_filter = (
        'is_active',
        'product',
        'expiry_date',
        'created_at',
    )

    search_fields = (
        'license_key',
        'customer_name',
        'customer_email',
    )

    readonly_fields = (
        'license_key',
        'created_at',
    )


@admin.register(LicenseActivation)
class LicenseActivationAdmin(admin.ModelAdmin):

    list_display = (
        'license',
        'device_id',
        'activated_at',
    )

    list_filter = (
        'activated_at',
    )

    search_fields = (
        'license__license_key',
        'device_id',
        'license__customer_email',
    )

    readonly_fields = (
        'activated_at',
    )


@admin.register(SoftwareDownloadLog)
class SoftwareDownloadLogAdmin(admin.ModelAdmin):

    list_display = (
        'customer_email',
        'product',
        'order',
        'ip_address',
        'downloaded_at',
    )

    list_filter = (
        'product',
        'downloaded_at',
    )

    search_fields = (
        'customer_email',
        'ip_address',
        'order__customer_name',
    )

    readonly_fields = (
        'downloaded_at',
    )
