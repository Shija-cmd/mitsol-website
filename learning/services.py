import re
import secrets
from dataclasses import dataclass
from io import BytesIO
from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import models, transaction
from django.db.models import Avg, Count, Max, Q
from django.http import HttpRequest
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils import timezone

from .models import (
    Assignment,
    AssignmentSubmission,
    Certificate,
    CourseAnnouncement,
    CourseReview,
    Enrolment,
    Lesson,
    LessonProgress,
    Notification,
    Payment,
    PaymentAuditLog,
    LearningPaymentSettings,
    PAYMENT_PROOF_EXTENSIONS,
    DANGEROUS_PAYMENT_EXTENSIONS,
    Question,
    QuizAttempt,
    StudentAnswer,
    DANGEROUS_ASSIGNMENT_EXTENSIONS,
)
from .permissions import ensure_course_owner


COURSE_REVIEW_MINIMUM_PROGRESS = 25
COURSE_REVIEW_MINIMUM_COMMENT_LENGTH = 10
COURSE_REVIEW_MAXIMUM_COMMENT_LENGTH = 2000


def absolute_site_url(path=''):

    site_url = getattr(
        settings,
        'SITE_URL',
        ''
    ).rstrip('/')

    if not path:
        return site_url

    if path.startswith('http://') or path.startswith('https://'):
        return path

    return f'{site_url}{path}'


def log_payment_audit(payment, action, actor=None, previous_status='', note=''):

    return PaymentAuditLog.objects.create(
        payment=payment,
        action=action,
        previous_status=previous_status or '',
        new_status=payment.status,
        note=note or '',
        actor=actor,
    )


def send_learning_email(subject, template_name, recipient, context):

    if not recipient:
        return False

    html_body = render_to_string(
        template_name,
        context
    )
    text_body = strip_tags(html_body)
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        to=[recipient],
    )
    email.attach_alternative(
        html_body,
        'text/html'
    )
    email.send(fail_silently=True)
    return True


def send_payment_lifecycle_email(payment, event, recipient=None):

    recipient = recipient or payment.student.email

    if not recipient:
        return False

    subjects = {
        'submitted': f'Payment Received for Verification - {payment.course.title}',
        'confirmed': f'Course Access Activated - {payment.course.title}',
        'rejected': f'Payment Needs Attention - {payment.course.title}',
        'refunded': f'Payment Refunded - {payment.course.title}',
    }
    return send_learning_email(
        subjects[event],
        'learning/emails/payment_status.html',
        recipient,
        {
            'payment': payment,
            'event': event,
            'student_name': payment.student.get_full_name() or payment.student.username,
            'course_url': absolute_site_url(payment.course.get_absolute_url()),
            'payment_url': absolute_site_url(reverse('learning:payment_detail', args=[payment.pk])),
            'site_url': getattr(settings, 'SITE_URL', ''),
        }
    )


@dataclass
class CompletionResult:

    completed: bool
    progress_percentage: int
    missing_requirements: list
    certificate: object = None
    changed: bool = False
    enrolment: object = None


def lesson_is_content(lesson):

    return lesson.lesson_type not in [
        Lesson.LessonType.QUIZ,
        Lesson.LessonType.ASSIGNMENT,
    ]


def quiz_lesson_completed(enrolment, lesson):

    quiz = getattr(
        lesson,
        'quiz',
        None
    )

    if not quiz or not quiz.is_published:
        return False

    return QuizAttempt.objects.filter(
        student=enrolment.student,
        enrolment=enrolment,
        quiz=quiz,
        status=QuizAttempt.Status.GRADED,
        passed=True,
    ).exists()


def assignment_lesson_completed(enrolment, lesson):

    assignment = getattr(
        lesson,
        'assignment',
        None
    )

    if not assignment or not assignment.is_published:
        return False

    return AssignmentSubmission.objects.filter(
        student=enrolment.student,
        enrolment=enrolment,
        assignment=assignment,
        status=AssignmentSubmission.Status.GRADED,
        passed=True,
    ).exists()


def content_lesson_completed(enrolment, lesson):

    return LessonProgress.objects.filter(
        student=enrolment.student,
        enrolment=enrolment,
        lesson=lesson,
        is_completed=True,
    ).exists()


def lesson_requirement_completed(enrolment, lesson):

    if lesson.lesson_type == Lesson.LessonType.QUIZ:
        return quiz_lesson_completed(enrolment, lesson)

    if lesson.lesson_type == Lesson.LessonType.ASSIGNMENT:
        return assignment_lesson_completed(enrolment, lesson)

    return content_lesson_completed(enrolment, lesson)


def trackable_lessons(enrolment):

    return Lesson.objects.select_related(
        'module'
    ).filter(
        module__course=enrolment.course,
        module__is_published=True,
        is_published=True,
    ).order_by(
        'module__order',
        'order',
        'title',
    )


def calculate_enrolment_progress(enrolment):

    lessons = list(trackable_lessons(enrolment))

    if not lessons:
        return 0

    completed = sum(
        1
        for lesson in lessons
        if lesson_requirement_completed(enrolment, lesson)
    )

    return min(
        100,
        round(completed * 100 / len(lessons))
    )


def recalculate_enrolment_progress(enrolment):
    return evaluate_course_completion(enrolment).enrolment


@transaction.atomic
def enrol_student_in_course(student, course):

    enrolment, created = Enrolment.objects.get_or_create(
        student=student,
        course=course,
        defaults={
            'status': (
                Enrolment.Status.ACTIVE
                if course.is_free
                else Enrolment.Status.PENDING
            ),
            'payment_status': (
                Enrolment.PaymentStatus.NOT_REQUIRED
                if course.is_free
                else Enrolment.PaymentStatus.PENDING
            ),
            'is_active': course.is_free,
            'activated_at': timezone.now() if course.is_free else None,
        }
    )

    if created:

        create_notification(
            recipient=student,
            title='Course enrolment received',
            message=(
                f'You have been enrolled in {course.title}.'
                if course.is_free
                else f'Your enrolment request for {course.title} is pending payment confirmation.'
            ),
            notification_type=Notification.NotificationType.ENROLMENT,
            related_url=course.get_absolute_url(),
            dedupe_key=f'enrolment:{enrolment.pk}:created'
        )

    return enrolment, created


@transaction.atomic
def mark_lesson_complete(student, enrolment, lesson):

    progress, created = LessonProgress.objects.get_or_create(
        student=student,
        enrolment=enrolment,
        lesson=lesson
    )

    if not progress.is_completed:

        progress.is_completed = True
        progress.completed_at = timezone.now()
        progress.save(
            update_fields=[
                'is_completed',
                'completed_at',
                'last_accessed_at',
            ]
        )

    recalculate_enrolment_progress(
        enrolment
    )

    return progress


def paid_enrolment_is_confirmed(enrolment):

    if enrolment.course.is_free:
        return enrolment.payment_status == Enrolment.PaymentStatus.NOT_REQUIRED

    return enrolment.payment_status == Enrolment.PaymentStatus.PAID


def course_code(course):

    source = course.slug or course.title or 'COURSE'
    code = re.sub(r'[^A-Za-z0-9]+', '', source).upper()
    return (code[:12] or 'COURSE')


def generate_certificate_number(course):

    year = timezone.now().year
    prefix = f'MITSOL-{year}-{course_code(course)}'
    next_number = Certificate.objects.filter(
        certificate_number__startswith=prefix
    ).count() + 1

    while True:
        certificate_number = f'{prefix}-{next_number:06d}'
        if not Certificate.objects.filter(certificate_number=certificate_number).exists():
            return certificate_number
        next_number += 1


def generate_verification_code():

    while True:
        code = secrets.token_urlsafe(32)
        if not Certificate.objects.filter(verification_code=code).exists():
            return code


def user_can_manage_certificates(user, permission='view_all_certificates'):

    if not user or not user.is_authenticated:
        return False

    return (
        user.is_superuser
        or user.has_perm(f'learning.{permission}')
        or user.has_perm('learning.view_all_certificates')
    )


@transaction.atomic
def issue_certificate(enrolment, notify=True):

    enrolment = Enrolment.objects.select_for_update().select_related(
        'student',
        'course',
        'course__instructor',
    ).get(pk=enrolment.pk)

    if enrolment.status != Enrolment.Status.COMPLETED:
        raise ValidationError('Certificates can only be issued for completed enrolments.')

    if not paid_enrolment_is_confirmed(enrolment):
        raise ValidationError('Certificate issuance requires confirmed course access.')

    existing = Certificate.objects.filter(enrolment=enrolment).first()

    if existing:
        return existing

    certificate = Certificate.objects.create(
        student=enrolment.student,
        course=enrolment.course,
        enrolment=enrolment,
        certificate_number=generate_certificate_number(enrolment.course),
        verification_code=generate_verification_code(),
        issued_at=timezone.now(),
        approval_status=Certificate.ApprovalStatus.PENDING,
        is_valid=False,
    )

    if notify:
        create_notification(
            recipient=enrolment.student,
            title='Certificate awaiting approval',
            message=f'Your certificate for {enrolment.course.title} has been generated and is awaiting MITSOL approval.',
            notification_type=Notification.NotificationType.CERTIFICATE,
            related_url=reverse('learning:certificate_detail', args=[certificate.pk]),
            dedupe_key=f'certificate:{certificate.pk}:pending-approval'
        )

    return certificate


