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
DJANGO_ADMIN_URL=admin

# Optional production media storage using Cloudinary.
# Keep CLOUDINARY_ENABLED=False locally if you want uploads saved to MEDIA_ROOT.
CLOUDINARY_ENABLED=True
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
SECURE_SSL_REDIRECT=True
```

For uploaded research PDFs, images, course files, certificates, and product screenshots on Render, use persistent storage through `MEDIA_ROOT` or enable Cloudinary with the environment variables above. When `CLOUDINARY_ENABLED=True`, uploaded media is saved to Cloudinary and Django does not serve `/media/` from local disk.

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
- When Cloudinary is disabled, public `MEDIA_URL` serving is not true private storage. The learning UI uses authorized download views for protected files, but Render local media is not reliably persistent unless persistent disk or external object storage is configured.

# MITSOL Learning Manual Payments

Stage 4 adds an independent manual payment workflow for paid learning courses. It does not use the software-store order or payment models.

Payment workflow:
- Free courses still enrol students immediately and use `Not Required` payment status.
- Paid courses create a pending inactive enrolment and send the student to the course payment page.
- Students submit a payment method, transaction reference, optional notes, and proof of payment where required.
- Administrators review payments from the learning payment queue, then confirm, reject, or refund.
- Confirmed payments activate the enrolment and unlock lessons, quizzes, and assignments.
- Rejected payments keep the enrolment inactive and allow the student to submit a corrected payment.
- Refunded payments suspend the enrolment and remove access.

Admin setup:
- Create one active `Learning payment settings` record in Django admin.
- Configure currency, mobile money details, bank details, support contact, and proof requirements.
- Manage submitted records in Django admin under `Payments`, or from `/learn/admin/payments/`.

Upload policy:
- Payment proof uploads allow PDF and common image formats only: `pdf`, `jpg`, `jpeg`, `png`, `webp`.
- The server rejects dangerous extensions, empty files, very long filenames, and files larger than 5 MB.
- Configure persistent media storage in production so uploaded proofs remain available after deployment restarts.

# MITSOL Learning Course Reviews

Stage 5 adds moderated course reviews and ratings.

Review eligibility:
- A learner must be enrolled in the course.
- The enrolment must be `Active` or `Completed`.
- Paid courses require confirmed payment status.
- A learner must complete at least 25% of the course, unless the course is already completed.
- Each learner can submit one review per course.

Review statuses:
- `Pending`: submitted or edited and awaiting moderation.
- `Approved`: publicly visible on the course detail page.
- `Rejected`: preserved privately for the learner to edit and resubmit.
- `Hidden`: previously approved but removed from public display by moderation.

Moderation workflow:
- New reviews are submitted as `Pending`.
- Editing an approved, rejected, or hidden review sends it back to `Pending`.
- Authorized moderators can approve, reject, or hide reviews from the learning moderation queue.
- Rejection and hiding require a reason.
- Instructors can view review status for their own courses but cannot moderate reviews unless separately authorized.

Public display policy:
- Only approved reviews are displayed publicly.
- Public reviews show a safe learner name: full name when available, otherwise `Verified Learner`.
- Email addresses, usernames, enrolment details, payment details, and moderation notes are not displayed publicly.
- The `Verified Learner` badge requires a matching valid enrolment and confirmed access.

Rating policy:
- Course rating summaries use approved reviews only.
- Average rating is calculated dynamically and rounded to one decimal place.
- Rating distribution counts 1-star through 5-star reviews and safely handles courses with no reviews.

Notifications:
- Learners are notified when reviews are submitted, approved, rejected, hidden, or resubmitted after editing.
- Review moderators are notified when a new or updated review awaits moderation.
