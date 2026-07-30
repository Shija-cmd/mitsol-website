import shutil
import tempfile

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from learning.models import (
    Course,
    CourseCategory,
    Enrolment,
    LearningPaymentSettings,
    Lesson,
    Module,
    Notification,
    Payment,
)
from learning.services import (
    confirm_payment,
    get_course_payable_amount,
    get_or_create_paid_course_enrolment,
    mark_payment_refunded,
    reject_payment,
    submit_course_payment,
    validate_payment_proof,
)


PAYMENT_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=PAYMENT_MEDIA_ROOT)
class StageFourPaymentTests(TestCase):

    @classmethod
    def tearDownClass(cls):

        super().tearDownClass()
        shutil.rmtree(PAYMENT_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):

        self.student = User.objects.create_user(
            username='payment_student',
            password='pass12345',
            email='student@example.com',
        )
        self.other_student = User.objects.create_user(
            username='other_payment_student',
            password='pass12345',
        )
        self.instructor = User.objects.create_user(
            username='payment_instructor',
            password='pass12345',
        )
        self.other_instructor = User.objects.create_user(
            username='other_payment_instructor',
            password='pass12345',
        )
        self.admin = User.objects.create_superuser(
            username='payment_admin',
            email='admin@example.com',
            password='pass12345',
        )

        instructor_group, created = Group.objects.get_or_create(
            name='Instructor'
        )
        self.instructor.groups.add(
            instructor_group
        )
        self.other_instructor.groups.add(
            instructor_group
        )

        self.category = CourseCategory.objects.create(
            name='Payment Category'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Paid Django Course',
            short_description='A paid course.',
            full_description='A paid course description.',
            status=Course.Status.PUBLISHED,
            is_free=False,
            price=120000,
            discount_price=100000,
        )
        self.other_course = Course.objects.create(
            instructor=self.other_instructor,
            category=self.category,
            title='Other Paid Course',
            short_description='Another paid course.',
            full_description='Another paid course description.',
            status=Course.Status.PUBLISHED,
            is_free=False,
            price=90000,
        )
        self.free_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Free Course',
            short_description='A free course.',
            full_description='A free course description.',
            status=Course.Status.PUBLISHED,
            is_free=True,
        )

        self.module = Module.objects.create(
            course=self.course,
            title='Payment Module',
            order=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Paid Lesson',
            slug='paid-lesson',
            order=1,
            is_preview=False,
        )

        self.other_module = Module.objects.create(
            course=self.other_course,
            title='Other Payment Module',
            order=1
        )
        self.other_lesson = Lesson.objects.create(
            module=self.other_module,
            title='Other Paid Lesson',
            slug='other-paid-lesson',
            order=1,
            is_preview=False,
        )

        self.free_module = Module.objects.create(
            course=self.free_course,
            title='Free Module',
            order=1
        )
        self.free_lesson = Lesson.objects.create(
            module=self.free_module,
            title='Free Lesson',
            slug='free-lesson',
            order=1,
            is_preview=False,
        )

        LearningPaymentSettings.objects.create(
            currency='TZS',
            mpesa_business_number='123456',
            mpesa_account_name='MITSOL',
            general_payment_instructions='Pay then submit the transaction reference.',
            require_proof_for_mobile_money=True,
            is_active=True,
        )

    def proof_file(self, name='proof.pdf'):

        return SimpleUploadedFile(
            name,
            b'%PDF-1.4 payment proof',
            content_type='application/pdf'
        )

    def payment_data(self, reference='PAY123'):

        return {
            'payment_method': Payment.PaymentMethod.MPESA,
            'transaction_reference': reference,
            'proof_of_payment': self.proof_file(f'{reference}.pdf'),
            'student_notes': 'Paid through mobile money.',
        }

    def create_pending_payment(self, reference='PAY123', course=None, student=None):

        course = course or self.course
        student = student or self.student
        enrolment, created = get_or_create_paid_course_enrolment(
            student,
            course
        )
        return submit_course_payment(
            student,
            enrolment,
            self.payment_data(reference)
        )

    def test_free_course_enrolment_still_activates_without_payment(self):

        self.client.login(
            username='payment_student',
            password='pass12345'
        )

        response = self.client.get(
            reverse('learning:enrol', args=[self.free_course.slug])
        )

        self.assertRedirects(
            response,
            reverse('learning:course_detail', args=[self.free_course.slug])
        )
        enrolment = Enrolment.objects.get(
            student=self.student,
            course=self.free_course
        )
        self.assertEqual(
            enrolment.status,
            Enrolment.Status.ACTIVE
        )
        self.assertEqual(
            enrolment.payment_status,
            Enrolment.PaymentStatus.NOT_REQUIRED
        )
        self.assertTrue(
            enrolment.is_active
        )

    def test_paid_course_enrolment_creates_pending_inactive_record(self):

        enrolment, created = get_or_create_paid_course_enrolment(
            self.student,
            self.course
        )

        self.assertTrue(created)
        self.assertEqual(
            enrolment.status,
            Enrolment.Status.PENDING
        )
        self.assertEqual(
            enrolment.payment_status,
            Enrolment.PaymentStatus.PENDING
        )
        self.assertFalse(
            enrolment.is_active
        )

    def test_pending_paid_enrolment_cannot_access_private_lesson(self):

        get_or_create_paid_course_enrolment(
            self.student,
            self.course
        )
        self.client.login(
            username='payment_student',
            password='pass12345'
        )

        response = self.client.get(
            reverse(
                'learning:lesson_detail',
                args=[
                    self.course.slug,
                    self.lesson.slug,
                ]
            )
        )

        self.assertRedirects(
            response,
            reverse('learning:course_detail', args=[self.course.slug])
        )

    def test_payment_submission_uses_server_amount_and_notifies(self):

        payment = self.create_pending_payment()

        self.assertEqual(
            payment.amount,
            self.course.discount_price
        )
        self.assertEqual(
            payment.currency,
            'TZS'
        )
        self.assertEqual(
            payment.status,
            Payment.Status.PENDING
        )
        self.assertEqual(
            payment.original_filename,
            'PAY123.pdf'
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                title='Payment submitted'
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.admin,
                title='Payment awaiting verification'
            ).exists()
        )

    def test_price_calculation_uses_discount_and_rejects_invalid_discount(self):

        self.assertEqual(
            get_course_payable_amount(self.course),
            self.course.discount_price
        )

        self.course.discount_price = 130000
        with self.assertRaises(ValidationError):
            get_course_payable_amount(self.course)

    def test_duplicate_pending_submission_returns_existing_payment(self):

        first_payment = self.create_pending_payment('PAY124')
        enrolment = first_payment.enrolment

        second_payment = submit_course_payment(
            self.student,
            enrolment,
            self.payment_data('PAY125')
        )

        self.assertEqual(
            first_payment.pk,
            second_payment.pk
        )
        self.assertEqual(
            Payment.objects.filter(enrolment=enrolment).count(),
            1
        )

    def test_confirm_payment_activates_course_access(self):

        payment = self.create_pending_payment('PAY126')

        confirm_payment(
            payment,
            self.admin
        )

        payment.refresh_from_db()
        payment.enrolment.refresh_from_db()
        self.assertEqual(
            payment.status,
            Payment.Status.PAID
        )
        self.assertEqual(
            payment.enrolment.status,
            Enrolment.Status.ACTIVE
        )
        self.assertEqual(
            payment.enrolment.payment_status,
            Enrolment.PaymentStatus.PAID
        )
        self.assertTrue(
            payment.enrolment.is_active
        )

        self.client.login(
            username='payment_student',
            password='pass12345'
        )
        response = self.client.get(
            reverse(
                'learning:lesson_detail',
                args=[
                    self.course.slug,
                    self.lesson.slug,
                ]
            )
        )
        self.assertEqual(
            response.status_code,
            200
        )

    def test_instructor_cannot_confirm_payment(self):

        payment = self.create_pending_payment('PAY133')

        with self.assertRaises(PermissionDenied):
            confirm_payment(
                payment,
                self.instructor
            )

    def test_rejected_payment_keeps_access_inactive_and_allows_new_reference(self):

        payment = self.create_pending_payment('PAY127')

        reject_payment(
            payment,
            self.admin,
            'Reference does not match received payment.'
        )
        payment.refresh_from_db()
        payment.enrolment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.REJECTED
        )
        self.assertEqual(
            payment.enrolment.payment_status,
            Enrolment.PaymentStatus.REJECTED
        )
        self.assertFalse(
            payment.enrolment.is_active
        )

        new_payment = submit_course_payment(
            self.student,
            payment.enrolment,
            self.payment_data('PAY128')
        )

        self.assertNotEqual(
            payment.pk,
            new_payment.pk
        )
        self.assertEqual(
            new_payment.status,
            Payment.Status.PENDING
        )
        new_payment.enrolment.refresh_from_db()
        self.assertEqual(
            new_payment.enrolment.payment_status,
            Enrolment.PaymentStatus.PENDING
        )

    def test_payment_proof_validation_rejects_dangerous_files(self):

        with self.assertRaises(ValidationError):
            validate_payment_proof(
                SimpleUploadedFile(
                    'proof.exe',
                    b'dangerous',
                    content_type='application/octet-stream'
                ),
                required=True
            )

    def test_admin_confirm_view_activates_payment(self):

        payment = self.create_pending_payment('PAY129')
        self.client.login(
            username='payment_admin',
            password='pass12345'
        )

        response = self.client.post(
            reverse('learning:admin_payment_confirm', args=[payment.pk])
        )

        self.assertRedirects(
            response,
            reverse('learning:admin_payment_detail', args=[payment.pk])
        )
        payment.refresh_from_db()
        self.assertEqual(
            payment.status,
            Payment.Status.PAID
        )

    def test_refund_suspends_access_and_blocks_private_lesson(self):

        payment = self.create_pending_payment('PAY134')
        confirm_payment(
            payment,
            self.admin
        )
        mark_payment_refunded(
            payment,
            self.admin,
            'Customer requested a refund.'
        )
        payment.refresh_from_db()
        payment.enrolment.refresh_from_db()

        self.assertEqual(
            payment.status,
            Payment.Status.REFUNDED
        )
        self.assertEqual(
            payment.enrolment.status,
            Enrolment.Status.SUSPENDED
        )
        self.assertFalse(
            payment.enrolment.is_active
        )

        self.client.login(
            username='payment_student',
            password='pass12345'
        )
        response = self.client.get(
            reverse(
                'learning:lesson_detail',
                args=[
                    self.course.slug,
                    self.lesson.slug,
                ]
            )
        )
        self.assertRedirects(
            response,
            reverse('learning:course_detail', args=[self.course.slug])
        )

    def test_instructor_payment_list_only_shows_owned_course_payments(self):

        own_payment = self.create_pending_payment('PAY130')
        other_payment = self.create_pending_payment(
            'PAY131',
            course=self.other_course,
            student=self.other_student
        )
        self.client.login(
            username='payment_instructor',
            password='pass12345'
        )

        response = self.client.get(
            reverse('learning:instructor_payment_list')
        )

        self.assertEqual(
            response.status_code,
            200
        )
        self.assertContains(
            response,
            own_payment.transaction_reference
        )
        self.assertNotContains(
            response,
            other_payment.transaction_reference
        )

    def test_student_cannot_download_other_student_payment_proof(self):

        payment = self.create_pending_payment('PAY132')
        self.client.login(
            username='other_payment_student',
            password='pass12345'
        )

        response = self.client.get(
            reverse('learning:payment_proof', args=[payment.pk])
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_student_cannot_view_other_student_payment_detail(self):

        payment = self.create_pending_payment('PAY135')
        self.client.login(
            username='other_payment_student',
            password='pass12345'
        )

        response = self.client.get(
            reverse('learning:payment_detail', args=[payment.pk])
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_paid_course_enrol_button_opens_payment_page(self):

        self.client.login(
            username='payment_student',
            password='pass12345'
        )

        response = self.client.get(
            reverse('learning:enrol', args=[self.course.slug])
        )

        self.assertRedirects(
            response,
            reverse('learning:payment_course', args=[self.course.slug])
        )