@transaction.atomic
def approve_certificate(certificate, administrator):

    if not user_can_manage_certificates(administrator, 'approve_certificate'):
        raise PermissionDenied('You cannot approve certificates.')

    certificate = Certificate.objects.select_for_update().select_related(
        'student',
        'course',
        'enrolment',
    ).get(pk=certificate.pk)

    if certificate.approval_status == Certificate.ApprovalStatus.APPROVED and certificate.is_valid:
        return certificate

    if certificate.approval_status == Certificate.ApprovalStatus.REVOKED:
        raise ValidationError('Revoked certificates must be restored before approval.')

    if certificate.enrolment.status != Enrolment.Status.COMPLETED:
        raise ValidationError('Only completed enrolments can have approved certificates.')

    if not paid_enrolment_is_confirmed(certificate.enrolment):
        raise ValidationError('Cannot approve certificate while course access is invalid.')

    certificate.approval_status = Certificate.ApprovalStatus.APPROVED
    certificate.is_valid = True
    certificate.approved_by = administrator
    certificate.approved_at = timezone.now()
    certificate.revoked_by = None
    certificate.revoked_at = None
    certificate.revocation_reason = ''
    certificate.save(
        update_fields=[
            'approval_status',
            'is_valid',
            'approved_by',
            'approved_at',
            'revoked_by',
            'revoked_at',
            'revocation_reason',
            'updated_at',
        ]
    )

    create_notification(
        recipient=certificate.student,
        title='Certificate approved',
        message=f'Your certificate for {certificate.course.title} is approved and ready to download.',
        notification_type=Notification.NotificationType.CERTIFICATE,
        related_url=reverse('learning:certificate_detail', args=[certificate.pk]),
        dedupe_key=f'certificate:{certificate.pk}:approved'
    )
    send_learning_email(
        f'Your MITSOL Certificate Is Ready - {certificate.course.title}',
        'learning/emails/certificate_issued.html',
        certificate.student.email,
        {
            'certificate': certificate,
            'student_name': certificate.student.get_full_name() or certificate.student.username,
            'certificate_url': absolute_site_url(reverse('learning:certificate_detail', args=[certificate.pk])),
            'verification_url': certificate_verification_url(certificate),
            'site_url': getattr(settings, 'SITE_URL', ''),
        }
    )

    return certificate


def certificate_verification_url(certificate, request=None):

    path = certificate.verification_url_path

    if isinstance(request, HttpRequest):
        return request.build_absolute_uri(path)

    return f"{settings.SITE_URL.rstrip('/')}{path}"


def find_certificate(query):

    value = (query or '').strip()

    if not value or len(value) > 140:
        return None

    return Certificate.objects.select_related(
        'student',
        'course',
        'course__instructor',
        'enrolment',
    ).filter(
        approval_status__in=[
            Certificate.ApprovalStatus.APPROVED,
            Certificate.ApprovalStatus.REVOKED,
        ],
    ).filter(
        Q(certificate_number__iexact=value)
        | Q(verification_code=value)
    ).first()


def certificate_logo_path():

    return finders.find('core/images/logo.png')


def generate_certificate_pdf(certificate, request=None):

    certificate = Certificate.objects.select_related(
        'student',
        'course',
        'course__instructor',
        'enrolment',
    ).get(pk=certificate.pk)

    verification_url = certificate_verification_url(certificate, request)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        page_width, page_height = landscape(A4)
        pdf = canvas.Canvas(buffer, pagesize=landscape(A4))

        pdf.setFillColor(colors.HexColor('#0d1b2a'))
        pdf.rect(0, 0, page_width, page_height, fill=True, stroke=False)
        pdf.setStrokeColor(colors.HexColor('#18b7d8'))
        pdf.setLineWidth(2)
        pdf.rect(15 * mm, 15 * mm, page_width - 30 * mm, page_height - 30 * mm)

        logo = certificate_logo_path()
        if logo:
            try:
                pdf.drawImage(logo, 24 * mm, page_height - 42 * mm, width=25 * mm, height=18 * mm, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica-Bold', 22)
        pdf.drawCentredString(page_width / 2, page_height - 35 * mm, 'MITSOL')
        pdf.setFont('Helvetica', 11)
        pdf.drawCentredString(page_width / 2, page_height - 42 * mm, 'Technology Solutions')

        pdf.setFillColor(colors.HexColor('#18b7d8'))
        pdf.setFont('Helvetica-Bold', 30)
        pdf.drawCentredString(page_width / 2, page_height - 68 * mm, 'Certificate of Completion')

        pdf.setFillColor(colors.white)
        pdf.setFont('Helvetica', 13)
        pdf.drawCentredString(page_width / 2, page_height - 86 * mm, 'This certifies that')
        pdf.setFont('Helvetica-Bold', 25)
        pdf.drawCentredString(page_width / 2, page_height - 101 * mm, certificate.public_student_name[:70])
        pdf.setFont('Helvetica', 13)
        pdf.drawCentredString(page_width / 2, page_height - 116 * mm, 'has successfully completed the course')
        pdf.setFont('Helvetica-Bold', 20)
        pdf.drawCentredString(page_width / 2, page_height - 131 * mm, certificate.course.title[:95])

        pdf.setFont('Helvetica', 10)
        pdf.drawString(26 * mm, 45 * mm, f'Certificate No: {certificate.certificate_number}')
        pdf.drawString(26 * mm, 38 * mm, f'Issued: {timezone.localtime(certificate.issued_at).strftime("%B %d, %Y")}')
        pdf.drawString(26 * mm, 31 * mm, f'Instructor: {certificate.course.instructor.get_full_name() or certificate.course.instructor.username}')
        pdf.drawString(26 * mm, 24 * mm, f'Verify: {verification_url}')

        try:
            import qrcode
            qr_image = qrcode.make(verification_url)
            qr_buffer = BytesIO()
            qr_image.save(qr_buffer, format='PNG')
            qr_buffer.seek(0)
            from reportlab.lib.utils import ImageReader
            pdf.drawImage(ImageReader(qr_buffer), page_width - 52 * mm, 25 * mm, width=28 * mm, height=28 * mm)
        except Exception:
            pdf.setFont('Helvetica', 8)
            pdf.drawRightString(page_width - 24 * mm, 31 * mm, 'QR unavailable')

        if not certificate.is_valid:
            pdf.saveState()
            pdf.setFillColor(colors.Color(1, 0, 0, alpha=0.18))
            pdf.setFont('Helvetica-Bold', 62)
            pdf.translate(page_width / 2, page_height / 2)
            pdf.rotate(25)
            pdf.drawCentredString(0, 0, 'REVOKED')
            pdf.restoreState()

        pdf.showPage()
        pdf.save()
        return buffer.getvalue()

    except Exception:
        content = (
            f'%PDF-1.4\n'
            f'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n'
            f'2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n'
            f'3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] '
            f'/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n'
            f'4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n'
        )
        text = (
            f'BT /F1 24 Tf 80 500 Td (MITSOL Certificate of Completion) Tj '
            f'0 -45 Td ({certificate.public_student_name[:80]}) Tj '
            f'0 -35 Td ({certificate.course.title[:90]}) Tj '
            f'0 -35 Td ({certificate.certificate_number}) Tj ET'
        )
        stream = f'5 0 obj << /Length {len(text)} >> stream\n{text}\nendstream endobj\n'
        trailer = 'xref\n0 6\n0000000000 65535 f \ntrailer << /Root 1 0 R /Size 6 >>\nstartxref\n0\n%%EOF'
        return (content + stream + trailer).encode('latin-1', errors='ignore')


@transaction.atomic
def revoke_certificate(certificate, administrator, reason):

    if not reason.strip():
        raise ValidationError('Revocation reason is required.')

    if not user_can_manage_certificates(administrator, 'revoke_certificate'):
        raise PermissionDenied('You cannot revoke certificates.')

    certificate = Certificate.objects.select_for_update().select_related('student', 'course').get(pk=certificate.pk)

    if certificate.approval_status == Certificate.ApprovalStatus.PENDING:
        raise ValidationError('Pending certificates must be approved before they can be revoked.')

    if not certificate.is_valid:
        return certificate

    certificate.is_valid = False
    certificate.approval_status = Certificate.ApprovalStatus.REVOKED
    certificate.revoked_by = administrator
    certificate.revoked_at = timezone.now()
    certificate.revocation_reason = reason.strip()
    certificate.save(update_fields=['is_valid', 'approval_status', 'revoked_by', 'revoked_at', 'revocation_reason', 'updated_at'])

    create_notification(
        recipient=certificate.student,
        title='Certificate revoked',
        message=f'Your certificate for {certificate.course.title} has been revoked.',
        notification_type=Notification.NotificationType.CERTIFICATE,
        related_url=reverse('learning:certificate_detail', args=[certificate.pk]),
        dedupe_key=f'certificate:{certificate.pk}:revoked'
    )

    return certificate


@transaction.atomic
def restore_certificate(certificate, administrator):

    if not user_can_manage_certificates(administrator, 'restore_certificate'):
        raise PermissionDenied('You cannot restore certificates.')

    certificate = Certificate.objects.select_for_update().select_related('student', 'course', 'enrolment').get(pk=certificate.pk)

    if certificate.approval_status == Certificate.ApprovalStatus.PENDING:
        raise ValidationError('Pending certificates must be approved, not restored.')

    if certificate.is_valid:
        return certificate

    if certificate.enrolment.status != Enrolment.Status.COMPLETED:
        raise ValidationError('Only completed enrolments can have valid certificates.')

    if not paid_enrolment_is_confirmed(certificate.enrolment):
        raise ValidationError('Cannot restore certificate while course access is invalid.')

    certificate.approval_status = Certificate.ApprovalStatus.APPROVED
    certificate.is_valid = True
    certificate.restored_by = administrator
    certificate.restored_at = timezone.now()
    certificate.approved_by = administrator
    certificate.approved_at = timezone.now()
    certificate.save(update_fields=['approval_status', 'is_valid', 'restored_by', 'restored_at', 'approved_by', 'approved_at', 'updated_at'])

    create_notification(
        recipient=certificate.student,
        title='Certificate restored',
        message=f'Your certificate for {certificate.course.title} has been restored.',
        notification_type=Notification.NotificationType.CERTIFICATE,
        related_url=reverse('learning:certificate_detail', args=[certificate.pk]),
        dedupe_key=f'certificate:{certificate.pk}:restored'
    )

    return certificate


def evaluate_course_completion(enrolment):

    enrolment = Enrolment.objects.select_related(
        'student',
        'course',
    ).get(pk=enrolment.pk)

    original_status = enrolment.status
    original_completed_at = enrolment.completed_at
    missing = []
    certificate = None
    progress = calculate_enrolment_progress(enrolment)

    if enrolment.status == Enrolment.Status.COMPLETED:
        certificate = issue_certificate(enrolment)
        if enrolment.progress_percentage != progress:
            enrolment.progress_percentage = progress
            enrolment.save(update_fields=['progress_percentage'])
        return CompletionResult(
            completed=True,
            progress_percentage=progress,
            missing_requirements=[],
            certificate=certificate,
            changed=False,
            enrolment=enrolment,
        )

    if enrolment.status != Enrolment.Status.ACTIVE or not enrolment.is_active:
        missing.append('Enrolment is not active.')

    if not paid_enrolment_is_confirmed(enrolment):
        missing.append('Payment or access confirmation is incomplete.')

    lessons = list(trackable_lessons(enrolment))

    if not lessons:
        missing.append('Course has no published learning requirements.')

    for lesson in lessons:
        if not lesson.is_compulsory:
            continue
        if not lesson_requirement_completed(enrolment, lesson):
            if lesson.lesson_type == Lesson.LessonType.QUIZ:
                missing.append(f'Quiz not passed: {lesson.title}')
            elif lesson.lesson_type == Lesson.LessonType.ASSIGNMENT:
                missing.append(f'Assignment not passed: {lesson.title}')
            else:
                missing.append(f'Lesson incomplete: {lesson.title}')

    completed = not missing
    changed = False

    enrolment.progress_percentage = progress

    if completed:
        enrolment.status = Enrolment.Status.COMPLETED
        if not enrolment.completed_at:
            enrolment.completed_at = timezone.now()
        changed = (
            original_status != enrolment.status
            or original_completed_at != enrolment.completed_at
        )

    enrolment.save(
        update_fields=[
            'progress_percentage',
            'status',
            'completed_at',
        ]
    )

    if completed:
        create_notification(
            recipient=enrolment.student,
            title='Course completed',
            message=f'You have completed {enrolment.course.title}.',
            notification_type=Notification.NotificationType.COURSE_COMPLETION,
            related_url=enrolment.course.get_absolute_url(),
            dedupe_key=f'enrolment:{enrolment.pk}:completed'
        )
        certificate = issue_certificate(enrolment)

    return CompletionResult(
        completed=completed,
        progress_percentage=progress,
        missing_requirements=missing,
        certificate=certificate,
        changed=changed,
        enrolment=enrolment,
    )


def create_notification(
    recipient,
    title,
    message,
    notification_type=Notification.NotificationType.SYSTEM,
    related_url='',
    dedupe_key='',
):

    if dedupe_key:

        notification, created = Notification.objects.get_or_create(
            recipient=recipient,
            dedupe_key=dedupe_key,
            defaults={
                'title': title,
                'message': message,
                'notification_type': notification_type,
                'related_url': related_url,
            }
        )

        return notification

    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        related_url=related_url,
    )


