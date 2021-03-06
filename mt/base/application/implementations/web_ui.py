import atexit

from cached_property import cached_property
from selenium.common.exceptions import NoSuchElementException
from taretto.navigate import Navigate, NavigateStep, NavigateToSibling
from taretto.ui import Browser
from webdriver_kaifuku import BrowserManager
from wait_for import wait_for

from mt.base.application.implementations import MtImplementationContext, Implementation
from mt.base.application.views.common import BaseLoggedInView, LoginPage


class MtNavigateStep(NavigateStep):
    VIEW = None

    @cached_property
    def view(self):
        if self.VIEW is None:
            raise AttributeError(
                "{} does not have VIEW specified".format(type(self).__name__)
            )
        return self.create_view(self.VIEW, additional_context={"object": self.obj})

    @property
    def application(self):
        return self.obj.application

    def create_view(self, *args, **kwargs):
        return self.application.web_ui.create_view(*args, **kwargs)

    def am_i_here(self):
        try:
            return self.view.is_displayed
        except (AttributeError, NoSuchElementException):
            return False

    def check_for_badness(self, fn, _tries, nav_args, *args, **kwargs):
        go_kwargs = kwargs.copy()
        go_kwargs.update(nav_args)
        self.log_message(
            "Invoking {}, with {} and {}".format(fn.__name__, args, kwargs),
            level="debug",
        )

        try:
            return fn(*args, **kwargs)
        except Exception as e:
            self.log_message(e)
            self.go(_tries, *args, **go_kwargs)

    def go(self, _tries=3, *args, **kwargs):
        """Wrapper around :meth:`navmazing.NavigateStep.go` which returns
        instance of view after successful navigation flow.
        :return: view instance if class attribute ``VIEW`` is set or ``None``
            otherwise
        """
        super(MtNavigateStep, self).go(_tries=_tries, *args, **kwargs)
        view = self.view if self.VIEW is not None else None
        return view


class ViaWebUI(Implementation):
    """UI implementation using the normal ux"""

    navigator = Navigate()
    navigate_to = navigator.navigate
    register_destination_for = navigator.register
    register_method_for = MtImplementationContext.external_for
    name = "ViaWebUI"

    def __init__(self, owner):
        super(ViaWebUI, self).__init__(owner)
        self.browser_manager = BrowserManager.from_conf({
            "webdriver": "Remote",
            "webdriver_options": {
                "desired_capabilities": {
                    "acceptInsecureCerts": True,
                    "browserName": "firefox",
                    "marionette": "true"
                }
            }
        })

    def create_view(self, view_class, additional_context=None):
        """Method that is used to instantiate a Widgetastic View.
        Views may define ``LOCATION`` on them, that implies a :py:meth:`force_navigate` call with
        ``LOCATION`` as parameter.
        Args:
            view_class: A view class, subclass of ``widgetastic.widget.View``
            additional_context: Additional informations passed to the view (user name, VM name, ...)
                which is also passed to the :py:meth:`force_navigate` in case when navigation is
                requested.
        Returns:
            An instance of the ``view_class``
        """
        additional_context = additional_context or {}
        view = view_class(self.widgetastic_browser, additional_context=additional_context)
        return view

    def _reset_cache(self):
        try:
            del self.widgetastic_browser
        except AttributeError:
            pass

    @cached_property
    def widgetastic_browser(self):
        """This gives us a widgetastic browser."""
        selenium_browser = self.browser_manager.ensure_open()
        selenium_browser.get(self.application.address)
        self.browser_manager.add_cleanup(self._reset_cache)
        atexit.register(self.browser_manager.quit)
        return Browser(selenium_browser)

    def open_login_page(self):
        self.widgetastic_browser.url = self.application.address

    def do_login(self):
        view = self.navigate_to(self, "LoginScreen")
        view.fill({
            "username": self.application.username,
            "password": self.application.password,
        })
        view.login_button.click()


@ViaWebUI.register_destination_for(ViaWebUI)
class LoginScreen(MtNavigateStep):
    VIEW = LoginPage

    def step(self):
        self.obj.open_login_page()


@ViaWebUI.register_destination_for(ViaWebUI)
class LoggedIn(MtNavigateStep):
    VIEW = BaseLoggedInView
    prerequisite = NavigateToSibling("LoginScreen")

    def step(self):
        self.obj.do_login()
        wait_for(lambda: self.view.is_displayed)
