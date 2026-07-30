from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from learning.models import Course, CourseAnnouncement, CourseCategory, Enrolment, Notification
from learning.services import create_notification, publish_announcement


class StageOneNotificationAnnouncementTests(TestCase):

    def setUp(self):

        self.student = User.objects.create_user(
            username='student_stage1',
            password='pass12345'
        )
        self.other_student = User.objects.create_user(
            username='other_student_stage1',
            password='pass12345'
        )
        self.instructor = User.objects.create_user(
            username='instructor_stage1',
            password='pass12345'
        )
        self.other_instructor = User.objects.create_user(
            username='other_instructor_stage1',
            password='pass12345'
        )
        self.admin = User.objects.create_superuser(
            username='admin_stage1',
            email='admin@example.com',
            password='pass12345'
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

        self.category, created = CourseCategory.objects.get_or_create(
            name='Software Development'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Stage One Course',
            short_description='Stage one course.',
            full_description='Stage one course description.',
            status=Course.Status.PUBLISHED,
            is_free=True,
        )
        self.other_course = Course.objects.create(
            instructor=self.other_instructor,
            category=self.category,
            title='Other Stage One Course',
            short_description='Other course.',
            full_description='Other course description.',
            status=Course.Status.PUBLISHED,
            is_free=True,
        )
        self.enrolment = Enrolment.objects.create(
            student=self.student,
            course=self.course
        )

    def test_create_notification_with_dedupe_key_is_idempotent(self):

        first = create_notification(
            recipient=self.student,
            title='Test',
            message='Message',
            dedupe_key='same-key'
        )
        second = create_notification(
            recipient=self.student,
            title='Test duplicate',
            message='Message duplicate',
            dedupe_key='same-key'
        )

        self.assertEqual(
            first.pk,
            second.pk
        )
        self.assertEqual(
            Notification.objects.filter(recipient=self.student).count(),
            1
        )

    def test_published_announcement_notifies_active_students_once(self):

        announcement = CourseAnnouncement.objects.create(
            course=self.course,
            author=self.instructor,
            title='Welcome',
            message='Welcome to the course.'
        )

        publish_announcement(
            announcement
        )
        publish_announcement(
            announcement
        )

        self.assertEqual(
            Notification.objects.filter(
                recipient=self.student,
                notification_type=Notification.NotificationType.ANNOUNCEMENT
            ).count(),
            1
        )
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.other_student
            ).exists()
        )

    def test_student_sees_own_course_announcements(self):

        CourseAnnouncement.objects.create(
            course=self.course,
            author=self.instructor,
            title='Visible announcement',
            message='Visible',
            is_published=True
        )
        CourseAnnouncement.objects.create(
            course=self.other_course,
            author=self.other_instructor,
            title='Hidden announcement',
            message='Hidden',
            is_published=True
        )

        self.client.login(
            username='student_stage1',
            password='pass12345'
        )
        response = self.client.get(
            reverse('learning:announcements')
        )

        self.assertContains(
            response,
            'Visible announcement'
        )
        self.assertNotContains(
            response,
            'Hidden announcement'
        )

    def test_notification_list_is_user_scoped(self):

        own = Notification.objects.create(
            recipient=self.student,
            title='Own',
            message='Own message'
        )
        other = Notification.objects.create(
            recipient=self.other_student,
            title='Other',
            message='Other message'
        )

        self.client.login(
            username='student_stage1',
            password='pass12345'
        )
        response = self.client.get(
            reverse('learning:notifications')
        )

        self.assertContains(
            response,
            own.title
        )
        self.assertNotContains(
            response,
            other.title
        )

    def test_mark_notification_read(self):

        notification = Notification.objects.create(
            recipient=self.student,
            title='Read me',
            message='Message'
        )

        self.client.login(
            username='student_stage1',
            password='pass12345'
        )
        response = self.client.get(
            reverse(
                'learning:notification_read',
                args=[
                    notification.pk,
                ]
            )
        )

        notification.refresh_from_db()
        self.assertTrue(
            notification.is_read
        )
        self.assertEqual(
            response.status_code,
            302
        )

    def test_user_cannot_read_another_users_notification(self):

        notification = Notification.objects.create(
            recipient=self.other_student,
            title='Private',
            message='Private'
        )

        self.client.login(
            username='student_stage1',
            password='pass12345'
        )
        response = self.client.get(
            reverse(
                'learning:notification_read',
                args=[
                    notification.pk,
                ]
            )
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_instructor_cannot_create_announcement_for_other_course(self):

        self.client.login(
            username='instructor_stage1',
            password='pass12345'
        )
        response = self.client.post(
            reverse('learning:instructor_announcement_create'),
            {
                'course': self.other_course.pk,
                'title': 'Invalid',
                'message': 'Invalid',
                'is_published': 'on',
            }
        )

        self.assertEqual(
            response.status_code,
            200
        )
        self.assertFalse(
            CourseAnnouncement.objects.filter(title='Invalid').exists()
        )

    def test_admin_announcement_page_requires_staff(self):

        self.client.login(
            username='student_stage1',
            password='pass12345'
        )
        response = self.client.get(
            reverse('learning:admin_announcements')
        )

        self.assertEqual(
            response.status_code,
            302
        )

        self.client.login(
            username='admin_stage1',
            password='pass12345'
        )
        response = self.client.get(
            reverse('learning:admin_announcements')
        )

        self.assertEqual(
            response.status_code,
            200
        )
