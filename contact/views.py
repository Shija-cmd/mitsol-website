from django.shortcuts import render
from django.core.mail import send_mail
from django.conf import settings

from .forms import ContactForm


def contact_page(request):

    success = False
    error = False

    if request.method == 'POST':
        form = ContactForm(request.POST)
    else:
        form = ContactForm()

    if form.is_valid():

        message = form.save()

    try:

        send_mail(

            subject=f'New Contact Message — {message.name}',

            message=f'''
Name: {message.name}

Email: {message.email}

Message:

{message.message}
''',

            from_email=settings.DEFAULT_FROM_EMAIL,

            recipient_list=[
                'info@mitsol.com.se'
            ],

            fail_silently=False

        )

        success = True

        form = ContactForm()

    except Exception as e:
        print(f"Email sending failed: {e}")
        error = True

    else:

        form = ContactForm()

    return render(
        request,
        'contact/contact.html',
        {
            'form': form,
            'success': success,
            'error': error
        }
    )