from django import forms

from .models import SoftwareOrder


class SoftwareOrderForm(forms.ModelForm):

    class Meta:

        model = SoftwareOrder

        fields = (
            'customer_name',
            'customer_phone',
            'customer_email',
            'business_name',
            'payment_method',
            'payment_reference',
        )

        widgets = {
            'customer_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                }
            ),
            'customer_phone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                }
            ),
            'customer_email': forms.EmailInput(
                attrs={
                    'class': 'form-control',
                }
            ),
            'business_name': forms.TextInput(
                attrs={
                    'class': 'form-control',
                }
            ),
            'payment_method': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Bank transfer, mobile money, cash, etc.',
                }
            ),
            'payment_reference': forms.TextInput(
                attrs={
                    'class': 'form-control',
                }
            ),
        }