def get_active_enrolment(student, course):

    return Enrolment.objects.filter(
        student=student,
        course=course,
        status__in=[
            Enrolment.Status.ACTIVE,
            Enrolment.Status.COMPLETED,
        ],
        is_active=True,
        payment_status__in=[
            Enrolment.PaymentStatus.NOT_REQUIRED,
            Enrolment.PaymentStatus.PAID,
        ],
    ).first()


def review_moderator_users():

    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.filter(
        is_active=True
    ).filter(
        Q(is_superuser=True)
        | Q(user_permissions__codename='moderate_course_reviews')
        | Q(groups__permissions__codename='moderate_course_reviews')
        | Q(user_permissions__codename='approve_course_review')
        | Q(groups__permissions__codename='approve_course_review')
    ).distinct()


def user_can_moderate_reviews(user, permission='moderate_course_reviews'):

    if not user or not user.is_authenticated:
        return False

    return (
        user.is_superuser
        or user.has_perm(f'learning.{permission}')
        or user.has_perm('learning.moderate_course_reviews')
    )


def validate_review_comment(comment):

    cleaned = (comment or '').strip()

    if len(cleaned) < COURSE_REVIEW_MINIMUM_COMMENT_LENGTH:
        raise ValidationError(
            f'Please provide at least {COURSE_REVIEW_MINIMUM_COMMENT_LENGTH} characters.'
        )

    if len(cleaned) > COURSE_REVIEW_MAXIMUM_COMMENT_LENGTH:
        raise ValidationError(
            f'Review comments cannot exceed {COURSE_REVIEW_MAXIMUM_COMMENT_LENGTH} characters.'
        )

    meaningful = ''.join(character for character in cleaned if character.isalnum())

    if not meaningful:
        raise ValidationError('Please write a meaningful review comment.')

    if 'http://' in cleaned.lower() or 'https://' in cleaned.lower():
        if cleaned.lower().count('http://') + cleaned.lower().count('https://') > 2:
            raise ValidationError('Please remove excessive links from your review.')

    return cleaned


def get_review_enrolment(student, course):

    return Enrolment.objects.filter(
        student=student,
        course=course,
        status__in=[
            Enrolment.Status.ACTIVE,
            Enrolment.Status.COMPLETED,
        ],
        is_active=True,
        payment_status__in=[
            Enrolment.PaymentStatus.NOT_REQUIRED,
            Enrolment.PaymentStatus.PAID,
        ],
    ).first()


def can_student_review_course(student, course, include_existing_check=True):

    if not student or not student.is_authenticated:
        return False, None, 'Please sign in before reviewing this course.'

    enrolment = get_review_enrolment(student, course)

    if not enrolment:
        return False, None, 'You must be actively enrolled with confirmed access before reviewing this course.'

    if not course.is_free and enrolment.payment_status != Enrolment.PaymentStatus.PAID:
        return False, enrolment, 'Payment must be confirmed before reviewing this course.'

    if enrolment.status != Enrolment.Status.COMPLETED and enrolment.progress_percentage < COURSE_REVIEW_MINIMUM_PROGRESS:
        return (
            False,
            enrolment,
            f'You must complete at least {COURSE_REVIEW_MINIMUM_PROGRESS}% of this course before reviewing it.'
        )

    if include_existing_check and CourseReview.objects.filter(student=student, course=course).exists():
        return False, enrolment, 'You have already reviewed this course.'

    return True, enrolment, ''


