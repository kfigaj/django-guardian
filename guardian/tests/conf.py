from __future__ import unicode_literals
import os
from guardian.utils import abspath
from django.conf import settings
from django.conf import UserSettingsHolder
from django.utils.functional import wraps


THIS = abspath(os.path.dirname(__file__))
TEST_TEMPLATES_DIR = abspath(THIS, 'templates')


TEST_SETTINGS = dict(
    TEMPLATE_DIRS=[TEST_TEMPLATES_DIR],
)

class TestDataMixin(object):
    def setUp(self):
        super(TestDataMixin, self).setUp()
        from django.contrib.auth.models import Group
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
        except ImportError:
            from django.contrib.auth.models import User
        Group.objects.create(pk=1, name='admins')
        jack_group = Group.objects.create(pk=2, name='jackGroup')
        User.objects.get_or_create(pk=settings.ANONYMOUS_USER_ID)
        jack = User.objects.create(pk=1, username='jack', is_active=True,
            is_superuser=False, is_staff=False)
        jack.groups.add(jack_group)


class override_settings(object):
    """
    Acts as either a decorator, or a context manager. If it's a decorator it
    takes a function and returns a wrapped function. If it's a contextmanager
    it's used with the ``with`` statement. In either event entering/exiting
    are called before and after, respectively, the function/block is executed.
    """
    def __init__(self, **kwargs):
        self.options = kwargs
        self.wrapped = settings._wrapped

    def __enter__(self):
        self.enable()

    def __exit__(self, exc_type, exc_value, traceback):
        self.disable()

    def __call__(self, test_func):
        from django.test import TransactionTestCase
        if isinstance(test_func, type) and issubclass(test_func, TransactionTestCase):
            original_pre_setup = test_func._pre_setup
            original_post_teardown = test_func._post_teardown
            def _pre_setup(innerself):
                self.enable()
                original_pre_setup(innerself)
            def _post_teardown(innerself):
                original_post_teardown(innerself)
                self.disable()
            test_func._pre_setup = _pre_setup
            test_func._post_teardown = _post_teardown
            return test_func
        else:
            @wraps(test_func)
            def inner(*args, **kwargs):
                with self:
                    return test_func(*args, **kwargs)
        return inner

    def enable(self):
        override = UserSettingsHolder(settings._wrapped)
        for key, new_value in self.options.items():
            setattr(override, key, new_value)
        settings._wrapped = override

    def disable(self):
        settings._wrapped = self.wrapped

