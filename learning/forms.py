from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model

from .models import Course, Lesson, Module


User = get_user_model()


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


class CourseForm(forms.ModelForm):

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


class ModuleForm(forms.ModelForm):

    class Meta:

        model = Module

        fields = (
            'title',
            'description',
            'order',
            'is_published',
        )


class LessonForm(forms.ModelForm):

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
