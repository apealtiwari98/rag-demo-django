import factory

from apps.users.models import BaseUser


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BaseUser

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "password123")
