from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from learning.models import (
    Choice,
    Course,
    CourseCategory,
    Enrolment,
    Lesson,
    LessonProgress,
    Module,
    Notification,
    Question,
    Quiz,
    QuizAttempt,
)
from learning.services import grade_short_answers, start_quiz_attempt, submit_quiz_attempt


class StageTwoQuizTests(TestCase):

    def setUp(self):

        self.student = User.objects.create_user(
            username='quiz_student',
            password='pass12345'
        )
        self.other_student = User.objects.create_user(
            username='other_quiz_student',
            password='pass12345'
        )
        self.instructor = User.objects.create_user(
            username='quiz_instructor',
            password='pass12345'
        )
        self.other_instructor = User.objects.create_user(
            username='other_quiz_instructor',
            password='pass12345'
        )
        self.admin = User.objects.create_superuser(
            username='quiz_admin',
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
            name='Quiz Category'
        )
        self.course = Course.objects.create(
            instructor=self.instructor,
            category=self.category,
            title='Quiz Course',
            short_description='Quiz course.',
            full_description='Quiz course description.',
            status=Course.Status.PUBLISHED,
            is_free=True,
        )
        self.other_course = Course.objects.create(
            instructor=self.other_instructor,
            category=self.category,
            title='Other Quiz Course',
            short_description='Other quiz course.',
            full_description='Other quiz course description.',
            status=Course.Status.PUBLISHED,
            is_free=True,
        )
        self.module = Module.objects.create(
            course=self.course,
            title='Quiz Module',
            order=1
        )
        self.lesson = Lesson.objects.create(
            module=self.module,
            title='Final Quiz',
            lesson_type=Lesson.LessonType.QUIZ,
            order=1,
            is_preview=False,
            is_compulsory=True,
        )
        self.quiz = Quiz.objects.create(
            lesson=self.lesson,
            title='Final Quiz',
            passing_score=50,
            attempts_allowed=2,
            is_published=True
        )
        self.mc_question = Question.objects.create(
            quiz=self.quiz,
            question_text='Choose the correct answer.',
            question_type=Question.QuestionType.MULTIPLE_CHOICE,
            marks=5,
            order=1
        )
        self.correct_choice = Choice.objects.create(
            question=self.mc_question,
            choice_text='Correct',
            is_correct=True,
            order=1
        )
        self.incorrect_choice = Choice.objects.create(
            question=self.mc_question,
            choice_text='Incorrect',
            is_correct=False,
            order=2
        )
        self.enrolment = Enrolment.objects.create(
            student=self.student,
            course=self.course
        )

    def test_enrolled_student_can_start_attempt(self):

        attempt = start_quiz_attempt(
            self.student,
            self.quiz
        )

        self.assertEqual(
            attempt.status,
            QuizAttempt.Status.IN_PROGRESS
        )
        self.assertEqual(
            attempt.attempt_number,
            1
        )

    def test_unenrolled_student_cannot_start_protected_quiz(self):

        with self.assertRaises(PermissionDenied):

            start_quiz_attempt(
                self.other_student,
                self.quiz
            )

    def test_duplicate_active_attempt_is_reused(self):

        first = start_quiz_attempt(
            self.student,
            self.quiz
        )
        second = start_quiz_attempt(
            self.student,
            self.quiz
        )

        self.assertEqual(
            first.pk,
            second.pk
        )

    def test_attempt_limit_is_enforced(self):

        first = start_quiz_attempt(
            self.student,
            self.quiz
        )
        submit_quiz_attempt(
            first,
            {
                str(self.mc_question.pk): {
                    'choice_ids': [
                        self.correct_choice.pk,
                    ]
                }
            }
        )
        second = start_quiz_attempt(
            self.student,
            self.quiz
        )
        submit_quiz_attempt(
            second,
            {
                str(self.mc_question.pk): {
                    'choice_ids': [
                        self.correct_choice.pk,
                    ]
                }
            }
        )

        with self.assertRaises(ValidationError):

            start_quiz_attempt(
                self.student,
                self.quiz
            )

    def test_multiple_choice_correct_answer_receives_full_marks(self):

        attempt = start_quiz_attempt(
            self.student,
            self.quiz
        )
        submit_quiz_attempt(
            attempt,
            {
                str(self.mc_question.pk): {
                    'choice_ids': [
                        self.correct_choice.pk,
                    ]
                }
            }
        )
        attempt.refresh_from_db()

        self.assertEqual(
            float(attempt.total_marks_awarded),
            5.0
        )
        self.assertTrue(
            attempt.passed
        )

    def test_multiple_choice_incorrect_answer_receives_zero(self):

        attempt = start_quiz_attempt(
            self.student,
            self.quiz
        )
        submit_quiz_attempt(
            attempt,
            {
                str(self.mc_question.pk): {
                    'choice_ids': [
                        self.incorrect_choice.pk,
                    ]
                }
            }
        )
        attempt.refresh_from_db()

        self.assertEqual(
            float(attempt.total_marks_awarded),
            0.0
        )
        self.assertFalse(
            attempt.passed
        )

    def test_short_answer_requires_manual_grading(self):

        short_question = Question.objects.create(
            quiz=self.quiz,
            question_text='Explain briefly.',
            question_type=Question.QuestionType.SHORT_ANSWER,
            marks=5,
            order=2
        )
        attempt = start_quiz_attempt(
            self.student,
            self.quiz
        )
        submit_quiz_attempt(
            attempt,
            {
                str(self.mc_question.pk): {
                    'choice_ids': [
                        self.correct_choice.pk,
                    ]
                },
                str(short_question.pk): {
                    'text_answer': 'Because it is correct.'
                },
            }
        )
        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            QuizAttempt.Status.AWAITING_MANUAL_GRADING
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.instructor,
                notification_type=Notification.NotificationType.QUIZ
            ).exists()
        )

    def test_manual_grading_recalculates_total_and_progress(self):

        short_question = Question.objects.create(
            quiz=self.quiz,
            question_text='Explain briefly.',
            question_type=Question.QuestionType.SHORT_ANSWER,
            marks=5,
            order=2
        )
        attempt = start_quiz_attempt(
            self.student,
            self.quiz
        )
        submit_quiz_attempt(
            attempt,
            {
                str(self.mc_question.pk): {
                    'choice_ids': [
                        self.correct_choice.pk,
                    ]
                },
                str(short_question.pk): {
                    'text_answer': 'A good answer.'
                },
            }
        )
        answer = attempt.answers.get(
            question=short_question
        )

        grade_short_answers(
            attempt,
            self.instructor,
            {
                str(answer.pk): {
                    'marks': '5',
                    'feedback': 'Good.',
                },
                'instructor_feedback': 'Well done.',
            }
        )
        attempt.refresh_from_db()

        self.assertEqual(
            attempt.status,
            QuizAttempt.Status.GRADED
        )
        self.assertTrue(
            attempt.passed
        )
        self.assertTrue(
            LessonProgress.objects.filter(
                student=self.student,
                lesson=self.lesson,
                is_completed=True
            ).exists()
        )

    def test_manual_marks_cannot_exceed_question_marks(self):

        short_question = Question.objects.create(
            quiz=self.quiz,
            question_text='Explain briefly.',
            question_type=Question.QuestionType.SHORT_ANSWER,
            marks=5,
            order=2
        )
        attempt = start_quiz_attempt(
            self.student,
            self.quiz
        )
        submit_quiz_attempt(
            attempt,
            {
                str(self.mc_question.pk): {
                    'choice_ids': [
                        self.correct_choice.pk,
                    ]
                },
                str(short_question.pk): {
                    'text_answer': 'A good answer.'
                },
            }
        )
        answer = attempt.answers.get(
            question=short_question
        )

        with self.assertRaises(ValidationError):

            grade_short_answers(
                attempt,
                self.instructor,
                {
                    str(answer.pk): {
                        'marks': '6',
                        'feedback': '',
                    }
                }
            )

    def test_student_cannot_access_another_students_attempt(self):

        attempt = start_quiz_attempt(
            self.student,
            self.quiz
        )
        self.client.login(
            username='other_quiz_student',
            password='pass12345'
        )
        response = self.client.get(
            reverse(
                'learning:quiz_attempt',
                args=[
                    attempt.pk,
                ]
            )
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_instructor_cannot_view_other_instructor_attempt(self):

        attempt = start_quiz_attempt(
            self.student,
            self.quiz
        )
        self.client.login(
            username='other_quiz_instructor',
            password='pass12345'
        )
        response = self.client.get(
            reverse(
                'learning:instructor_quiz_attempt_detail',
                args=[
                    attempt.pk,
                ]
            )
        )

        self.assertEqual(
            response.status_code,
            404
        )

    def test_student_dashboard_shows_recent_attempts(self):

        attempt = start_quiz_attempt(
            self.student,
            self.quiz
        )
        submit_quiz_attempt(
            attempt,
            {
                str(self.mc_question.pk): {
                    'choice_ids': [
                        self.correct_choice.pk,
                    ]
                }
            }
        )
        self.client.login(
            username='quiz_student',
            password='pass12345'
        )
        response = self.client.get(
            reverse('learning:dashboard')
        )

        self.assertContains(
            response,
            self.quiz.title
        )