def get_course_rating_summary(course):

    approved = CourseReview.objects.filter(
        course=course,
        status=CourseReview.Status.APPROVED,
        is_approved=True
    )

    aggregate = approved.aggregate(
        average=Avg('rating'),
        count=Count('id'),
        five=Count('id', filter=Q(rating=5)),
        four=Count('id', filter=Q(rating=4)),
        three=Count('id', filter=Q(rating=3)),
        two=Count('id', filter=Q(rating=2)),
        one=Count('id', filter=Q(rating=1)),
    )

    review_count = aggregate['count'] or 0

    def percentage(value):
        if not review_count:
            return 0
        return round((value or 0) * 100 / review_count)

    return {
        'average_rating': round(aggregate['average'] or 0, 1),
        'review_count': review_count,
        'five_star_count': aggregate['five'] or 0,
        'four_star_count': aggregate['four'] or 0,
        'three_star_count': aggregate['three'] or 0,
        'two_star_count': aggregate['two'] or 0,
        'one_star_count': aggregate['one'] or 0,
        'five_star_percentage': percentage(aggregate['five']),
        'four_star_percentage': percentage(aggregate['four']),
        'three_star_percentage': percentage(aggregate['three']),
        'two_star_percentage': percentage(aggregate['two']),
        'one_star_percentage': percentage(aggregate['one']),
    }


def rating_summaries_for_courses(courses):

    course_ids = [course.pk for course in courses]

    if not course_ids:
        return {}

    rows = CourseReview.objects.filter(
        course_id__in=course_ids,
        status=CourseReview.Status.APPROVED,
        is_approved=True
    ).values(
        'course_id'
    ).annotate(
        average=Avg('rating'),
        count=Count('id')
    )

    return {
        row['course_id']: {
            'average_rating': round(row['average'] or 0, 1),
            'review_count': row['count'] or 0,
        }
        for row in rows
    }


def attach_rating_summaries(courses):

    courses = list(courses)
    summaries = rating_summaries_for_courses(courses)

    for course in courses:
        course.rating_summary = summaries.get(
            course.pk,
            {
                'average_rating': 0,
                'review_count': 0,
            }
        )

    return courses


def notify_review_moderators(review, title, message, dedupe_suffix):

    for moderator in review_moderator_users():
        create_notification(
            recipient=moderator,
            title=title,
            message=message,
            notification_type=Notification.NotificationType.REVIEW,
            related_url=reverse('learning:admin_review_detail', args=[review.pk]),
            dedupe_key=f'course-review:{review.pk}:{dedupe_suffix}:moderator:{moderator.pk}:{review.updated_at:%Y%m%d%H%M%S}'
        )


@transaction.atomic
def create_course_review(student, course, cleaned_data):

    eligible, enrolment, reason = can_student_review_course(
        student,
        course,
        include_existing_check=False
    )

    if not eligible:
        raise PermissionDenied(reason)

    enrolment = Enrolment.objects.select_for_update().get(pk=enrolment.pk)

    if CourseReview.objects.select_for_update().filter(student=student, course=course).exists():
        raise ValidationError('You have already reviewed this course.')

    comment = validate_review_comment(cleaned_data.get('comment', ''))
    rating = cleaned_data.get('rating')

    review = CourseReview.objects.create(
        student=student,
        course=course,
        enrolment=enrolment,
        rating=rating,
        comment=comment,
        status=CourseReview.Status.PENDING,
        is_approved=False,
        moderation_notes='',
        moderated_by=None,
        moderated_at=None,
    )

    create_notification(
        recipient=student,
        title='Review submitted',
        message=f'Your review for {course.title} is awaiting moderation.',
        notification_type=Notification.NotificationType.REVIEW,
        related_url=reverse('learning:course_review_detail', args=[review.pk]),
        dedupe_key=f'course-review:{review.pk}:submitted-student'
    )

    notify_review_moderators(
        review,
        'Review awaiting moderation',
        f'{student} submitted a review for {course.title}.',
        'submitted'
    )

    return review


@transaction.atomic
def update_course_review(review, student, cleaned_data):

    review = CourseReview.objects.select_for_update().select_related('course', 'student').get(pk=review.pk)

    if review.student_id != student.id:
        raise PermissionDenied('You can only edit your own reviews.')

    review.rating = cleaned_data.get('rating')
    review.comment = validate_review_comment(cleaned_data.get('comment', ''))
    review.status = CourseReview.Status.PENDING
    review.is_approved = False
    review.moderation_notes = ''
    review.moderated_by = None
    review.moderated_at = None
    review.save()

    create_notification(
        recipient=student,
        title='Review updated',
        message=f'Your updated review for {review.course.title} is awaiting moderation.',
        notification_type=Notification.NotificationType.REVIEW,
        related_url=reverse('learning:course_review_detail', args=[review.pk]),
        dedupe_key=f'course-review:{review.pk}:updated-student:{review.updated_at:%Y%m%d%H%M%S}'
    )

    notify_review_moderators(
        review,
        'Updated review awaiting moderation',
        f'{student} updated a review for {review.course.title}.',
        'updated'
    )

    return review


@transaction.atomic
def approve_course_review(review, moderator):

    if not user_can_moderate_reviews(moderator, 'approve_course_review'):
        raise PermissionDenied('You cannot approve course reviews.')

    review = CourseReview.objects.select_for_update().select_related('student', 'course').get(pk=review.pk)

    if review.status == CourseReview.Status.APPROVED and review.is_approved:
        return review

    if review.status not in [
        CourseReview.Status.PENDING,
        CourseReview.Status.REJECTED,
        CourseReview.Status.HIDDEN,
    ]:
        raise ValidationError('This review cannot be approved from its current status.')

    review.status = CourseReview.Status.APPROVED
    review.is_approved = True
    review.moderation_notes = ''
    review.moderated_by = moderator
    review.moderated_at = timezone.now()
    review.save()

    create_notification(
        recipient=review.student,
        title='Review approved',
        message=f'Your review for {review.course.title} has been approved.',
        notification_type=Notification.NotificationType.REVIEW,
        related_url=review.course.get_absolute_url(),
        dedupe_key=f'course-review:{review.pk}:approved'
    )

    return review


@transaction.atomic
def reject_course_review(review, moderator, reason):

    if not reason.strip():
        raise ValidationError('Rejection reason is required.')

    if not user_can_moderate_reviews(moderator, 'reject_course_review'):
        raise PermissionDenied('You cannot reject course reviews.')

    review = CourseReview.objects.select_for_update().select_related('student', 'course').get(pk=review.pk)

    if review.status == CourseReview.Status.REJECTED:
        return review

    if review.status not in [
        CourseReview.Status.PENDING,
        CourseReview.Status.APPROVED,
        CourseReview.Status.HIDDEN,
    ]:
        raise ValidationError('This review cannot be rejected from its current status.')

    review.status = CourseReview.Status.REJECTED
    review.is_approved = False
    review.moderation_notes = reason.strip()
    review.moderated_by = moderator
    review.moderated_at = timezone.now()
    review.save()

    create_notification(
        recipient=review.student,
        title='Review rejected',
        message=f'Your review for {review.course.title} was rejected. You may edit and resubmit it.',
        notification_type=Notification.NotificationType.REVIEW,
        related_url=reverse('learning:course_review_detail', args=[review.pk]),
        dedupe_key=f'course-review:{review.pk}:rejected'
    )

    return review


@transaction.atomic
def hide_course_review(review, moderator, reason):

    if not reason.strip():
        raise ValidationError('Hide reason is required.')

    if not user_can_moderate_reviews(moderator, 'hide_course_review'):
        raise PermissionDenied('You cannot hide course reviews.')

    review = CourseReview.objects.select_for_update().select_related('student', 'course').get(pk=review.pk)

    if review.status == CourseReview.Status.HIDDEN:
        return review

    if review.status != CourseReview.Status.APPROVED:
        raise ValidationError('Only approved reviews can be hidden.')

    review.status = CourseReview.Status.HIDDEN
    review.is_approved = False
    review.moderation_notes = reason.strip()
    review.moderated_by = moderator
    review.moderated_at = timezone.now()
    review.save()

    create_notification(
        recipient=review.student,
        title='Review hidden',
        message=f'Your review for {review.course.title} is no longer publicly visible.',
        notification_type=Notification.NotificationType.REVIEW,
        related_url=reverse('learning:course_review_detail', args=[review.pk]),
        dedupe_key=f'course-review:{review.pk}:hidden'
    )

    return review


def get_learning_payment_settings():

    settings_obj = LearningPaymentSettings.objects.filter(
        is_active=True
    ).first()

    if settings_obj:
        return settings_obj

    return LearningPaymentSettings(currency='TZS')


def get_course_payable_amount(course):

    if course.price < 0 or (course.discount_price is not None and course.discount_price < 0):
        raise ValidationError('Course price cannot be negative.')

    if course.is_free:
        return Decimal('0')

    if course.price <= 0:
        raise ValidationError('Paid courses must have a price greater than zero.')

    if course.discount_price is not None:
        if course.discount_price > course.price:
            raise ValidationError('Discount price cannot exceed normal price.')
        if course.discount_price < course.price:
            return course.discount_price

    return course.price


