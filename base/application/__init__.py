import importscan
from pkg_resources import iter_entry_points

from mt.base.application.implementations.web_ui import ViaWebUI
from mt.base.application.implementations.rest_api import ViaRESTAPI
from mt.base.application.implementations import MtImplementationContext
from mt.base.entities import EntityCollections


class Application(object):
    def __init__(self, hostname=None, path="", scheme="https", username=None, password=None):
        self.application = self
        self.hostname = hostname
        self.path = path
        self.scheme = scheme
        self.web_ui = ViaWebUI(owner=self)
        self.rest_api = ViaRESTAPI(owner=self)
        self.context = MtImplementationContext.from_instances([self.web_ui, self.rest_api])
        self.collections = EntityCollections.for_application(self)
        self.username = username
        self.password = password

    @property
    def address(self):
        return "{}://{}/{}".format(self.scheme, self.hostname, self.path)

    @property
    def destinations(self):
        """Returns a dict of all valid destinations for a particular object"""
        return {
            impl.name: impl.navigator.list_destinations(self)
            for impl in self.application.context.implementations.values()
            if impl.navigator
        }


def load_application_collections():
    return {
        ep.name: ep.resolve() for ep in iter_entry_points("mt.application_collections")
    }


from mt import base  # noqa

importscan.scan(base)
