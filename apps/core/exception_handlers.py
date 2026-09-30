from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler

from apps.core.exceptions import ApplicationError


def hacksoft_proposed_exception_handler(exc, ctx):
    """
    Normalizes every error to:

        {"message": "...", "extra": {...}}

    Validation errors carry the field errors under extra["fields"].
    Django's ValidationError (raised by full_clean() in services) is mapped
    to DRF's so it renders exactly like serializer validation errors.
    """
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    if isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()

    response = exception_handler(exc, ctx)

    # DRF doesn't know about our domain exception.
    if response is None:
        if isinstance(exc, ApplicationError):
            data = {"message": exc.message, "extra": exc.extra}
            return Response(data, status=400)

        # Missing provider package / API key / wrong EMBEDDING_DIM: a server
        # misconfiguration, but one worth surfacing with its fix-it message.
        if isinstance(exc, ImproperlyConfigured):
            return Response({"message": str(exc), "extra": {}}, status=503)

        return response

    if isinstance(exc.detail, (list, dict)):
        response.data = {"detail": response.data}

    if isinstance(exc, exceptions.ValidationError):
        response.data["message"] = "Validation error"
        response.data["extra"] = {"fields": response.data["detail"]}
    else:
        response.data["message"] = response.data["detail"]
        response.data["extra"] = {}

    del response.data["detail"]

    return response