@transaction.atomic
def get_or_create_paid_course_enrolment(student, course):

    if course.is_free:
        raise ValidationError('Free courses do not require payment.')

    if not course.is_published:
        raise PermissionDenied('This course is not available.')

    enrolment, created = Enrolment.objects.select_for_update().get_or_create(
        student=student,
        course=course,
        defaults={
            'status': Enrolment.Status.PENDING,
            'payment_status': Enrolment.PaymentStatus.PENDING,
            'is_active': False,
        }
    )

    if enrolment.status in [Enrolment.Status.ACTIVE, Enrolment.Status.COMPLETED]:
        return enrolment, created

    if enrolment.status != Enrolment.Status.PENDING or enrolment.is_active:
        enrolment.status = Enrolment.Status.PENDING
        enrolment.is_active = False
        enrolment.payment_status = Enrolment.PaymentStatus.PENDING
        enrolment.save(update_fields=['status', 'is_active', 'payment_status'])

    if created:
        create_notification(
            recipient=student,
            title='Paid-course enrolment created',
            message=f'Your enrolment request for {course.title} is pending payment.',
            notification_type=Notification.NotificationType.PAYMENT,
            related_url=reverse('learning:payment_course', args=[course.slug]),
            dedupe_key=f'paid-enrolment:{enrolment.pk}:created'
        )

    return enrolment, created


def payment_file_extension(filename):
    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def validate_payment_proof(uploaded_file, required=False):

    if not uploaded_file:
        if required:
            raise ValidationError('Proof of payment is required.')
        return

    filename = uploaded_file.name or ''

    if len(filename) > 255:
        raise ValidationError('The filename is too long.')

    extension = payment_file_extension(filename)

    if not extension or extension in DANGEROUS_PAYMENT_EXTENSIONS or extension not in PAYMENT_PROOF_EXTENSIONS:
        raise ValidationError('The selected proof file type is not allowed.')

    if uploaded_file.size <= 0:
        raise ValidationError('The proof file is empty.')

    if uploaded_file.size > 5 * 1024 * 1024:
        raise ValidationError('The proof file exceeds the maximum size of 5 MB.')


def proof_required_for_method(method, settings_obj=None):

    settings_obj = settings_obj or get_learning_payment_settings()

    if method in [Payment.PaymentMethod.MPESA, Payment.PaymentMethod.AIRTEL, Payment.PaymentMethod.MIXX]:
        return settings_obj.require_proof_for_mobile_money

    if method == Payment.PaymentMethod.BANK:
        return settings_obj.require_proof_for_bank_transfer

    return False


def payment_admin_users():

    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.filter(
        is_active=True
    ).filter(
        models.Q(is_superuser=True)
        | models.Q(user_permissions__codename='verify_learning_payment')
        | models.Q(groups__permissions__codename='verify_learning_payment')
    ).distinct()


@transaction.atomic
def submit_course_payment(student, enrolment, cleaned_data):

    enrolment = Enrolment.objects.select_for_update().select_related('course').get(pk=enrolment.pk)

    if enrolment.student_id != student.id:
        raise PermissionDenied('You cannot submit payment for this enrolment.')

    course = enrolment.course

    if course.is_free:
        raise ValidationError('This course is free and does not require payment.')

    if enrolment.status != Enrolment.Status.PENDING:
        raise ValidationError('This enrolment is not awaiting payment.')

    pending = Payment.objects.select_for_update().filter(
        enrolment=enrolment,
        status=Payment.Status.PENDING
    ).first()

    if pending:
        return pending

    method = cleaned_data['payment_method']
    reference = cleaned_data['transaction_reference'].strip().upper()
    proof = cleaned_data.get('proof_of_payment')
    settings_obj = get_learning_payment_settings()

    if not reference:
        raise ValidationError('Transaction reference is required.')

    if Payment.objects.filter(transaction_reference=reference).exclude(status=Payment.Status.REJECTED).exists():
        raise ValidationError('This transaction reference has already been used.')

    validate_payment_proof(
        proof,
        required=proof_required_for_method(method, settings_obj)
    )

    payment = Payment.objects.create(
        student=student,
        course=course,
        enrolment=enrolment,
        amount=get_course_payable_amount(course),
        currency=settings_obj.currency,
        payment_method=method,
        transaction_reference=reference,
        proof_of_payment=proof,
        original_filename=proof.name if proof else '',
        proof_file_size=proof.size if proof else 0,
        student_notes=cleaned_data.get('student_notes', ''),
        submitted_at=timezone.now()
    )

    log_payment_audit(
        payment,
        PaymentAuditLog.Action.SUBMITTED,
        actor=student,
        previous_status='',
        note='Payment submitted by learner.'
    )

    if (
        enrolment.status != Enrolment.Status.PENDING
        or enrolment.payment_status != Enrolment.PaymentStatus.PENDING
        or enrolment.is_active
    ):
        enrolment.status = Enrolment.Status.PENDING
        enrolment.payment_status = Enrolment.PaymentStatus.PENDING
        enrolment.is_active = False
        enrolment.save(
            update_fields=[
                'status',
                'payment_status',
                'is_active',
            ]
        )

    create_notification(
        recipient=student,
        title='Payment submitted',
        message=f'Your payment for {course.title} is awaiting verification.',
        notification_type=Notification.NotificationType.PAYMENT,
        related_url=reverse('learning:payment_detail', args=[payment.pk]),
        dedupe_key=f'learning-payment:{payment.pk}:submitted-student'
    )

    for admin_user in payment_admin_users():
        create_notification(
            recipient=admin_user,
            title='Payment awaiting verification',
            message=f'{student} submitted payment for {course.title}.',
            notification_type=Notification.NotificationType.PAYMENT,
            related_url=reverse('learning:admin_payment_detail', args=[payment.pk]),
            dedupe_key=f'learning-payment:{payment.pk}:submitted-admin:{admin_user.pk}'
        )

    send_payment_lifecycle_email(
        payment,
        'submitted'
    )

    return payment


@transaction.atomic
def confirm_payment(payment, administrator):

    payment = Payment.objects.select_for_update().select_related('enrolment', 'course', 'student').get(pk=payment.pk)
    enrolment = Enrolment.objects.select_for_update().get(pk=payment.enrolment_id)

    if not administrator.is_staff and not administrator.has_perm('learning.verify_learning_payment'):
        raise PermissionDenied('You cannot verify payments.')

    if payment.status == Payment.Status.PAID:
        return payment

    if payment.status != Payment.Status.PENDING:
        raise ValidationError('Only pending payments can be confirmed.')

    if payment.amount != get_course_payable_amount(payment.course):
        raise ValidationError('Payment amount does not match the current course amount.')

    previous_status = payment.status
    payment.status = Payment.Status.PAID
    payment.verified_by = administrator
    payment.verified_at = timezone.now()
    payment.rejected_by = None
    payment.rejected_at = None
    payment.administrator_notes = ''
    payment.save()

    log_payment_audit(
        payment,
        PaymentAuditLog.Action.CONFIRMED,
        actor=administrator,
        previous_status=previous_status,
        note='Payment confirmed and enrolment activated.'
    )

    enrolment.payment_status = Enrolment.PaymentStatus.PAID
    if enrolment.status != Enrolment.Status.COMPLETED:
        enrolment.status = Enrolment.Status.ACTIVE
    enrolment.is_active = True
    if not enrolment.activated_at:
        enrolment.activated_at = timezone.now()
    enrolment.save(update_fields=['payment_status', 'status', 'is_active', 'activated_at'])

    create_notification(
        recipient=payment.student,
        title='Payment confirmed',
        message=f'Your payment for {payment.course.title} has been confirmed and access is active.',
        notification_type=Notification.NotificationType.PAYMENT,
        related_url=payment.course.get_absolute_url(),
        dedupe_key=f'learning-payment:{payment.pk}:confirmed'
    )

    send_payment_lifecycle_email(
        payment,
        'confirmed'
    )

    return payment


@transaction.atomic
def reject_payment(payment, administrator, reason):

    if not reason.strip():
        raise ValidationError('Rejection reason is required.')

    payment = Payment.objects.select_for_update().select_related('enrolment', 'course', 'student').get(pk=payment.pk)

    if not administrator.is_staff and not administrator.has_perm('learning.reject_learning_payment'):
        raise PermissionDenied('You cannot reject payments.')

    if payment.status == Payment.Status.REJECTED:
        return payment

    if payment.status != Payment.Status.PENDING:
        raise ValidationError('Only pending payments can be rejected.')

    previous_status = payment.status
    payment.status = Payment.Status.REJECTED
    payment.administrator_notes = reason
    payment.rejected_by = administrator
    payment.rejected_at = timezone.now()
    payment.save()

    log_payment_audit(
        payment,
        PaymentAuditLog.Action.REJECTED,
        actor=administrator,
        previous_status=previous_status,
        note=reason
    )

    enrolment = payment.enrolment
    enrolment.payment_status = Enrolment.PaymentStatus.REJECTED
    enrolment.status = Enrolment.Status.PENDING
    enrolment.is_active = False
    enrolment.save(update_fields=['payment_status', 'status', 'is_active'])

    create_notification(
        recipient=payment.student,
        title='Payment rejected',
        message=f'Your payment for {payment.course.title} was rejected. Please review and resubmit.',
        notification_type=Notification.NotificationType.PAYMENT,
        related_url=reverse('learning:payment_detail', args=[payment.pk]),
        dedupe_key=f'learning-payment:{payment.pk}:rejected'
    )

    send_payment_lifecycle_email(
        payment,
        'rejected'
    )

    return payment


