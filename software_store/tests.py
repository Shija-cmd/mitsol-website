import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    LicenseActivation,
    SoftwareLicense,
    SoftwareOrder,
    SoftwareProduct,
)


class SoftwareStoreTests(TestCase):

    def setUp(self):

        self.product = SoftwareProduct.objects.create(
            name='Pharmacy Management System',
            slug='pharmacy',
            description='Pharmacy business software.',
            version='1.0.1',
            price='100.00',
            proton_drive_link='https://drive.proton.me/urls/example',
            release_notes='Bug fixes and improvements.'
        )

    def create_paid_order(self):

        return SoftwareOrder.objects.create(
            customer_name='Jane Customer',
            customer_phone='255700000000',
            customer_email='jane@example.com',
            business_name='Jane Pharmacy',
            product=self.product,
            amount=self.product.price,
            payment_method='Mobile money',
            payment_reference='ABC123',
            payment_status=SoftwareOrder.PaymentStatus.PAID
        )

    def test_paid_order_creates_one_license(self):

        order = self.create_paid_order()
        order.payment_reference = 'ABC124'
        order.save()

        self.assertEqual(
            SoftwareLicense.objects.filter(
                order=order
            ).count(),
            1
        )

    def test_activation_respects_allowed_device_limit(self):

        order = self.create_paid_order()
        license_obj = order.licenses.first()

        first_response = self.client.post(
            reverse('software_license_activate'),
            data=json.dumps(
                {
                    'license_key': str(license_obj.license_key),
                    'device_id': 'device-1',
                }
            ),
            content_type='application/json'
        )
        second_response = self.client.post(
            reverse('software_license_activate'),
            data=json.dumps(
                {
                    'license_key': str(license_obj.license_key),
                    'device_id': 'device-2',
                }
            ),
            content_type='application/json'
        )

        self.assertEqual(
            first_response.status_code,
            200
        )
        self.assertEqual(
            second_response.status_code,
            400
        )

    def test_verify_requires_activated_device(self):

        order = self.create_paid_order()
        license_obj = order.licenses.first()
        LicenseActivation.objects.create(
            license=license_obj,
            device_id='device-1'
        )

        response = self.client.post(
            reverse('software_license_verify'),
            data=json.dumps(
                {
                    'license_key': str(license_obj.license_key),
                    'device_id': 'device-1',
                }
            ),
            content_type='application/json'
        )

        self.assertTrue(
            response.json()['valid']
        )

    def test_latest_manifest_hides_download_url_without_valid_license(self):

        response = self.client.get(
            reverse(
                'software_latest',
                args=[
                    self.product.slug,
                ]
            )
        )

        self.assertNotIn(
            'download_url',
            response.json()
        )

    def test_latest_manifest_includes_download_url_with_valid_license(self):

        order = self.create_paid_order()
        license_obj = order.licenses.first()

        response = self.client.get(
            reverse(
                'software_latest',
                args=[
                    self.product.slug,
                ]
            ),
            {
                'license_key': str(license_obj.license_key),
            }
        )

        self.assertEqual(
            response.json()['download_url'],
            self.product.proton_drive_link
        )

    def test_expired_license_cannot_verify(self):

        order = self.create_paid_order()
        license_obj = order.licenses.first()
        license_obj.expiry_date = timezone.localdate() - timedelta(days=1)
        license_obj.save()

        response = self.client.post(
            reverse('software_license_verify'),
            data=json.dumps(
                {
                    'license_key': str(license_obj.license_key),
                    'device_id': 'device-1',
                }
            ),
            content_type='application/json'
        )

        self.assertFalse(
            response.json()['valid']
        )
