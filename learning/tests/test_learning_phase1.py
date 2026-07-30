from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from learning.models import Course, CourseCategory, Enrolment, Lesson, Module
from learning.services import mark_lesson_complete


class LearningPhaseOneTests(TestCase):

    def setUp(self):

        self.student = User.objects.create_user(
            username='student',
            password='pass12345'
        )
        self.instructor = User.objects.create_user(
            username='instructor',
            password='pass12345'
        )
        self.other_instructor = User.objects.create_user(
            username='other',
            password='pass12345'
        )
        self.admin = User.objects.create_superuser(
            username='admin',
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
            name='Django Web Development'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Django Practical Course',
            short_description='Build a real Django project.',
            full_description='A practical course for Django learners.',
            status=Course.Status.PUBLISHED,
            is_published=True,
            is_free=True,
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Getting Started',
            order=1
        )
        self.preview_lesson = Lesson.objects.create(
            module=self.module,
            title='Course Preview',
            slug='course-preview',
            order=1,
            is_preview=True,
            is_compulsory=True,
        )
        self.private_lesson = Lesson.objects.create(
            module=self.module,
            title='Private Lesson',
            slug='private-lesson',
            order=2,
            is_preview=False,
            is_compulsory=True,
        )

    def test_public_learning_homepage(self):

        response = self.client.get(
            reverse('learning:home')
        )

        self.assertEqual(
            response.status_code,
            200
        )
        self.assertContains(
            response,
            'Build Practical Digital Skills'
        )

    def test_published_course_catalogue(self):

        response = self.client.get(
            reverse('learning:course_list')
        )

        self.assertContains(
            response,
            self.course.title
        )

    def test_course_detail_page(self):

        response = self.client.get(
            reverse(
                'learning:course_detail',
                args=[
                    self.course.slug,
                ]
            )
        )

        self.assertContains(
            response,
            self.private_lesson.title
        )

    def test_free_course_enrolment_activates(self):

        self.client.login(
            username='student',
            password='pass12345'
        )

        response = self.client.get(
            reverse(
                'learning:enrol',
                args=[
                    self.course.slug,
                ]
            )
        )

        self.assertEqual(
            response.status_code,
            302
        )
        enrolment = Enrolment.objects.get(
            student=self.student,
            course=self.course
        )
        self.assertEqual(
            enrolment.status,
            Enrolment.Status.ACTIVE
        )

    def test_duplicate_enrolment_prevention(self):

        Enrolment.objects.create(
            student=self.student,
            course=self.course
        )

        self.client.login(
            username='student',
            password='pass12345'
        )
        self.client.get(
            reverse(
                'learning:enrol',
                args=[
                    self.course.slug,
                ]
            )
        )

        self.assertEqual(
            Enrolment.objects.filter(
                student=self.student,
                course=self.course
            ).count(),
            1
        )

    def test_protected_lesson_redirects_unenrolled_user(self):

        response = self.client.get(
            reverse(
                'learning:lesson_detail',
                args=[
                    self.course.slug,
                    self.private_lesson.slug,
                ]
            )
        )

        self.assertRedirects(
            response,
            reverse(
                'learning:course_detail',
                args=[
                    self.course.slug,
                ]
            )
        )

    def test_preview_lesson_public_access(self):

        response = self.client.get(
            reverse(
                'learning:lesson_detail',
                args=[
                    self.course.slug,
                    self.preview_lesson.slug,
                ]
            )
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_student_dashboard_requires_login(self):

        response = self.client.get(
            reverse('learning:dashboard')
        )

        self.assertEqual(
            response.status_code,
            302
        )

    def test_student_dashboard(self):

        self.client.login(
            username='student',
            password='pass12345'
        )
        response = self.client.get(
            reverse('learning:dashboard')
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_instructor_dashboard(self):

        self.client.login(
            username='instructor',
            password='pass12345'
        )
        response = self.client.get(
            reverse('learning:instructor_dashboard')
        )

        self.assertEqual(
            response.status_code,
            200
        )

    def test_course_ownership_protection(self):

        self.client.login(
            username='other',
            password='pass12345'
        )
        response = self.client.get(
            reverse(
                'learning:instructor_course_edit',
                args=[
                    self.course.pk,
                ]
            )
        )

        self.assertEqual(
            response.status_code,
            403
        )

    def test_lesson_progress_calculation(self):

        enrolment = Enrolment.objects.create(
            student=self.student,
            course=self.course
        )

        mark_lesson_complete(
            self.student,
            enrolment,
            self.preview_lesson
        )
        enrolment.refresh_from_db()

        self.assertEqual(
            enrolment.progress_percentage,
            50
        )

    def test_admin_access(self):

        self.client.login(
            username='admin',
            password='pass12345'
        )
        response = self.client.get(
            reverse('admin:learning_course_changelist')
        )

        self.assertEqual(
            response.status_code,
            200
        )