@transaction.atomic
def mark_payment_refunded(payment, administrator, reason):

    if not reason.strip():
        raise ValidationError('Refund reason is required.')

    payment = Payment.objects.select_for_update().select_related('enrolment', 'course', 'student').get(pk=payment.pk)

    if not administrator.is_staff and not administrator.has_perm('learning.refund_learning_payment'):
        raise PermissionDenied('You cannot refund payments.')

    if payment.status == Payment.Status.REFUNDED:
        return payment

    if payment.status != Payment.Status.PAID:
        raise ValidationError('Only paid payments can be refunded.')

    previous_status = payment.status
    payment.status = Payment.Status.REFUNDED
    payment.refund_reason = reason
    payment.refunded_by = administrator
    payment.refunded_at = timezone.now()
    payment.save()

    log_payment_audit(
        payment,
        PaymentAuditLog.Action.REFUNDED,
        actor=administrator,
        previous_status=previous_status,
        note=reason
    )

    enrolment = payment.enrolment
    enrolment.payment_status = Enrolment.PaymentStatus.REFUNDED
    enrolment.status = Enrolment.Status.SUSPENDED
    enrolment.is_active = False
    enrolment.save(update_fields=['payment_status', 'status', 'is_active'])

    create_notification(
        recipient=payment.student,
        title='Payment refunded',
        message=f'Your payment for {payment.course.title} was marked refunded and access is suspended.',
        notification_type=Notification.NotificationType.PAYMENT,
        related_url=reverse('learning:payment_detail', args=[payment.pk]),
        dedupe_key=f'learning-payment:{payment.pk}:refunded'
    )

    send_payment_lifecycle_email(
        payment,
        'refunded'
    )

    return payment


def quiz_is_accessible(student, quiz):

    lesson = quiz.lesson

    if lesson.is_preview:

        return None

    enrolment = get_active_enrolment(
        student,
        quiz.course
    )

    if not enrolment:

        raise PermissionDenied(
            'You must be actively enrolled to access this quiz.'
        )

    return enrolment


@transaction.atomic
def start_quiz_attempt(student, quiz):

    quiz = quiz.__class__.objects.select_for_update().select_related(
        'lesson',
        'lesson__module',
        'lesson__module__course'
    ).get(
        pk=quiz.pk
    )

    if not quiz.is_published:

        raise PermissionDenied(
            'This quiz is not available.'
        )

    enrolment = quiz_is_accessible(
        student,
        quiz
    )

    active_attempt = QuizAttempt.objects.select_for_update().filter(
        student=student,
        quiz=quiz,
        status=QuizAttempt.Status.IN_PROGRESS
    ).first()

    if active_attempt:

        expire_quiz_attempt_if_needed(
            active_attempt
        )

        if active_attempt.status == QuizAttempt.Status.IN_PROGRESS:

            return active_attempt

    used_attempts = QuizAttempt.objects.select_for_update().filter(
        student=student,
        quiz=quiz
    ).count()

    if used_attempts >= quiz.attempts_allowed:

        raise ValidationError(
            'You have used all allowed attempts for this quiz.'
        )

    next_attempt = (
        QuizAttempt.objects.filter(
            student=student,
            quiz=quiz
        ).aggregate(
            highest=Max('attempt_number')
        )['highest'] or 0
    ) + 1

    expires_at = None

    if quiz.time_limit_minutes:

        expires_at = timezone.now() + timedelta(
            minutes=quiz.time_limit_minutes
        )

    attempt = QuizAttempt.objects.create(
        student=student,
        quiz=quiz,
        enrolment=enrolment,
        attempt_number=next_attempt,
        expires_at=expires_at,
        total_possible_marks=quiz.total_marks
    )

    for question in quiz.questions.all():

        StudentAnswer.objects.get_or_create(
            attempt=attempt,
            question=question
        )

    return attempt


@transaction.atomic
def expire_quiz_attempt_if_needed(attempt):

    attempt = QuizAttempt.objects.select_for_update().select_related(
        'quiz'
    ).get(
        pk=attempt.pk
    )

    if (
        attempt.status == QuizAttempt.Status.IN_PROGRESS
        and attempt.expires_at
        and timezone.now() >= attempt.expires_at
    ):

        _grade_attempt(
            attempt,
            submitted_at=attempt.expires_at,
            expired=True
        )

    return attempt


@transaction.atomic
def submit_quiz_attempt(attempt, submitted_answers):

    attempt = QuizAttempt.objects.select_for_update().select_related(
        'quiz',
        'quiz__lesson',
        'quiz__lesson__module',
        'quiz__lesson__module__course',
        'student'
    ).get(
        pk=attempt.pk
    )

    if attempt.status != QuizAttempt.Status.IN_PROGRESS:

        raise ValidationError(
            'This attempt has already been submitted.'
        )

    if attempt.expires_at and timezone.now() >= attempt.expires_at:

        return expire_quiz_attempt_if_needed(
            attempt
        )

    questions = attempt.quiz.questions.prefetch_related(
        'choices'
    )

    for question in questions:

        answer, created = StudentAnswer.objects.get_or_create(
            attempt=attempt,
            question=question
        )

        payload = submitted_answers.get(
            str(question.pk),
            submitted_answers.get(question.pk, {})
        )

        if question.question_type == Question.QuestionType.SHORT_ANSWER:

            answer.text_answer = (
                payload.get('text_answer', '')
                if isinstance(payload, dict)
                else str(payload or '')
            )
            answer.selected_choices.clear()
            answer.save(
                update_fields=[
                    'text_answer',
                    'updated_at',
                ]
            )

        else:

            choice_ids = payload.get(
                'choice_ids',
                []
            ) if isinstance(payload, dict) else payload

            if not isinstance(choice_ids, (list, tuple, set)):

                choice_ids = [
                    choice_ids,
                ] if choice_ids else []

            try:

                normalized_choice_ids = {
                    int(choice_id)
                    for choice_id in choice_ids
                    if str(choice_id).strip()
                }

            except (TypeError, ValueError):

                raise ValidationError(
                    'One or more submitted choices are invalid.'
                )

            valid_choices = list(
                question.choices.filter(
                    pk__in=normalized_choice_ids
                )
            )
            valid_choice_ids = {
                choice.pk
                for choice in valid_choices
            }

            if valid_choice_ids != normalized_choice_ids:

                raise ValidationError(
                    'One or more submitted choices are invalid.'
                )

            answer.text_answer = ''
            answer.save(
                update_fields=[
                    'text_answer',
                    'updated_at',
                ]
            )
            answer.selected_choices.set(
                valid_choices
            )

    return _grade_attempt(
        attempt,
        submitted_at=timezone.now()
    )


def _grade_attempt(attempt, submitted_at=None, expired=False):

    objective_marks = Decimal('0')
    total_possible = Decimal('0')
    requires_manual = False

    questions = attempt.quiz.questions.prefetch_related(
        'choices'
    )

    for question in questions:

        total_possible += question.marks
        answer, created = StudentAnswer.objects.get_or_create(
            attempt=attempt,
            question=question
        )

        answer.objective_marks_awarded = Decimal('0')
        answer.is_correct = False

        if question.question_type == Question.QuestionType.SHORT_ANSWER:

            requires_manual = True

        else:

            selected_ids = set(
                answer.selected_choices.values_list(
                    'pk',
                    flat=True
                )
            )
            correct_ids = set(
                question.choices.filter(
                    is_correct=True
                ).values_list(
                    'pk',
                    flat=True
                )
            )

            if selected_ids and selected_ids == correct_ids:

                answer.objective_marks_awarded = question.marks
                answer.is_correct = True
                objective_marks += question.marks

        answer.save(
            update_fields=[
                'objective_marks_awarded',
                'is_correct',
                'updated_at',
            ]
        )

    attempt.objective_marks_awarded = objective_marks
    attempt.manual_marks_awarded = Decimal('0')
    attempt.total_possible_marks = total_possible
    attempt.total_marks_awarded = objective_marks
    attempt.requires_manual_grading = requires_manual
    attempt.submitted_at = submitted_at or timezone.now()

    if requires_manual:

        attempt.status = QuizAttempt.Status.AWAITING_MANUAL_GRADING
        attempt.passed = False

    else:

        attempt.status = QuizAttempt.Status.GRADED
        attempt.graded_at = timezone.now()
        _finalize_attempt_score(
            attempt
        )

    if expired and not requires_manual:

        attempt.status = QuizAttempt.Status.EXPIRED

    attempt.save()
    _send_submission_notifications(
        attempt
    )

    if attempt.status == QuizAttempt.Status.GRADED and attempt.passed:

        mark_quiz_lesson_complete(
            attempt
        )

    return attempt


