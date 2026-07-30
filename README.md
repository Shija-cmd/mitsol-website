# MITSOL Website

Official website and software store for MITSOL.

This project provides a responsive web presence for MITSOL, showcasing company information, services, software products, portfolio projects, research publications, and contact workflows.

## Features

* Responsive Design
* Company Profile
* Services Information
* Software Product Store
* Desktop License Delivery
* SaaS Product Links
* Research & Publications Management
* Portfolio Projects
* Contact Page
* Modern User Interface
* Mobile-Friendly Layout

## Technologies Used

* Python
* Django
* HTML5
* CSS3
* Bootstrap 5
* JavaScript

## Installation

```bash
git clone <repository-url>
cd mitsol
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Visit:

```text
https://www.mitsol.com.se
```

## Deployment

Configured for deployment on Render with Gunicorn.

Recommended deployment commands:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

Required environment variables:

```text
SECRET_KEY
DATABASE_URL
SITE_URL
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
DEFAULT_FROM_EMAIL
```

Common optional environment variables:

```text
DEBUG=False
MEDIA_ROOT=/var/data/media
SECURE_SSL_REDIRECT=True
```

For uploaded research PDFs, images, and product screenshots on Render, configure persistent storage and point `MEDIA_ROOT` to that mounted disk path. For larger production usage, use external media storage such as S3-compatible storage or Cloudinary.

## Useful Checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
```

## Author

Developed and maintained by Juma Shija.
# MITSOL Learning Assignments

Stage 3 adds assignment lessons to the online learning system. An assignment is linked to one `Assignment` lesson and supports written responses, file uploads, drafts, final submission, grading, and revision.

Assignment workflow:
- Students create or resume one draft for the current attempt.
- Saving a draft does not notify instructors and does not complete lesson progress.
- Final submission changes the draft to `Submitted` and makes it read-only for the student.
- Instructors can mark submitted work `Under Review`, grade it, or return it for revision.
- Returned submissions are preserved. If resubmission is allowed and attempts remain, the student creates a new draft as the next attempt.
- A compulsory assignment lesson is completed only when at least one submission is graded as passed.

Submission statuses:
- `Draft`
- `Submitted`
- `Under Review`
- `Graded`
- `Returned for Revision`
- `Withdrawn`

Late-submission policy:
- Due dates are checked server-side.
- Late submissions are rejected when `allow_late_submission` is disabled.
- When late submissions are allowed, `is_late` is calculated by the server during final submission.

File validation:
- The server validates extension, file size, empty files, filename length, dangerous executable extensions, and assignment-specific allowed extensions.
- Public `MEDIA_URL` serving is not true private storage. The learning UI uses an authorized download view for assignment files, but Render local media is not reliably persistent unless persistent disk or external object storage is configured.
