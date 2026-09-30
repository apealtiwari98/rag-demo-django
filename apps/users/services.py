from apps.users.models import BaseUser


def user_create(
    *,
    email: str,
    password: str | None = None,
    is_active: bool = True,
    is_admin: bool = False,
) -> BaseUser:
    user = BaseUser(email=email.lower(), is_active=is_active, is_admin=is_admin)

    if password is not None:
        user.set_password(password)
    else:
        user.set_unusable_password()

    user.full_clean()
    user.save()

    return user