def _finalize_attempt_score(attempt):

    if attempt.total_possible_marks:

        attempt.percentage = (
            attempt.total_marks_awarded * Decimal('100')
            / attempt.total_possible_marks
        ).quantize(
            Decimal('0.01')
        )

    else:

        attempt.percentage = Decimal('0')

    attempt.passed = attempt.percentage >= Decimal(
        str(attempt.quiz.passing_score)
    )


def _send_submission_notifications(attempt):

    result_url = reverse(
        'learning:quiz_result',
        args=[
            attempt.pk,
        ]
    )

    create_notification(
        recipient=attempt.student,
        title='Quiz submitted',
        message=f'Your attempt for {attempt.quiz.title} has been submitted.',
        notification_type=Notification.NotificationType.QUIZ,
        related_url=result_url,
        dedupe_key=f'quiz-attempt:{attempt.pk}:submitted'
    )

    if attempt.status == QuizAttempt.Status.AWAITING_MANUAL_GRADING:

        create_notification(
            recipient=attempt.student,
            title='Quiz awaiting manual grading',
            message=f'{attempt.quiz.title} includes short-answer questions and is awaiting grading.',
            notification_type=Notification.NotificationType.QUIZ,
            related_url=result_url,
            dedupe_key=f'quiz-attempt:{attempt.pk}:awaiting'
        )

        create_notification(
            recipient=attempt.quiz.course.instructor,
            title='Quiz attempt needs grading',
            message=f'{attempt.student} submitted {attempt.quiz.title}.',
            notification_type=Notification.NotificationType.QUIZ,
            related_url=reverse(
                'learning:instructor_quiz_attempt_grade',
                args=[
                    attempt.pk,
                ]
            ),
            dedupe_key=f'quiz-attempt:{attempt.pk}:instructor-grading'
        )

    elif attempt.status == QuizAttempt.Status.GRADED:

        create_notification(
            recipient=attempt.student,
            title='Quiz automatically graded',
            message=f'Your score for {attempt.quiz.title} is {attempt.percentage}%.',
            notification_type=Notification.NotificationType.QUIZ,
            related_url=result_url,
            dedupe_key=f'quiz-attempt:{attempt.pk}:auto-graded'
        )

        create_notification(
            recipient=attempt.student,
            title='Quiz passed' if attempt.passed else 'Quiz failed',
            message=f'You {"passed" if attempt.passed else "did not pass"} {attempt.quiz.title}.',
            notification_type=Notification.NotificationType.QUIZ,
            related_url=result_url,
            dedupe_key=f'quiz-attempt:{attempt.pk}:pass-state'
        )


@transaction.atomic
def grade_short_answers(attempt, grader, grading_data):

    attempt = QuizAttempt.objects.select_for_update().select_related(
        'quiz',
        'quiz__lesson',
        'quiz__lesson__module',
        'quiz__lesson__module__course',
        'student'
    ).get(
        pk=attempt.pk
    )

    ensure_course_owner(
        grader,
        attempt.quiz.course
    )

    if attempt.status not in [
        QuizAttempt.Status.AWAITING_MANUAL_GRADING,
        QuizAttempt.Status.GRADED,
    ]:

        raise ValidationError(
            'This attempt is not ready for manual grading.'
        )

    manual_total = Decimal('0')

    for answer in attempt.answers.select_related('question').filter(
        question__question_type=Question.QuestionType.SHORT_ANSWER
    ):

        data = grading_data.get(
            str(answer.pk),
            grading_data.get(answer.pk, {})
        )
        marks = Decimal(
            str(data.get('marks', 0) or 0)
        )

        if marks < 0 or marks > answer.question.marks:

            raise ValidationError(
                'Manual marks must be between zero and the question marks.'
            )

        answer.manual_marks_awarded = marks
        answer.instructor_feedback = data.get(
            'feedback',
            ''
        )
        answer.graded_by = grader
        answer.graded_at = timezone.now()
        answer.save()
        manual_total += marks

    attempt.manual_marks_awarded = manual_total
    attempt.total_marks_awarded = attempt.objective_marks_awarded + manual_total
    attempt.instructor_feedback = grading_data.get(
        'instructor_feedback',
        attempt.instructor_feedback
    )
    attempt.status = QuizAttempt.Status.GRADED
    attempt.requires_manual_grading = False
    attempt.graded_by = grader
    attempt.graded_at = timezone.now()
    _finalize_attempt_score(
        attempt
    )
    attempt.save()

    create_notification(
        recipient=attempt.student,
        title='Quiz manually graded',
        message=f'Your result for {attempt.quiz.title} is now available.',
        notification_type=Notification.NotificationType.QUIZ,
        related_url=reverse(
            'learning:quiz_result',
            args=[
                attempt.pk,
            ]
        ),
        dedupe_key=f'quiz-attempt:{attempt.pk}:manual-graded'
    )

    create_notification(
        recipient=attempt.student,
        title='Quiz passed' if attempt.passed else 'Quiz failed',
        message=f'You {"passed" if attempt.passed else "did not pass"} {attempt.quiz.title}.',
        notification_type=Notification.NotificationType.QUIZ,
        related_url=reverse(
            'learning:quiz_result',
            args=[
                attempt.pk,
            ]
        ),
        dedupe_key=f'quiz-attempt:{attempt.pk}:manual-pass-state'
    )

    if attempt.passed:

        mark_quiz_lesson_complete(
            attempt
        )

    return attempt


def mark_quiz_lesson_complete(attempt):

    if not attempt.enrolment:

        return None

    quiz = attempt.quiz

    if quiz.is_compulsory or quiz.lesson.is_compulsory:

        return mark_lesson_complete(
            attempt.student,
            attempt.enrolment,
            quiz.lesson
        )

    return evaluate_course_completion(
        attempt.enrolment
    )


def assignment_file_extension(filename):

    return filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''


def validate_assignment_file(assignment, uploaded_file):

    if not uploaded_file:

        return

    filename = uploaded_file.name or ''

    if len(filename) > 255:

        raise ValidationError(
            'The filename is too long.'
        )

    extension = assignment_file_extension(
        filename
    )

    if not extension or extension in DANGEROUS_ASSIGNMENT_EXTENSIONS:

        raise ValidationError(
            'The selected file type is not allowed.'
        )

    if extension not in assignment.allowed_extension_list:

        raise ValidationError(
            'The selected file type is not allowed.'
        )

    if uploaded_file.size <= 0:

        raise ValidationError(
            'The selected file is empty.'
        )

    max_bytes = assignment.maximum_file_size_mb * 1024 * 1024

    if uploaded_file.size > max_bytes:

        raise ValidationError(
            f'The file exceeds the maximum size of {assignment.maximum_file_size_mb} MB.'
        )


def can_access_assignment(user, assignment):

    if not assignment.is_published and not (
        user.is_authenticated
        and (
            user.is_staff
            or assignment.course.instructor_id == user.id
        )
    ):

        raise PermissionDenied(
            'This assignment is not available.'
        )

    if assignment.lesson.is_preview:

        return None

    if user.is_authenticated and (
        user.is_staff
        or assignment.course.instructor_id == user.id
    ):

        return None

    if not user.is_authenticated:

        raise PermissionDenied(
            'Please sign in and enrol to access this assignment.'
        )

    enrolment = get_active_enrolment(
        user,
        assignment.course
    )

    if not enrolment:

        raise PermissionDenied(
            'You must be actively enrolled to access this assignment.'
        )

    return enrolment


def assignment_accepts_submission(assignment):

    if (
        assignment.due_date
        and timezone.now() > assignment.due_date
        and not assignment.allow_late_submission
    ):

        raise ValidationError(
            'The assignment deadline has passed.'
        )


@transaction.atomic
def get_or_create_assignment_draft(student, assignment):

    assignment = Assignment.objects.select_for_update().select_related(
        'lesson',
        'lesson__module',
        'lesson__module__course'
    ).get(
        pk=assignment.pk
    )

    if not assignment.is_published:

        raise PermissionDenied(
            'This assignment is not available.'
        )

    assignment_accepts_submission(
        assignment
    )

    enrolment = get_active_enrolment(
        student,
        assignment.course
    )

    if not enrolment:

        raise PermissionDenied(
            'You must be actively enrolled to submit this assignment.'
        )

    draft = AssignmentSubmission.objects.select_for_update().filter(
        assignment=assignment,
        student=student,
        status=AssignmentSubmission.Status.DRAFT
    ).first()

    if draft:

        return draft, enrolment

    used_attempts = AssignmentSubmission.objects.select_for_update().filter(
        assignment=assignment,
        student=student
    ).count()

    if used_attempts >= assignment.maximum_attempts:

        raise ValidationError(
            'You have used all permitted submission attempts.'
        )

    latest_returned = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=student,
        status=AssignmentSubmission.Status.RETURNED
    ).order_by(
        '-attempt_number'
    ).first()

    if used_attempts and not (
        assignment.allow_resubmission
        and latest_returned
    ):

        raise ValidationError(
            'Resubmission is not available for this assignment.'
        )

    next_attempt = (
        AssignmentSubmission.objects.filter(
            assignment=assignment,
            student=student
        ).aggregate(
            highest=Max('attempt_number')
        )['highest'] or 0
    ) + 1

    draft = AssignmentSubmission.objects.create(
        assignment=assignment,
        student=student,
        enrolment=enrolment,
        attempt_number=next_attempt
    )

    return draft, enrolment


