from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from learning.models import (
    Assignment,
    AssignmentSubmission,
    Course,
    CourseCategory,
    Enrolment,
    Lesson,
    LessonProgress,
    Module,
    Notification,
)
from learning.services import (
    get_or_create_assignment_draft,
    grade_assignment_submission,
    return_assignment_for_revision,
    save_assignment_draft,
    submit_assignment,
    validate_assignment_file,
)


class StageThreeAssignmentTests(TestCase):

    def setUp(self):

        self.student = User.objects.create_user(
            username='assignment_student',
            password='pass12345'
        )
        self.other_student = User.objects.create_user(
            username='other_assignment_student',
            password='pass12345'
        )
        self.instructor = User.objects.create_user(
            username='assignment_instructor',
            password='pass12345'
        )
        self.other_instructor = User.objects.create_user(
            username='other_assignment_instructor',
            password='pass12345'
        )
        self.admin = User.objects.create_superuser(
            username='assignment_admin',
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

        self.category = CourseCategory.objects.create(
            name='Assignment Category'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Assignment Course',
            short_description='Assignment course.',
            full_description='Assignment course description.',
            status=Course.Status.PUBLISHED,
            is_free=True,
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Assignment Module',
            order=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Final Assignment',
            lesson_type=Lesson.LessonType.ASSIGNMENT,
            order=1,
            is_compulsory=True
        )
        self.assignment = Assignment.objects.create(
            lesson=self.lesson,
            title='Final Assignment',
            instructions='Submit your final work.',
            maximum_score=100,
            passing_score=50,
            maximum_attempts=2,
            require_text_submission=True,
            require_file_submission=False,
            is_published=True
        )
        self.enrolment = Enrolment.objects.create(
            student=self.student,
            course=self.course
        )

    def test_assignment_validation_rejects_bad_scores(self):

        self.assignment.maximum_score = 0

        with self.assertRaises(ValidationError):

            self.assignment.full_clean()

        self.assignment.maximum_score = 100
        self.assignment.passing_score = 150

        with self.assertRaises(ValidationError):

            self.assignment.full_clean()

    def test_student_can_create_and_reuse_draft(self):

        first, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )
        second, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )

        self.assertEqual(
            first.pk,
            second.pk
        )
        self.assertEqual(
            first.attempt_number,
            1
        )

    def test_unenrolled_student_cannot_create_draft(self):

        with self.assertRaises(PermissionDenied):

            get_or_create_assignment_draft(
                self.other_student,
                self.assignment
            )

    def test_draft_save_does_not_notify_or_complete(self):

        draft, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )
        save_assignment_draft(
            draft,
            self.student,
            {
                'submission_text': 'Draft answer.',
                'submission_file': None,
            }
        )

        self.assertFalse(
            Notification.objects.filter(
                recipient=self.instructor,
                notification_type=Notification.NotificationType.ASSIGNMENT
            ).exists()
        )
        self.assertFalse(
            LessonProgress.objects.filter(
                student=self.student,
                lesson=self.lesson,
                is_completed=True
            ).exists()
        )

    def test_final_submission_notifies_student_and_instructor(self):

        draft, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )
        save_assignment_draft(
            draft,
            self.student,
            {
                'submission_text': 'Final answer.',
                'submission_file': None,
            }
        )
        submit_assignment(
            draft,
            self.student
        )
        draft.refresh_from_db()

        self.assertEqual(
            draft.status,
            AssignmentSubmission.Status.SUBMITTED
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.instructor,
                notification_type=Notification.NotificationType.ASSIGNMENT
            ).exists()
        )

    def test_missing_required_text_rejected(self):

        draft, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )

        with self.assertRaises(ValidationError):

            submit_assignment(
                draft,
                self.student
            )

    def test_invalid_executable_file_rejected(self):

        uploaded = SimpleUploadedFile(
            'bad.exe',
            b'not safe'
        )

        with self.assertRaises(ValidationError):

            validate_assignment_file(
                self.assignment,
                uploaded
            )

    def test_late_submission_rejected_when_prohibited(self):

        self.assignment.due_date = timezone.now() - timedelta(days=1)
        self.assignment.allow_late_submission = False
        self.assignment.save()

        with self.assertRaises(ValidationError):

            get_or_create_assignment_draft(
                self.student,
                self.assignment
            )

    def test_grading_sets_pass_and_completes_lesson(self):

        draft, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )
        save_assignment_draft(
            draft,
            self.student,
            {
                'submission_text': 'Final answer.',
                'submission_file': None,
            }
        )
        submit_assignment(
            draft,
            self.student
        )
        grade_assignment_submission(
            draft,
            self.instructor,
            80,
            'Good work.'
        )
        draft.refresh_from_db()

        self.assertTrue(
            draft.passed
        )
        self.assertTrue(
            LessonProgress.objects.filter(
                student=self.student,
                lesson=self.lesson,
                is_completed=True
            ).exists()
        )

    def test_return_for_revision_allows_new_attempt(self):

        draft, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )
        save_assignment_draft(
            draft,
            self.student,
            {
                'submission_text': 'Final answer.',
                'submission_file': None,
            }
        )
        submit_assignment(
            draft,
            self.student
        )
        return_assignment_for_revision(
            draft,
            self.instructor,
            'Please add more detail.'
        )
        second, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )

        self.assertEqual(
            second.attempt_number,
            2
        )

    def test_student_cannot_access_another_submission(self):

        draft, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )
        self.client.login(
            username='other_assignment_student',
            password='pass12345'
        )
        response = self.client.get(
            reverse(
                'learning:submission_detail',
                args=[
                    draft.pk,
                ]
            )
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_instructor_cannot_grade_other_course_submission(self):

        draft, enrolment = get_or_create_assignment_draft(
            self.student,
            self.assignment
        )
        save_assignment_draft(
            draft,
            self.student,
            {
                'submission_text': 'Final answer.',
                'submission_file': None,
            }
        )
        submit_assignment(
            draft,
            self.student
        )

        with self.assertRaises(PermissionDenied):

            grade_assignment_submission(
                draft,
                self.other_instructor,
                70,
                'Invalid.'
            )
