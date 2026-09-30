from django.contrib.auth.models import BaseUserManager as DjangoBaseUserManager


class BaseUserManager(DjangoBaseUserManager):
    """
    Only `createsuperuser` and the test client should go through here; app
    code creates users via `apps.users.services.user_create`.
    """

    def create_user(self, email: str, password: str | None = None, is_active: bool = True, is_admin: bool = False):
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(email=self.normalize_email(email.lower()), is_active=is_active, is_admin=is_admin)

        if password is not None:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.full_clean()
        user.save(using=self._db)

        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        user = self.create_user(email=email, password=password, is_admin=True)
        user.is_superuser = True
        user.save(using=self._db)

        return user