@transaction.atomic
def save_assignment_draft(submission, student, cleaned_data):

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course',
        'student'
    ).get(
        pk=submission.pk
    )

    if submission.student_id != student.id:

        raise PermissionDenied(
            'You cannot edit this submission.'
        )

    if submission.status != AssignmentSubmission.Status.DRAFT:

        raise ValidationError(
            'Submitted work cannot be edited.'
        )

    assignment_accepts_submission(
        submission.assignment
    )

    uploaded_file = cleaned_data.get(
        'submission_file'
    )

    if uploaded_file:

        validate_assignment_file(
            submission.assignment,
            uploaded_file
        )
        submission.submission_file = uploaded_file
        submission.original_filename = uploaded_file.name
        submission.file_size = uploaded_file.size

    submission.submission_text = cleaned_data.get(
        'submission_text',
        ''
    )
    submission.save()

    return submission


def validate_assignment_submission_content(submission):

    assignment = submission.assignment

    if assignment.require_text_submission and not submission.submission_text.strip():

        raise ValidationError(
            'A written response is required.'
        )

    if assignment.require_file_submission and not submission.submission_file:

        raise ValidationError(
            'A file submission is required.'
        )


@transaction.atomic
def submit_assignment(submission, student):

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course',
        'student'
    ).get(
        pk=submission.pk
    )

    if submission.student_id != student.id:

        raise PermissionDenied(
            'You cannot submit this assignment.'
        )

    if submission.status == AssignmentSubmission.Status.SUBMITTED:

        return submission

    if submission.status != AssignmentSubmission.Status.DRAFT:

        raise ValidationError(
            'This submission cannot be finalized.'
        )

    assignment_accepts_submission(
        submission.assignment
    )
    validate_assignment_submission_content(
        submission
    )

    if submission.submission_file:

        validate_assignment_file(
            submission.assignment,
            submission.submission_file
        )

    now = timezone.now()
    submission.is_late = bool(
        submission.assignment.due_date
        and now > submission.assignment.due_date
    )
    submission.status = AssignmentSubmission.Status.SUBMITTED
    submission.submitted_at = now
    submission.save()

    detail_url = reverse(
        'learning:submission_detail',
        args=[
            submission.pk,
        ]
    )

    create_notification(
        recipient=submission.student,
        title='Assignment submitted',
        message=f'Your submission for {submission.assignment.title} has been received.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=detail_url,
        dedupe_key=f'assignment-submission:{submission.pk}:submitted-student'
    )
    create_notification(
        recipient=submission.assignment.course.instructor,
        title='Assignment submitted',
        message=f'{submission.student} submitted {submission.assignment.title}.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=reverse(
            'learning:instructor_submission_detail',
            args=[
                submission.pk,
            ]
        ),
        dedupe_key=f'assignment-submission:{submission.pk}:submitted-instructor'
    )

    return submission


@transaction.atomic
def mark_submission_under_review(submission, instructor):

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course'
    ).get(
        pk=submission.pk
    )

    ensure_course_owner(
        instructor,
        submission.assignment.course
    )

    if submission.status == AssignmentSubmission.Status.SUBMITTED:

        submission.status = AssignmentSubmission.Status.UNDER_REVIEW
        submission.save(
            update_fields=[
                'status',
                'updated_at',
            ]
        )

    return submission


@transaction.atomic
def grade_assignment_submission(submission, grader, score, feedback):

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course',
        'student',
        'enrolment'
    ).get(
        pk=submission.pk
    )

    ensure_course_owner(
        grader,
        submission.assignment.course
    )

    if submission.status not in [
        AssignmentSubmission.Status.SUBMITTED,
        AssignmentSubmission.Status.UNDER_REVIEW,
        AssignmentSubmission.Status.GRADED,
    ]:

        raise ValidationError(
            'This submission is not ready for grading.'
        )

    score = Decimal(
        str(score)
    )

    if score < 0 or score > submission.assignment.maximum_score:

        raise ValidationError(
            'Score must be between zero and the maximum score.'
        )

    submission.score = score
    submission.passed = score >= submission.assignment.passing_score
    submission.instructor_feedback = feedback
    submission.graded_by = grader
    submission.graded_at = timezone.now()
    submission.status = AssignmentSubmission.Status.GRADED
    submission.save()

    create_notification(
        recipient=submission.student,
        title='Assignment graded',
        message=f'Your submission for {submission.assignment.title} has been graded.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=reverse(
            'learning:submission_detail',
            args=[
                submission.pk,
            ]
        ),
        dedupe_key=f'assignment-submission:{submission.pk}:graded'
    )
    create_notification(
        recipient=submission.student,
        title='Assignment passed' if submission.passed else 'Assignment failed',
        message=f'You {"passed" if submission.passed else "did not pass"} {submission.assignment.title}.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=reverse(
            'learning:submission_detail',
            args=[
                submission.pk,
            ]
        ),
        dedupe_key=f'assignment-submission:{submission.pk}:pass-state'
    )

    if submission.passed:

        mark_assignment_lesson_complete(
            submission
        )

    return submission


@transaction.atomic
def return_assignment_for_revision(submission, grader, revision_message):

    if not revision_message.strip():

        raise ValidationError(
            'Revision message is required.'
        )

    submission = AssignmentSubmission.objects.select_for_update().select_related(
        'assignment',
        'assignment__lesson',
        'assignment__lesson__module',
        'assignment__lesson__module__course',
        'student'
    ).get(
        pk=submission.pk
    )

    ensure_course_owner(
        grader,
        submission.assignment.course
    )

    if not submission.assignment.allow_resubmission:

        raise ValidationError(
            'This assignment does not allow resubmission.'
        )

    used_attempts = AssignmentSubmission.objects.filter(
        assignment=submission.assignment,
        student=submission.student
    ).count()

    if used_attempts >= submission.assignment.maximum_attempts:

        raise ValidationError(
            'No submission attempts remain.'
        )

    if submission.status == AssignmentSubmission.Status.RETURNED:

        return submission

    submission.status = AssignmentSubmission.Status.RETURNED
    submission.returned_by = grader
    submission.returned_at = timezone.now()
    submission.revision_message = revision_message
    submission.save()

    create_notification(
        recipient=submission.student,
        title='Assignment returned for revision',
        message=f'{submission.assignment.title} was returned for revision.',
        notification_type=Notification.NotificationType.ASSIGNMENT,
        related_url=reverse(
            'learning:submission_detail',
            args=[
                submission.pk,
            ]
        ),
        dedupe_key=f'assignment-submission:{submission.pk}:returned'
    )

    return submission


def mark_assignment_lesson_complete(submission):

    if not submission.enrolment:

        return None

    if submission.assignment.is_compulsory or submission.assignment.lesson.is_compulsory:

        return mark_lesson_complete(
            submission.student,
            submission.enrolment,
            submission.assignment.lesson
        )

    return evaluate_course_completion(
        submission.enrolment
    )


@transaction.atomic
def publish_announcement(announcement):

    announcement = CourseAnnouncement.objects.select_for_update().select_related(
        'course'
    ).get(
        pk=announcement.pk
    )

    if not announcement.is_published:

        announcement.is_published = True
        announcement.published_at = timezone.now()
        announcement.save(
            update_fields=[
                'is_published',
                'published_at',
                'updated_at',
            ]
        )

    send_announcement_notifications(
        announcement
    )

    return announcement


@transaction.atomic
def send_announcement_notifications(announcement):

    announcement = CourseAnnouncement.objects.select_for_update().select_related(
        'course'
    ).get(
        pk=announcement.pk
    )

    if announcement.notifications_sent:

        return 0

    enrolments = Enrolment.objects.select_related(
        'student'
    ).filter(
        course=announcement.course,
        status__in=[
            Enrolment.Status.ACTIVE,
            Enrolment.Status.COMPLETED,
        ],
        is_active=True
    )

    sent_count = 0

    for enrolment in enrolments:

        create_notification(
            recipient=enrolment.student,
            title=announcement.title,
            message=announcement.message,
            notification_type=Notification.NotificationType.ANNOUNCEMENT,
            related_url=reverse('learning:announcements'),
            dedupe_key=f'announcement:{announcement.pk}:student:{enrolment.student_id}'
        )
        sent_count += 1

    announcement.notifications_sent = True
    announcement.save(
        update_fields=[
            'notifications_sent',
            'updated_at',
        ]
    )

    return sent_count
