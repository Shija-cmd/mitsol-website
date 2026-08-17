from io import StringIO

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from learning.models import (
    Assignment,
    AssignmentSubmission,
    Certificate,
    Course,
    CourseCategory,
    Enrolment,
    Lesson,
    LessonProgress,
    Module,
    Notification,
    Quiz,
    QuizAttempt,
)
from learning.services import (
    approve_certificate,
    evaluate_course_completion,
    generate_certificate_pdf,
    issue_certificate,
    restore_certificate,
    revoke_certificate,
)


class StageSixCertificateTests(TestCase):

    def setUp(self):
        self.student = User.objects.create_user(
            username='certificate_student',
            password='pass12345',
            first_name='Certificate',
            last_name='Student',
            email='student@example.com',
        )
        self.other_student = User.objects.create_user(
            username='other_certificate_student',
            password='pass12345',
        )
        self.instructor = User.objects.create_user(
            username='certificate_instructor',
            password='pass12345',
        )
        self.other_instructor = User.objects.create_user(
            username='other_certificate_instructor',
            password='pass12345',
        )
        self.staff = User.objects.create_user(
            username='certificate_staff',
            password='pass12345',
            is_staff=True,
        )
        self.admin = User.objects.create_superuser(
            username='certificate_admin',
            email='admin@example.com',
            password='pass12345',
        )

        instructor_group, created = Group.objects.get_or_create(
            name='Instructor'
        )
        self.instructor.groups.add(instructor_group)
        self.other_instructor.groups.add(instructor_group)

        self.category = CourseCategory.objects.create(
            name='Certificate Category'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Certificate Course',
            short_description='A certificate course.',
            full_description='A certificate course description.',
            status=Course.Status.PUBLISHED,
            is_published=True,
            is_free=True,
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Certificate Module',
            order=1
        )
        self.content_lesson = Lesson.objects.create(
            module=self.module,
            title='Certificate Lesson',
            slug='certificate-lesson',
            order=1,
            is_compulsory=True,
        )
        self.quiz_lesson = Lesson.objects.create(
            module=self.module,
            title='Certificate Quiz Lesson',
            slug='certificate-quiz-lesson',
            order=2,
            lesson_type=Lesson.LessonType.QUIZ,
            is_compulsory=True,
        )
        self.quiz = Quiz.objects.create(
            lesson=self.quiz_lesson,
            title='Certificate Quiz',
            is_published=True,
            passing_score=50,
        )
        self.assignment_lesson = Lesson.objects.create(
            module=self.module,
            title='Certificate Assignment Lesson',
            slug='certificate-assignment-lesson',
            order=3,
            lesson_type=Lesson.LessonType.ASSIGNMENT,
            is_compulsory=True,
        )
        self.assignment = Assignment.objects.create(
            lesson=self.assignment_lesson,
            title='Certificate Assignment',
            instructions='Submit practical work.',
            is_published=True,
            passing_score=50,
        )
        self.enrolment = Enrolment.objects.create(
            student=self.student,
            course=self.course,
            status=Enrolment.Status.ACTIVE,
            payment_status=Enrolment.PaymentStatus.NOT_REQUIRED,
            is_active=True,
        )

        self.other_course = Course.objects.create(
            instructor=self.other_instructor,
            category=self.category,
            title='Other Certificate Course',
            short_description='Another certificate course.',
            full_description='Another certificate course description.',
            status=Course.Status.PUBLISHED,
            is_published=True,
            is_free=True,
        )
        self.other_module = Module.objects.create(
            course=self.other_course,
            title='Other Module',
            order=1
        )
        self.other_lesson = Lesson.objects.create(
            module=self.other_module,
            title='Other Lesson',
            slug='other-lesson',
            order=1,
            is_compulsory=True,
        )
        self.other_enrolment = Enrolment.objects.create(
            student=self.other_student,
            course=self.other_course,
            status=Enrolment.Status.ACTIVE,
            payment_status=Enrolment.PaymentStatus.NOT_REQUIRED,
            is_active=True,
        )

    def complete_content_lesson(self, enrolment=None, lesson=None):
        enrolment = enrolment or self.enrolment
        lesson = lesson or self.content_lesson
        return LessonProgress.objects.create(
            student=enrolment.student,
            enrolment=enrolment,
            lesson=lesson,
            is_completed=True,
        )

    def pass_quiz(self):
        return QuizAttempt.objects.create(
            student=self.student,
            quiz=self.quiz,
            enrolment=self.enrolment,
            attempt_number=1,
            status=QuizAttempt.Status.GRADED,
            total_possible_marks=100,
            total_marks_awarded=80,
            percentage=80,
            passed=True,
        )

    def pass_assignment(self):
        return AssignmentSubmission.objects.create(
            assignment=self.assignment,
            student=self.student,
            enrolment=self.enrolment,
            attempt_number=1,
            submission_text='Completed assignment.',
            status=AssignmentSubmission.Status.GRADED,
            score=80,
            passed=True,
        )

    def complete_all_requirements(self):
        self.complete_content_lesson()
        self.pass_quiz()
        self.pass_assignment()

    def test_completion_requires_content_quiz_and_assignment_passes(self):
        result = evaluate_course_completion(self.enrolment)

        self.assertFalse(result.completed)
        self.assertIn('Lesson incomplete: Certificate Lesson', result.missing_requirements)
        self.assertIn('Quiz not passed: Certificate Quiz Lesson', result.missing_requirements)
        self.assertIn('Assignment not passed: Certificate Assignment Lesson', result.missing_requirements)
        self.assertEqual(Certificate.objects.count(), 0)

        self.complete_content_lesson()
        self.pass_quiz()
        result = evaluate_course_completion(self.enrolment)

        self.assertFalse(result.completed)
        self.assertIn('Assignment not passed: Certificate Assignment Lesson', result.missing_requirements)

        self.pass_assignment()
        result = evaluate_course_completion(self.enrolment)

        self.assertTrue(result.completed)
        self.enrolment.refresh_from_db()
        self.assertEqual(self.enrolment.status, Enrolment.Status.COMPLETED)
        self.assertEqual(self.enrolment.progress_percentage, 100)
        self.assertIsNotNone(self.enrolment.completed_at)
        self.assertEqual(Certificate.objects.count(), 1)

    def test_issue_certificate_is_idempotent_and_creates_notification(self):
        self.complete_all_requirements()
        evaluate_course_completion(self.enrolment)

        certificate = Certificate.objects.get()
        duplicate = issue_certificate(self.enrolment)

        self.assertEqual(certificate.pk, duplicate.pk)
        self.assertEqual(Certificate.objects.count(), 1)
        self.assertEqual(
            certificate.approval_status,
            Certificate.ApprovalStatus.PENDING,
        )
        self.assertFalse(certificate.is_valid)
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                title='Certificate awaiting approval'
            ).exists()
        )

    def test_paid_course_requires_paid_status_for_certificate(self):
        paid_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Paid Certificate Course',
            short_description='Paid certificate course.',
            full_description='Paid certificate course description.',
            status=Course.Status.PUBLISHED,
            is_published=True,
            is_free=False,
            price=100000,
        )
        enrolment = Enrolment.objects.create(
            student=self.student,
            course=paid_course,
            status=Enrolment.Status.COMPLETED,
            payment_status=Enrolment.PaymentStatus.PENDING,
            is_active=True,
        )

        with self.assertRaises(ValidationError):
            issue_certificate(enrolment)

    def test_certificate_pdf_and_public_verification(self):
        self.complete_all_requirements()
        result = evaluate_course_completion(self.enrolment)
        certificate = result.certificate
        approve_certificate(certificate, self.admin)

        pdf = generate_certificate_pdf(certificate)
        self.assertTrue(pdf.startswith(b'%PDF'))

        response = self.client.get(
            reverse('learning:certificate_verify_code', args=[certificate.verification_code])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This certificate is valid.')
        self.assertContains(response, certificate.certificate_number)
        self.assertNotContains(response, 'student@example.com')

    def test_student_can_download_own_valid_certificate_only(self):
        self.complete_all_requirements()
        certificate = evaluate_course_completion(self.enrolment).certificate

        self.client.login(username='certificate_student', password='pass12345')
        response = self.client.get(
            reverse('learning:certificate_download', args=[certificate.pk])
        )
        self.assertEqual(response.status_code, 404)

        certificate = approve_certificate(certificate, self.admin)
        response = self.client.get(
            reverse('learning:certificate_download', args=[certificate.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        self.client.login(username='other_certificate_student', password='pass12345')
        response = self.client.get(
            reverse('learning:certificate_download', args=[certificate.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_revoked_certificate_is_visible_but_not_publicly_downloadable(self):
        self.complete_all_requirements()
        certificate = evaluate_course_completion(self.enrolment).certificate
        certificate = approve_certificate(certificate, self.admin)

        revoked = revoke_certificate(certificate, self.admin, 'Issued in error.')
        self.assertFalse(revoked.is_valid)

        self.client.login(username='certificate_student', password='pass12345')
        response = self.client.get(
            reverse('learning:certificate_detail', args=[certificate.pk])
        )
        self.assertContains(response, 'Revoked')

        response = self.client.get(
            reverse('learning:certificate_download', args=[certificate.pk])
        )
        self.assertEqual(response.status_code, 404)

        restored = restore_certificate(certificate, self.admin)
        self.assertTrue(restored.is_valid)

    def test_only_admin_can_revoke_restore_certificates(self):
        self.complete_all_requirements()
        certificate = evaluate_course_completion(self.enrolment).certificate
        certificate = approve_certificate(certificate, self.admin)

        with self.assertRaises(PermissionDenied):
            revoke_certificate(certificate, self.instructor, 'Invalid.')

        with self.assertRaises(PermissionDenied):
            revoke_certificate(certificate, self.staff, 'Invalid.')

    def test_instructor_certificate_list_is_limited_to_owned_courses(self):
        self.complete_all_requirements()
        own_certificate = evaluate_course_completion(self.enrolment).certificate
        self.complete_content_lesson(self.other_enrolment, self.other_lesson)
        other_certificate = evaluate_course_completion(self.other_enrolment).certificate

        self.client.login(username='certificate_instructor', password='pass12345')
        response = self.client.get(reverse('learning:instructor_certificate_list'))

        self.assertContains(response, own_certificate.certificate_number)
        self.assertNotContains(response, other_certificate.certificate_number)
        self.assertNotContains(response, 'other_certificate_student')

    def test_admin_certificate_views_revoke_restore_and_download(self):
        self.complete_all_requirements()
        certificate = evaluate_course_completion(self.enrolment).certificate
        self.client.login(username='certificate_admin', password='pass12345')

        response = self.client.get(reverse('learning:admin_certificate_list'))
        self.assertContains(response, certificate.certificate_number)

        response = self.client.get(
            reverse('learning:admin_certificate_download', args=[certificate.pk])
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            reverse('learning:admin_certificate_approve', args=[certificate.pk])
        )
        self.assertRedirects(
            response,
            reverse('learning:admin_certificate_detail', args=[certificate.pk])
        )
        certificate.refresh_from_db()
        self.assertEqual(
            certificate.approval_status,
            Certificate.ApprovalStatus.APPROVED,
        )
        self.assertTrue(certificate.is_valid)

        response = self.client.get(
            reverse('learning:admin_certificate_download', args=[certificate.pk])
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('learning:admin_certificate_revoke', args=[certificate.pk]),
            {'reason': 'Administrative correction.'}
        )
        self.assertRedirects(
            response,
            reverse('learning:admin_certificate_detail', args=[certificate.pk])
        )
        certificate.refresh_from_db()
        self.assertFalse(certificate.is_valid)

        response = self.client.post(
            reverse('learning:admin_certificate_restore', args=[certificate.pk])
        )
        self.assertRedirects(
            response,
            reverse('learning:admin_certificate_detail', args=[certificate.pk])
        )
        certificate.refresh_from_db()
        self.assertTrue(certificate.is_valid)

    def test_issue_missing_certificates_command(self):
        self.complete_all_requirements()
        self.enrolment.status = Enrolment.Status.COMPLETED
        self.enrolment.progress_percentage = 100
        self.enrolment.save()
        output = StringIO()

        call_command('issue_missing_certificates', stdout=output)

        self.assertEqual(Certificate.objects.count(), 1)
        self.assertIn('Generated pending certificate', output.getvalue())
