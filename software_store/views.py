import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .forms import SoftwareOrderForm
from .models import (
    LicenseActivation,
    SoftwareDownloadLog,
    SoftwareLicense,
    SoftwareOrder,
    SoftwareProduct,
)


def product_list(request):

    products = SoftwareProduct.objects.filter(
        is_active=True
    )

    return render(
        request,
        'software_store/product_list.html',
        {
            'products': products,
        }
    )


def order_product(request, product_slug):

    product = get_object_or_404(
        SoftwareProduct,
        slug=product_slug,
        is_active=True
    )

    if request.method == 'POST':

        form = SoftwareOrderForm(
            request.POST
        )

        if form.is_valid():

            order = form.save(
                commit=False
            )
            order.product = product
            order.amount = product.price
            order.payment_status = SoftwareOrder.PaymentStatus.PENDING
            order.save()

            return render(
                request,
                'software_store/order_received.html',
                {
                    'product': product,
                    'order': order,
                }
            )

    else:

        form = SoftwareOrderForm()

    return render(
        request,
        'software_store/order_form.html',
        {
            'form': form,
            'product': product,
        }
    )


def download_software(request, license_key):

    license_obj = SoftwareLicense.objects.select_related(
        'order',
        'product'
    ).filter(
        license_key=license_key
    ).first()

    error_message = get_license_error(
        license_obj
    )

    if error_message:

        return render(
            request,
            'software_store/download_error.html',
            {
                'error_message': error_message,
            },
            status=403
        )

    SoftwareDownloadLog.objects.create(
        order=license_obj.order,
        product=license_obj.product,
        customer_email=license_obj.customer_email,
        ip_address=get_client_ip(request)
    )

    return render(
        request,
        'software_store/download.html',
        {
            'license': license_obj,
            'product': license_obj.product,
        }
    )


@csrf_exempt
@require_POST
def activate_license(request):

    data, error = parse_json_body(request)

    if error:

        return invalid_response(error)

    license_key = data.get(
        'license_key'
    )
    device_id = data.get(
        'device_id'
    )

    if not license_key or not device_id:

        return invalid_response('license_key and device_id are required')

    license_obj = get_license_by_key(
        license_key
    )

    error_message = get_license_error(
        license_obj
    )

    if error_message:

        return invalid_response(error_message)

    activation_exists = license_obj.activations.filter(
        device_id=device_id
    ).exists()

    if not activation_exists:

        activated_devices = license_obj.activations.count()

        if activated_devices >= license_obj.allowed_devices:

            return invalid_response('Allowed device limit has been reached')

        LicenseActivation.objects.create(
            license=license_obj,
            device_id=device_id
        )

    return JsonResponse(
        {
            'valid': True,
            'message': 'License activated successfully',
            'customer_name': license_obj.customer_name,
            'product_name': license_obj.product.name,
            'expiry_date': license_obj.expiry_date.isoformat(),
        }
    )


@csrf_exempt
@require_POST
def verify_license(request):

    data, error = parse_json_body(request)

    if error:

        return invalid_response(error)

    license_key = data.get(
        'license_key'
    )
    device_id = data.get(
        'device_id'
    )

    if not license_key or not device_id:

        return invalid_response('license_key and device_id are required')

    license_obj = get_license_by_key(
        license_key
    )

    error_message = get_license_error(
        license_obj
    )

    if error_message:

        return invalid_response(error_message)

    if not license_obj.activations.filter(
        device_id=device_id
    ).exists():

        return invalid_response('This device is not activated for this license')

    return JsonResponse(
        {
            'valid': True,
            'message': 'License verified successfully',
            'customer_name': license_obj.customer_name,
            'product_name': license_obj.product.name,
            'expiry_date': license_obj.expiry_date.isoformat(),
        }
    )


@require_GET
def latest_software(request, product_slug):

    product = get_object_or_404(
        SoftwareProduct,
        slug=product_slug,
        is_active=True
    )

    response_data = {
        'product': product.name,
        'latest_version': product.version,
        'release_notes': product.release_notes,
        'mandatory': False,
    }

    license_key = request.GET.get(
        'license_key'
    )

    if license_key:

        license_obj = get_license_by_key(
            license_key
        )

        if (
            license_obj
            and license_obj.product_id == product.id
            and not get_license_error(license_obj)
        ):

            response_data['download_url'] = product.proton_drive_link

    return JsonResponse(
        response_data
    )


def parse_json_body(request):

    try:

        return json.loads(
            request.body.decode('utf-8')
        ), None

    except json.JSONDecodeError:

        return {}, 'Invalid JSON body'


def get_license_by_key(license_key):

    return SoftwareLicense.objects.select_related(
        'order',
        'product'
    ).filter(
        license_key=license_key
    ).first()


def get_license_error(license_obj):

    if not license_obj:

        return 'License was not found'

    if not license_obj.is_active:

        return 'License is not active'

    if license_obj.order.payment_status != SoftwareOrder.PaymentStatus.PAID:

        return 'Order payment has not been approved'

    if license_obj.expiry_date < timezone.localdate():

        return 'License has expired'

    if not license_obj.product.is_active:

        return 'Software product is not active'

    return ''


def invalid_response(message):

    return JsonResponse(
        {
            'valid': False,
            'message': message,
        },
        status=400
    )


def get_client_ip(request):

    forwarded_for = request.META.get(
        'HTTP_X_FORWARDED_FOR'
    )

    if forwarded_for:

        return forwarded_for.split(',')[0].strip()

    return request.META.get(
        'REMOTE_ADDR'
    )
