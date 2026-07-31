from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import Assignment, AssignmentSubmission, Choice, Course, CourseAnnouncement, CourseReview, Lesson, Module, Payment, Question, Quiz
from .services import proof_required_for_method, validate_assignment_file, validate_payment_proof, validate_review_comment


User = get_user_model()


class BootstrapFormMixin:

    def apply_bootstrap_styles(self):

        for field_name, field in self.fields.items():

            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):

                css_class = 'form-check-input'

            elif isinstance(widget, forms.Select):

                css_class = 'form-select'

            elif isinstance(widget, forms.ClearableFileInput):

                css_class = 'form-control'

            else:

                css_class = 'form-control'

            existing_class = widget.attrs.get(
                'class',
                ''
            )

            widget.attrs['class'] = (
                f'{existing_class} {css_class}'.strip()
                if css_class not in existing_class
                else existing_class
            )

            if not isinstance(
                widget,
                (
                    forms.CheckboxInput,
                    forms.Select,
                    forms.ClearableFileInput,
                    forms.Textarea,
                )
            ):

                widget.attrs.setdefault(
                    'placeholder',
                    field.label
                )


class StudentRegistrationForm(UserCreationForm):

    email = forms.EmailField(
        required=True,
        label='Email address'
    )

    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='First name'
    )

    last_name = forms.CharField(
        max_length=150,
        required=False,
        label='Last name'
    )

    class Meta:

        model = User

        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'password1',
            'password2',
        )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        placeholders = {
            'username': 'Choose a username',
            'first_name': 'Enter your first name',
            'last_name': 'Enter your last name',
            'email': 'you@example.com',
            'password1': 'Create a secure password',
            'password2': 'Repeat your password',
        }

        for field_name, field in self.fields.items():

            field.widget.attrs.update(
                {
                    'class': 'form-control',
                    'placeholder': placeholders.get(
                        field_name,
                        ''
                    ),
                }
            )

        self.fields['username'].help_text = (
            'Use letters, numbers, and @/./+/-/_ only.'
        )
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''


class CourseForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = Course

        fields = (
            'category',
            'title',
            'short_description',
            'full_description',
            'cover_image',
            'promotional_video_url',
            'level',
            'language',
            'delivery_mode',
            'estimated_duration',
            'price',
            'discount_price',
            'is_free',
            'learning_outcomes',
            'requirements',
            'target_audience',
            'status',
            'is_featured',
        )

        widgets = {
            'short_description': forms.Textarea(
                attrs={
                    'rows': 3,
                }
            ),
            'full_description': forms.Textarea(
                attrs={
                    'rows': 6,
                }
            ),
            'learning_outcomes': forms.Textarea(
                attrs={
                    'rows': 5,
                }
            ),
            'requirements': forms.Textarea(
                attrs={
                    'rows': 4,
                }
            ),
            'target_audience': forms.Textarea(
                attrs={
                    'rows': 4,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()

    def clean(self):

        cleaned_data = super().clean()
        is_free = cleaned_data.get('is_free')
        price = cleaned_data.get('price')

        if not is_free and price <= 0:

            self.add_error(
                'price',
                'Paid courses must have a price greater than zero.'
            )

        return cleaned_data


class ModuleForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = Module

        fields = (
            'title',
            'description',
            'order',
            'is_published',
        )

        widgets = {
            'description': forms.Textarea(
                attrs={
                    'rows': 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()


class LessonForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = Lesson

        fields = (
            'module',
            'title',
            'lesson_type',
            'written_content',
            'video_url',
            'video_file',
            'downloadable_file',
            'source_code_file',
            'external_resource_url',
            'duration_minutes',
            'order',
            'is_preview',
            'is_compulsory',
            'is_published',
        )

        widgets = {
            'written_content': forms.Textarea(
                attrs={
                    'rows': 8,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        course = kwargs.pop(
            'course',
            None
        )

        super().__init__(*args, **kwargs)

        if course:

            self.fields['module'].queryset = course.modules.all()

        self.apply_bootstrap_styles()


class CourseAnnouncementForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = CourseAnnouncement

        fields = (
            'course',
            'title',
            'message',
            'is_published',
        )

        widgets = {
            'message': forms.Textarea(
                attrs={
                    'rows': 6,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop(
            'user',
            None
        )

        super().__init__(*args, **kwargs)

        if user and not user.is_staff:

            self.fields['course'].queryset = Course.objects.filter(
                instructor=user
            )

        self.apply_bootstrap_styles()


class QuizForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = Quiz

        fields = (
            'lesson',
            'title',
            'instructions',
            'passing_score',
            'time_limit_minutes',
            'attempts_allowed',
            'randomise_questions',
            'randomise_choices',
            'show_score_after_submission',
            'show_correct_answers',
            'is_compulsory',
            'is_published',
        )

        widgets = {
            'instructions': forms.Textarea(
                attrs={
                    'rows': 5,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop(
            'user',
            None
        )

        super().__init__(*args, **kwargs)

        lessons = Lesson.objects.select_related(
            'module',
            'module__course'
        ).filter(
            is_published=True
        )

        if user and not user.is_staff:

            lessons = lessons.filter(
                module__course__instructor=user
            )

        self.fields['lesson'].queryset = lessons
        self.apply_bootstrap_styles()

    def clean(self):

        cleaned_data = super().clean()
        passing_score = cleaned_data.get('passing_score')
        attempts_allowed = cleaned_data.get('attempts_allowed')
        time_limit = cleaned_data.get('time_limit_minutes')

        if passing_score is not None and not 0 <= passing_score <= 100:

            self.add_error(
                'passing_score',
                'Passing score must be between 0 and 100.'
            )

        if attempts_allowed is not None and attempts_allowed < 1:

            self.add_error(
                'attempts_allowed',
                'Attempts allowed must be at least 1.'
            )

        if time_limit is not None and time_limit <= 0:

            self.add_error(
                'time_limit_minutes',
                'Time limit must be greater than zero.'
            )

        return cleaned_data


class QuestionForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = Question

        fields = (
            'question_text',
            'question_type',
            'marks',
            'order',
            'explanation',
            'is_required',
        )

        widgets = {
            'question_text': forms.Textarea(
                attrs={
                    'rows': 4,
                }
            ),
            'explanation': forms.Textarea(
                attrs={
                    'rows': 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        self.quiz = kwargs.pop(
            'quiz',
            None
        )
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()

    def clean_order(self):

        order = self.cleaned_data['order']

        if self.quiz:

            qs = Question.objects.filter(
                quiz=self.quiz,
                order=order
            )

            if self.instance.pk:

                qs = qs.exclude(
                    pk=self.instance.pk
                )

            if qs.exists():

                raise forms.ValidationError(
                    'Another question already uses this order.'
                )

        return order

    def clean_marks(self):

        marks = self.cleaned_data['marks']

        if marks <= 0:

            raise forms.ValidationError(
                'Marks must be greater than zero.'
            )

        return marks


class ChoiceForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = Choice

        fields = (
            'choice_text',
            'is_correct',
            'order',
        )

    def __init__(self, *args, **kwargs):

        self.question = kwargs.pop(
            'question',
            None
        )
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()

    def clean_choice_text(self):

        value = self.cleaned_data['choice_text'].strip()

        if not value:

            raise forms.ValidationError(
                'Choice text is required.'
            )

        if self.question:

            qs = Choice.objects.filter(
                question=self.question,
                choice_text__iexact=value
            )

            if self.instance.pk:

                qs = qs.exclude(
                    pk=self.instance.pk
                )

            if qs.exists():

                raise forms.ValidationError(
                    'This choice already exists for the question.'
                )

        return value


class ManualQuizGradingForm(forms.Form):

    instructor_feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Overall feedback for the student',
            }
        )
    )


class QuizAttemptForm(forms.Form):

    def __init__(self, *args, **kwargs):

        self.quiz = kwargs.pop(
            'quiz'
        )
        super().__init__(*args, **kwargs)

        questions = self.quiz.questions.prefetch_related(
            'choices'
        )

        for question in questions:

            field_name = f'question_{question.pk}'

            if question.question_type == Question.QuestionType.SHORT_ANSWER:

                self.fields[field_name] = forms.CharField(
                    label=question.question_text,
                    required=question.is_required,
                    widget=forms.Textarea(
                        attrs={
                            'rows': 4,
                            'class': 'form-control',
                        }
                    )
                )

            else:

                choices = [
                    (
                        choice.pk,
                        choice.choice_text,
                    )
                    for choice in question.choices.all()
                ]

                if question.question_type == Question.QuestionType.MULTIPLE_SELECT:

                    widget = forms.CheckboxSelectMultiple
                    field_class = forms.MultipleChoiceField

                else:

                    widget = forms.RadioSelect
                    field_class = forms.ChoiceField

                self.fields[field_name] = field_class(
                    label=question.question_text,
                    choices=choices,
                    required=question.is_required,
                    widget=widget
                )

    def submitted_answers(self):

        answers = {}

        for question in self.quiz.questions.all():

            value = self.cleaned_data.get(
                f'question_{question.pk}'
            )

            if question.question_type == Question.QuestionType.SHORT_ANSWER:

                answers[str(question.pk)] = {
                    'text_answer': value or '',
                }

            else:

                choice_ids = value if isinstance(value, list) else [
                    value,
                ] if value else []
                answers[str(question.pk)] = {
                    'choice_ids': choice_ids,
                }

        return answers


class AssignmentForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = Assignment

        fields = (
            'lesson',
            'title',
            'instructions',
            'maximum_score',
            'passing_score',
            'due_date',
            'allow_late_submission',
            'allow_resubmission',
            'maximum_attempts',
            'allowed_file_extensions',
            'maximum_file_size_mb',
            'require_text_submission',
            'require_file_submission',
            'is_compulsory',
            'is_published',
        )

        widgets = {
            'instructions': forms.Textarea(
                attrs={
                    'rows': 6,
                }
            ),
            'due_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        user = kwargs.pop(
            'user',
            None
        )
        super().__init__(*args, **kwargs)

        lessons = Lesson.objects.select_related(
            'module',
            'module__course'
        ).filter(
            is_published=True
        )

        if user and not user.is_staff:

            lessons = lessons.filter(
                module__course__instructor=user
            )

        self.fields['lesson'].queryset = lessons
        self.apply_bootstrap_styles()


class AssignmentSubmissionForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = AssignmentSubmission

        fields = (
            'submission_text',
            'submission_file',
        )

        widgets = {
            'submission_text': forms.Textarea(
                attrs={
                    'rows': 8,
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        self.assignment = kwargs.pop(
            'assignment'
        )
        super().__init__(*args, **kwargs)
        self.fields['submission_text'].required = self.assignment.require_text_submission
        self.fields['submission_file'].required = (
            self.assignment.require_file_submission
            and not getattr(self.instance, 'submission_file', None)
        )
        self.apply_bootstrap_styles()

    def clean_submission_text(self):

        value = self.cleaned_data.get(
            'submission_text',
            ''
        )

        if self.assignment.require_text_submission and not value.strip():

            raise forms.ValidationError(
                'A written response is required.'
            )

        return value

    def clean_submission_file(self):

        uploaded_file = self.cleaned_data.get(
            'submission_file'
        )

        if uploaded_file:

            validate_assignment_file(
                self.assignment,
                uploaded_file
            )

        elif self.assignment.require_file_submission and not getattr(
            self.instance,
            'submission_file',
            None
        ):

            raise forms.ValidationError(
                'A file submission is required.'
            )

        return uploaded_file


class AssignmentGradingForm(BootstrapFormMixin, forms.Form):

    score = forms.DecimalField(
        min_value=0,
        label='Score'
    )

    instructor_feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 5,
            }
        )
    )

    def __init__(self, *args, **kwargs):

        self.submission = kwargs.pop(
            'submission'
        )
        super().__init__(*args, **kwargs)
        self.fields['score'].max_value = self.submission.assignment.maximum_score
        self.apply_bootstrap_styles()


class AssignmentRevisionForm(BootstrapFormMixin, forms.Form):

    revision_message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'rows': 5,
            }
        )
    )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()


class PaymentSubmissionForm(BootstrapFormMixin, forms.ModelForm):

    class Meta:

        model = Payment

        fields = (
            'payment_method',
            'transaction_reference',
            'proof_of_payment',
            'student_notes',
        )

        widgets = {
            'student_notes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):

        self.settings_obj = kwargs.pop('settings_obj', None)
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()

    def clean_transaction_reference(self):

        reference = self.cleaned_data.get('transaction_reference', '').strip().upper()

        if not reference:
            raise forms.ValidationError('Transaction reference is required.')

        if len(reference) < 3:
            raise forms.ValidationError('Transaction reference is too short.')

        return reference

    def clean(self):

        cleaned_data = super().clean()
        method = cleaned_data.get('payment_method')
        proof = cleaned_data.get('proof_of_payment')

        if method:
            try:
                validate_payment_proof(
                    proof,
                    required=proof_required_for_method(method, self.settings_obj)
                )
            except forms.ValidationError:
                raise
            except Exception as exc:
                self.add_error('proof_of_payment', str(exc))

        return cleaned_data


class PaymentReasonForm(BootstrapFormMixin, forms.Form):

    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4})
    )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()


class CourseReviewForm(BootstrapFormMixin, forms.ModelForm):

    rating = forms.ChoiceField(
        choices=[
            (5, '5 - Excellent'),
            (4, '4 - Very good'),
            (3, '3 - Good'),
            (2, '2 - Fair'),
            (1, '1 - Poor'),
        ],
        widget=forms.RadioSelect,
        error_messages={
            'required': 'Select a rating from 1 to 5.',
            'invalid_choice': 'Select a rating from 1 to 5.',
        }
    )

    class Meta:

        model = CourseReview

        fields = (
            'rating',
            'comment',
        )

        widgets = {
            'comment': forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()
        self.fields['rating'].widget.attrs['class'] = 'learning-rating-options'

    def clean_rating(self):

        try:
            rating = int(self.cleaned_data.get('rating'))
        except (TypeError, ValueError):
            raise forms.ValidationError('Select a rating from 1 to 5.')

        if rating < 1 or rating > 5:
            raise forms.ValidationError('Select a rating from 1 to 5.')

        return rating

    def clean_comment(self):

        try:
            return validate_review_comment(
                self.cleaned_data.get('comment', '')
            )
        except Exception as exc:
            raise forms.ValidationError(
                exc.messages[0] if hasattr(exc, 'messages') else str(exc)
            )


class ReviewModerationReasonForm(BootstrapFormMixin, forms.Form):

    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4})
    )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()


class CertificateVerificationForm(BootstrapFormMixin, forms.Form):

    certificate_number_or_code = forms.CharField(
        max_length=140,
        label='Certificate number or verification code'
    )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()

    def clean_certificate_number_or_code(self):

        value = self.cleaned_data.get('certificate_number_or_code', '').strip()

        if len(value) < 6:
            raise forms.ValidationError('Enter a valid certificate number or verification code.')

        return value


class CertificateRevocationForm(BootstrapFormMixin, forms.Form):

    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4})
    )

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.apply_bootstrap_styles()
