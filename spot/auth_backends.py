from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CaseInsensitiveUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(getattr(UserModel, 'USERNAME_FIELD', 'username'))
        if username is None or password is None:
            return None

        lookup = f"{getattr(UserModel, 'USERNAME_FIELD', 'username')}__iexact"
        try:
            user = UserModel._default_manager.get(**{lookup: username})
        except UserModel.DoesNotExist:
            return None
        except UserModel.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

