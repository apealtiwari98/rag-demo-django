from rest_framework import serializers


def create_serializer_class(name: str, fields: dict) -> type[serializers.Serializer]:
    return type(name, (serializers.Serializer,), fields)


def inline_serializer(*, name: str, fields: dict, data=None, **kwargs):
    """
    Build a nested serializer inline, inside an API's Input/OutputSerializer.
    `name` must be unique across the project so drf-spectacular emits a
    distinct schema component for it.
    """
    serializer_class = create_serializer_class(name=name, fields=fields)

    if data is not None:
        return serializer_class(data=data, **kwargs)

    return serializer_class(**kwargs)
