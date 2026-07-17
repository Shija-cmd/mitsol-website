from django.contrib import admin
from .models import PaymentSetting
from django.urls import reverse
from django.utils.html import format_html
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from .models import (
    LicenseActivation,
    SoftwareDownloadLog,
    SoftwareLicense,
    SoftwareOrder,
    SoftwareProductFAQ,
    SoftwareProductFeature,
    SoftwareProductScreenshot,
    SoftwareProduct,
)


class SoftwareProductFeatureInline(admin.TabularInline):

    model = SoftwareProductFeature

    extra = 1


class SoftwareProductScreenshotInline(admin.TabularInline):

    model = SoftwareProductScreenshot

    extra = 1


class SoftwareProductFAQInline(admin.TabularInline):

    model = SoftwareProductFAQ

    extra = 1


@admin.register(SoftwareProduct)
class SoftwareProductAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'delivery_type',
        'sales_flow',
        'version',
        'price',
        'is_active',
        'updated_at',
    )

    list_filter = (
        'delivery_type',
        'sales_flow',
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

    inlines = (
        SoftwareProductFeatureInline,
        SoftwareProductScreenshotInline,
        SoftwareProductFAQInline,
    )

    fieldsets = (
        (
            'Product Information',
            {
                'fields': (
                    'name',
                    'slug',
                    'delivery_type',
                    'sales_flow',
                    'description',
                    'version',
                    'price',
                    'is_active',
                )
            }
        ),
        (
            'Delivery Links',
            {
                'fields': (
                    'proton_drive_link',
                    'proton_drive_password',
                    'saas_signup_url',
                )
            }
        ),
        (
            'Product Content',
            {
                'fields': (
                    'release_notes',
                    'key_features',
                    'youtube_overview_url',
                    'youtube_installation_url',
                    'youtube_activation_url',
                )
            }
        ),
    )


@admin.register(SoftwareOrder)
class SoftwareOrderAdmin(admin.ModelAdmin):

    list_display = (
        'customer_name',
        'customer_email',
        'product',
        'amount',
        'payment_method',
        'payment_status',
        'license_email_sent',
        'download_link',
        'created_at',
    )

    list_filter = (
        'payment_status',
        'payment_method',
        'product__delivery_type',
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
        'download_link',
        'license_email_sent',
    )

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.payment_status != SoftwareOrder.PaymentStatus.PAID:
            return

        updated = SoftwareOrder.objects.filter(
            pk=obj.pk,
            license_email_sent=False
        ).update(
            license_email_sent=True
        )

        if not updated:
            return

        if obj.product.delivery_type == SoftwareProduct.DeliveryType.WEB_APP:
            self.send_web_app_deployment_email(obj)
            return

        license_obj, created = SoftwareLicense.objects.get_or_create(
            order=obj,
            defaults={
                "product": obj.product,
                "customer_name": obj.customer_name,
                "customer_email": obj.customer_email,
            }
        )

        self.send_license_email(request, obj, license_obj)

    def download_link(self, obj):
        if obj.product.delivery_type == SoftwareProduct.DeliveryType.WEB_APP:
            return "Web application - no download link"

        if obj.payment_status != SoftwareOrder.PaymentStatus.PAID:
            return "Payment is not approved yet"

        license_obj = obj.licenses.first()

        if not license_obj:
            return "No license generated yet"

        url = reverse(
            "download_software",
            args=[license_obj.license_key]
        )

        return format_html(
            '<a href="{}" target="_blank">Open Download Page</a><br>'
            '<small>{}</small>',
            url,
            url
        )

    download_link.short_description = "Download Link"
    
    def send_license_email(self, request, order, license_obj):
        download_url = reverse(
            "download_software",
            args=[license_obj.license_key]
        )

        full_url = self.build_absolute_url(
            request,
            download_url
        )

        subject = f"Your {order.product.name} License is Ready"

        context = {
            "customer_name": order.customer_name,
            "product_name": order.product.name,
            "product_version": order.product.version,
            "license_key": license_obj.license_key,
            "download_url": full_url,
            "support_email": "info@mitsol.com.se",
            "company_name": "MITSOL Company Limited",
            "website_url": settings.SITE_URL,
        }

        text_message = f"""
            Dear {order.customer_name},

            Thank you for purchasing {order.product.name}.

            Your payment has been confirmed.

            Product: {order.product.name}
            Version: {order.product.version}

            License Key:
                {license_obj.license_key}

            Download Software:
                {full_url}

            Please keep this license key safe. You will need it to activate the software after installation.

            Support:
            info@mitsol.com.se

            MITSOL Company Limited
            Website: 
            {settings.SITE_URL}
            """

        html_message = render_to_string(
            "software_store/emails/license_ready.html",
            context
        )

        email = EmailMultiAlternatives(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [order.customer_email],
        )

        email.attach_alternative(html_message, "text/html")
        email.send()

    def build_absolute_url(self, request, path):
        if request:
            return request.build_absolute_uri(
                path
            )

        return f"{settings.SITE_URL}{path}"

    def send_web_app_deployment_email(self, order):
        subject = (
            "Your MITSOL Hospital Management System Order Has Been Confirmed"
        )

        context = {
            "customer_name": order.customer_name,
            "product_name": order.product.name,
            "website_url": settings.SITE_URL,
            "support_email": "info@mitsol.com.se",
            "company_name": "MITSOL Company Limited",
        }

        text_message = f"""
Dear {order.customer_name},

Thank you for purchasing {order.product.name}.

Your payment has been confirmed successfully.

This product is a secure web-based application. Our implementation team will contact you shortly to deploy and configure your system.

You will receive:

- Your secure system URL
- Administrator username
- Temporary password
- Initial system configuration
- User guide
- Technical support

Deployment normally begins within 24 hours after payment confirmation.

Thank you for choosing MITSOL Company Limited.

Website:
{settings.SITE_URL}

Email:
info@mitsol.com.se
"""

        html_message = render_to_string(
            "software_store/emails/web_app_confirmed.html",
            context
        )

        email = EmailMultiAlternatives(
            subject,
            text_message,
            settings.DEFAULT_FROM_EMAIL,
            [order.customer_email],
        )

        email.attach_alternative(html_message, "text/html")
        email.send()


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
        "license",
        "device_name",
        "windows_user",
        "os_name",
        "is_active",
        "activated_at",
    )

    list_filter = (
        "is_active",
        "os_name",
        "activated_at",
    )

    search_fields = (
        "license__customer_name",
        "device_id",
        "device_name",
        "windows_user",
    )

    actions = [
        "deactivate_devices",
    ]

    def deactivate_devices(self, request, queryset):
        queryset.update(is_active=False)

    deactivate_devices.short_description = "Deactivate selected devices"


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


@admin.register(PaymentSetting)
class PaymentSettingAdmin(admin.ModelAdmin):
    list_display = (
        "mpesa_business_number",
        "airtel_money_number",
        "mixx_number",
        "bank_name",
        "updated_at",
    )
