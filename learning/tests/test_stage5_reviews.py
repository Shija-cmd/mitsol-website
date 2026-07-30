from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from learning.models import (
    Course,
    CourseCategory,
    CourseReview,
    Enrolment,
    Lesson,
    Module,
    Notification,
)
from learning.services import (
    approve_course_review,
    can_student_review_course,
    create_course_review,
    get_course_rating_summary,
    hide_course_review,
    reject_course_review,
    update_course_review,
)


class StageFiveReviewTests(TestCase):

    def setUp(self):

        self.student = User.objects.create_user(
            username='review_student',
            password='pass12345',
            first_name='Review',
            last_name='Student',
            email='student@example.com',
        )
        self.other_student = User.objects.create_user(
            username='other_review_student',
            password='pass12345',
            email='other@example.com',
        )
        self.instructor = User.objects.create_user(
            username='review_instructor',
            password='pass12345',
        )
        self.other_instructor = User.objects.create_user(
            username='other_review_instructor',
            password='pass12345',
        )
        self.staff = User.objects.create_user(
            username='review_staff',
            password='pass12345',
            is_staff=True,
        )
        self.admin = User.objects.create_superuser(
            username='review_admin',
            email='admin@example.com',
            password='pass12345',
        )

        instructor_group, created = Group.objects.get_or_create(
            name='Instructor'
        )
        self.instructor.groups.add(instructor_group)
        self.other_instructor.groups.add(instructor_group)

        self.category = CourseCategory.objects.create(
            name='Review Category'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Review Course',
            short_description='Reviewable course.',
            full_description='Review course description.',
            status=Course.Status.PUBLISHED,
            is_free=True,
        )
        self.paid_course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Paid Review Course',
            short_description='Paid reviewable course.',
            full_description='Paid review course description.',
            status=Course.Status.PUBLISHED,
            is_free=False,
            price=100000,
        )
        self.other_course = Course.objects.create(
            instructor=self.other_instructor,
            category=self.category,
            title='Other Review Course',
            short_description='Other reviewable course.',
            full_description='Other review course description.',
            status=Course.Status.PUBLISHED,
            is_free=True,
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Review Module',
            order=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Review Lesson',
            slug='review-lesson',
            order=1,
            is_compulsory=True,
        )
        self.enrolment = Enrolment.objects.create(
            student=self.student,
            course=self.course,
            status=Enrolment.Status.ACTIVE,
            payment_status=Enrolment.PaymentStatus.NOT_REQUIRED,
            is_active=True,
            progress_percentage=25,
        )
        self.paid_enrolment = Enrolment.objects.create(
            student=self.student,
            course=self.paid_course,
            status=Enrolment.Status.ACTIVE,
            payment_status=Enrolment.PaymentStatus.PAID,
            is_active=True,
            progress_percentage=25,
        )
        self.low_progress_enrolment = Enrolment.objects.create(
            student=self.other_student,
            course=self.course,
            status=Enrolment.Status.ACTIVE,
            payment_status=Enrolment.PaymentStatus.NOT_REQUIRED,
            is_active=True,
            progress_percentage=10,
        )

    def review_data(self, rating=5, comment='This course was practical and useful.'):

        return {
            'rating': rating,
            'comment': comment,
        }

    def create_review(self, student=None, course=None, data=None):

        return create_course_review(
            student or self.student,
            course or self.course,
            data or self.review_data()
        )

    def test_model_validation_rejects_invalid_rating_and_mismatch(self):

        review = CourseReview(
            student=self.student,
            course=self.course,
            enrolment=self.enrolment,
            rating=6,
            comment='This is a valid comment.',
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

        review.rating = 5
        review.student = self.other_student

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_model_validation_requires_consistent_moderation_state(self):

        review = CourseReview(
            student=self.student,
            course=self.course,
            enrolment=self.enrolment,
            rating=5,
            comment='This is a valid comment.',
            status=CourseReview.Status.APPROVED,
            is_approved=False,
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

        review.status = CourseReview.Status.REJECTED
        review.is_approved = False

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_eligibility_requires_active_enrolment_and_progress(self):

        eligible, enrolment, reason = can_student_review_course(
            self.student,
            self.course
        )

        self.assertTrue(eligible)

        eligible, enrolment, reason = can_student_review_course(
            self.other_student,
            self.course
        )

        self.assertFalse(eligible)
        self.assertIn('25%', reason)

    def test_paid_course_requires_confirmed_payment_status(self):

        eligible, enrolment, reason = can_student_review_course(
            self.student,
            self.paid_course
        )

        self.assertTrue(eligible)

        self.paid_enrolment.payment_status = Enrolment.PaymentStatus.REFUNDED
        self.paid_enrolment.status = Enrolment.Status.SUSPENDED
        self.paid_enrolment.is_active = False
        self.paid_enrolment.save()

        eligible, enrolment, reason = can_student_review_course(
            self.student,
            self.paid_course
        )

        self.assertFalse(eligible)

    def test_completed_student_can_review_even_with_less_progress(self):

        self.enrolment.status = Enrolment.Status.COMPLETED
        self.enrolment.progress_percentage = 10
        self.enrolment.save()

        eligible, enrolment, reason = can_student_review_course(
            self.student,
            self.course
        )

        self.assertTrue(eligible)

    def test_create_review_saves_pending_and_notifies(self):

        review = self.create_review()

        self.assertEqual(review.status, CourseReview.Status.PENDING)
        self.assertFalse(review.is_approved)
        self.assertEqual(review.comment, self.review_data()['comment'])
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.student,
                title='Review submitted'
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.admin,
                title='Review awaiting moderation'
            ).exists()
        )

    def test_duplicate_review_is_prevented(self):

        self.create_review()

        with self.assertRaises(ValidationError):
            self.create_review(data=self.review_data(4, 'A second useful comment.'))

    def test_student_review_view_requires_login_and_progress(self):

        response = self.client.get(
            reverse('learning:course_review_create', args=[self.course.slug])
        )
        self.assertEqual(response.status_code, 302)

        self.client.login(username='other_review_student', password='pass12345')
        response = self.client.post(
            reverse('learning:course_review_create', args=[self.course.slug]),
            self.review_data()
        )
        self.assertContains(response, '25%')
        self.assertEqual(CourseReview.objects.count(), 0)

    def test_student_can_create_review_from_view(self):

        self.client.login(username='review_student', password='pass12345')

        response = self.client.post(
            reverse('learning:course_review_create', args=[self.course.slug]),
            self.review_data(4, 'A very useful practical course.')
        )

        review = CourseReview.objects.get()
        self.assertRedirects(
            response,
            reverse('learning:course_review_detail', args=[review.pk])
        )
        self.assertEqual(review.rating, 4)

    def test_student_edits_approved_review_back_to_pending(self):

        review = self.create_review()
        approve_course_review(review, self.admin)
        review.refresh_from_db()

        updated = update_course_review(
            review,
            self.student,
            self.review_data(3, 'Updated comment after more learning.')
        )

        self.assertEqual(updated.status, CourseReview.Status.PENDING)
        self.assertFalse(updated.is_approved)
        self.assertIsNone(updated.moderated_by)
        self.assertIsNone(updated.moderated_at)

    def test_student_cannot_view_or_edit_another_review(self):

        review = self.create_review()
        self.client.login(username='other_review_student', password='pass12345')

        detail_response = self.client.get(
            reverse('learning:course_review_detail', args=[review.pk])
        )
        edit_response = self.client.get(
            reverse('learning:course_review_edit', args=[review.pk])
        )

        self.assertEqual(detail_response.status_code, 404)
        self.assertEqual(edit_response.status_code, 404)

    def test_approve_review_exposes_publicly_and_updates_summary(self):

        review = self.create_review()
        approve_course_review(review, self.admin)
        review.refresh_from_db()

        self.assertEqual(review.status, CourseReview.Status.APPROVED)
        self.assertTrue(review.is_approved)
        self.assertIsNotNone(review.moderated_at)

        summary = get_course_rating_summary(self.course)
        self.assertEqual(summary['review_count'], 1)
        self.assertEqual(summary['average_rating'], 5)

        response = self.client.get(
            reverse('learning:course_detail', args=[self.course.slug])
        )
        self.assertContains(response, 'This course was practical and useful.')
        self.assertContains(response, 'Verified Learner')
        self.assertNotContains(response, 'student@example.com')

    def test_pending_rejected_and_hidden_reviews_do_not_display_publicly(self):

        pending = self.create_review(data=self.review_data(5, 'Pending public hidden text.'))
        response = self.client.get(reverse('learning:course_detail', args=[self.course.slug]))
        self.assertNotContains(response, pending.comment)

        reject_course_review(pending, self.admin, 'Needs more detail.')
        response = self.client.get(reverse('learning:course_detail', args=[self.course.slug]))
        self.assertNotContains(response, pending.comment)

        updated = update_course_review(
            pending,
            self.student,
            self.review_data(5, 'Approved then hidden public text.')
        )
        approve_course_review(updated, self.admin)
        hide_course_review(updated, self.admin, 'Privacy concern.')
        response = self.client.get(reverse('learning:course_detail', args=[self.course.slug]))
        self.assertNotContains(response, 'Approved then hidden public text.')

    def test_reject_and_hide_require_reason(self):

        review = self.create_review()

        with self.assertRaises(ValidationError):
            reject_course_review(review, self.admin, '')

        approve_course_review(review, self.admin)

        with self.assertRaises(ValidationError):
            hide_course_review(review, self.admin, '')

    def test_unauthorized_staff_and_instructor_cannot_moderate(self):

        review = self.create_review()

        with self.assertRaises(PermissionDenied):
            approve_course_review(review, self.staff)

        with self.assertRaises(PermissionDenied):
            approve_course_review(review, self.instructor)

    def test_admin_moderation_views(self):

        review = self.create_review()
        self.client.login(username='review_admin', password='pass12345')

        response = self.client.post(
            reverse('learning:admin_review_approve', args=[review.pk])
        )

        self.assertRedirects(
            response,
            reverse('learning:admin_review_detail', args=[review.pk])
        )
        review.refresh_from_db()
        self.assertEqual(review.status, CourseReview.Status.APPROVED)

    def test_instructor_sees_only_owned_course_reviews(self):

        own_review = self.create_review()
        approve_course_review(own_review, self.admin)

        other_enrolment = Enrolment.objects.create(
            student=self.other_student,
            course=self.other_course,
            status=Enrolment.Status.ACTIVE,
            payment_status=Enrolment.PaymentStatus.NOT_REQUIRED,
            is_active=True,
            progress_percentage=25,
        )
        other_review = create_course_review(
            self.other_student,
            self.other_course,
            self.review_data(4, 'Other course review comment.')
        )
        approve_course_review(other_review, self.admin)

        self.client.login(username='review_instructor', password='pass12345')
        response = self.client.get(reverse('learning:instructor_review_list'))

        self.assertContains(response, own_review.course.title)
        self.assertNotContains(response, other_review.course.title)
        self.assertNotContains(response, 'student@example.com')

    def test_course_cards_show_approved_rating_only(self):

        review = self.create_review()
        response = self.client.get(reverse('learning:course_list'))
        self.assertContains(response, 'New course')

        approve_course_review(review, self.admin)
        response = self.client.get(reverse('learning:course_list'))
        self.assertContains(response, '5.0 (1 reviews)')

    def test_review_comment_validation_rejects_short_or_punctuation(self):

        with self.assertRaises(ValidationError):
            self.create_review(data=self.review_data(5, 'short'))

        with self.assertRaises(ValidationError):
            self.create_review(data=self.review_data(5, '!!!!!!!!!!!!'))
