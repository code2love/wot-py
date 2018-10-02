#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Class that represents a WoT servient.
"""

import socket

import six
import tornado.concurrent
import tornado.gen
import tornado.ioloop
import tornado.web

from wotpy.protocols.enums import Protocols
from wotpy.protocols.ws.client import WebsocketClient
from wotpy.td.description import ThingDescription
from wotpy.td.enums import InteractionTypes
from wotpy.wot.exposed.group import ExposedThingGroup
from wotpy.wot.wot import WoT


# noinspection PyAbstractClass,PyMethodOverriding,PyAttributeOutsideInit
class TDHandler(tornado.web.RequestHandler):
    """Handler that returns the TD document of a given Thing."""

    def initialize(self, servient):
        self.servient = servient

    def get(self, thing_url_name):
        exp_thing = self.servient.exposed_thing_group.find_by_thing_id(thing_url_name)

        td_doc = ThingDescription.from_thing(exp_thing.thing).to_dict()
        td_doc.update({"base": self.servient.get_thing_base_url(exp_thing)})

        self.write(td_doc)


# noinspection PyAbstractClass,PyMethodOverriding,PyAttributeOutsideInit
class TDCatalogueHandler(tornado.web.RequestHandler):
    """Handler that returns the entire catalogue of Things contained in this servient.
    May return TDs in expanded format or URL pointers to the individual TDs."""

    def initialize(self, servient):
        self.servient = servient

    def get(self):
        response = {}

        for exp_thing in self.servient.exposed_thing_group.exposed_things:
            thing_id = exp_thing.thing.id

            if self.get_argument("expanded", False):
                val = ThingDescription.from_thing(exp_thing.thing).to_dict()
                val.update({"base": self.servient.get_thing_base_url(exp_thing)})
            else:
                val = "/{}".format(exp_thing.thing.url_name)

            response[thing_id] = val

        self.write(response)


class Servient(object):
    """An entity that is both a WoT client and server at the same time.
    WoT servers are Web servers that possess capabilities to access underlying
    IoT devices and expose a public interface named the WoT Interface that may
    be used by other clients.
    WoT clients are entities that are able to understand the WoT Interface to
    send requests and interact with IoT devices exposed by other WoT servients
    or servers using the capabilities of a Web client such as Web browser."""

    def __init__(self, hostname=None):
        self._hostname = hostname or socket.getfqdn()

        if not isinstance(self._hostname, six.string_types):
            raise ValueError("Invalid hostname")

        self._servers = {}
        self._clients = {}
        self._catalogue_port = None
        self._catalogue_server = None
        self._exposed_thing_group = ExposedThingGroup()

        self._build_default_clients()

    @staticmethod
    def _default_select_client(clients, td, name):
        """Default implementation of the function to select
        a Protocol Binding client for an Interaction."""

        protocol_preference_map = {
            InteractionTypes.PROPERTY: [],
            InteractionTypes.ACTION: [Protocols.WEBSOCKETS],
            InteractionTypes.EVENT: [Protocols.WEBSOCKETS]
        }

        supported_protocols = [
            client.protocol for client in clients
            if client.is_supported_interaction(td, name)
        ]

        intrct_names = {
            InteractionTypes.PROPERTY: six.iterkeys(td.properties),
            InteractionTypes.ACTION: six.iterkeys(td.actions),
            InteractionTypes.EVENT: six.iterkeys(td.events)
        }

        try:
            intrct_type = next(key for key, names in six.iteritems(intrct_names) if name in names)
        except StopIteration:
            raise ValueError("Unknown interaction: {}".format(name))

        protocol_prefs = protocol_preference_map[intrct_type]
        protocol_choices = set(protocol_prefs).intersection(set(supported_protocols))

        if not len(protocol_choices):
            return list(clients)[0]

        protocol = next(proto for proto in protocol_prefs if proto in protocol_choices)

        return next(client for client in clients if client.protocol == protocol)

    @property
    def hostname(self):
        """Hostname attached to this servient."""

        return self._hostname

    @property
    def exposed_thing_group(self):
        """Returns the ExposedThingGroup instance that
        contains the ExposedThings of this servient."""

        return self._exposed_thing_group

    @property
    def exposed_things(self):
        """Returns an iterator for the ExposedThings contained in this Sevient."""

        return self.exposed_thing_group.exposed_things

    @property
    def servers(self):
        """Returns the dict of Protocol Binding servers attached to this servient."""

        return self._servers

    @property
    def clients(self):
        """Returns the dict of Protocol Binding clients attached to this servient."""

        return self._clients

    def _build_default_clients(self):
        """Builds the default Protocol Binding clients."""

        self._clients.update({
            Protocols.WEBSOCKETS: WebsocketClient()
        })

    def _build_td_catalogue_app(self):
        """Returns a Tornado app that provides one endpoint to retrieve the
        entire catalogue of thing descriptions contained in this servient."""

        return tornado.web.Application([
            (r"/", TDCatalogueHandler, dict(servient=self)),
            (r"/(?P<thing_url_name>[^\/]+)", TDHandler, dict(servient=self))
        ])

    def _start_catalogue(self):
        """Starts the TD catalogue server if enabled."""

        if self._catalogue_server or not self._catalogue_port:
            return

        catalogue_app = self._build_td_catalogue_app()
        self._catalogue_server = catalogue_app.listen(self._catalogue_port)

    def _stop_catalogue(self):
        """Stops the TD catalogue server if running."""

        if not self._catalogue_server:
            return

        self._catalogue_server.stop()
        self._catalogue_server = None

    def _clean_protocol_forms(self, exposed_thing, protocol):
        """Removes all interaction forms linked to this
        server protocol for the given ExposedThing."""

        assert self._exposed_thing_group.contains(exposed_thing)
        assert protocol in self._servers

        for interaction in exposed_thing.thing.interactions:
            forms_to_remove = [
                form for form in interaction.forms
                if form.protocol == protocol
            ]

            for form in forms_to_remove:
                interaction.remove_form(form)

    def _server_has_exposed_thing(self, server, exposed_thing):
        """Returns True if the given server contains the ExposedThing."""

        assert server in self._servers.values()
        assert self._exposed_thing_group.contains(exposed_thing)

        return server.exposed_thing_group.contains(exposed_thing)

    def _add_interaction_forms(self, server, exposed_thing):
        """Builds and adds to the ExposedThing the Links related to the given server."""

        assert server in self._servers.values()
        assert self._exposed_thing_group.contains(exposed_thing)

        for interaction in exposed_thing.thing.interactions:
            forms = server.build_forms(hostname=self._hostname, interaction=interaction)

            for form in forms:
                interaction.add_form(form)

    def _regenerate_server_forms(self, server):
        """Cleans and regenerates Forms for the given server in all ExposedThings."""

        assert server in self._servers.values()

        for exp_thing in self._exposed_thing_group.exposed_things:
            self._clean_protocol_forms(exp_thing, server.protocol)
            if self._server_has_exposed_thing(server, exp_thing):
                self._add_interaction_forms(server, exp_thing)

    def get_thing_base_url(self, exposed_thing):
        """Return the base URL for the given ExposedThing
        for one of the currently active servers."""

        if not self.exposed_thing_group.contains(exposed_thing):
            raise ValueError("Unknown ExposedThing")

        if not len(self.servers):
            return None

        protocol = sorted(list(self.servers.keys()))[0]
        server = self.servers[protocol]

        return server.build_base_url(hostname=self.hostname, thing=exposed_thing.thing)

    def select_client(self, td, name):
        """Returns the Protocol Binding client instance to
        communicate with the given Interaction."""

        return Servient._default_select_client(self.clients.values(), td, name)

    def add_client(self, client):
        """Adds a new Protocol Binding client to this servient."""

        self._clients[client.protocol] = client

    def remove_client(self, protocol):
        """Removes the Protocol Binding client with the given protocol from this servient."""

        self._clients.pop(protocol, None)

    def add_server(self, server):
        """Adds a new Protocol Binding server to this servient."""

        self._servers[server.protocol] = server

    def remove_server(self, protocol):
        """Removes the Protocol Binding server with the given protocol from this servient."""

        self._servers.pop(protocol, None)

    def refresh_forms(self):
        """Cleans and regenerates Forms for all the
        ExposedThings and servers contained in this servient."""

        for server in self._servers.values():
            self._regenerate_server_forms(server)

    def enable_exposed_thing(self, thing_id):
        """Enables the ExposedThing with the given ID.
        This is, the servers will listen for requests for this thing."""

        exposed_thing = self.get_exposed_thing(thing_id)

        for server in self._servers.values():
            server.add_exposed_thing(exposed_thing)
            self._regenerate_server_forms(server)

    def disable_exposed_thing(self, thing_id):
        """Disables the ExposedThing with the given ID.
        This is, the servers will not listen for requests for this thing."""

        exposed_thing = self.get_exposed_thing(thing_id)

        for server in self._servers.values():
            server.remove_exposed_thing(exposed_thing.thing.id)
            self._regenerate_server_forms(server)

    def add_exposed_thing(self, exposed_thing):
        """Adds a ExposedThing to this servient.
        ExposedThings are disabled by default."""

        self._exposed_thing_group.add(exposed_thing)

    def remove_exposed_thing(self, thing_id):
        """Adds a ExposedThing to this servient.
        ExposedThings are disabled by default."""

        self.disable_exposed_thing(thing_id)
        self._exposed_thing_group.remove(thing_id)

    def get_exposed_thing(self, thing_id):
        """Finds and returns an ExposedThing contained in this servient by Thing ID.
        Raises ValueError if the ExposedThing is not present."""

        exp_thing = self._exposed_thing_group.find_by_thing_id(thing_id)

        if exp_thing is None:
            raise ValueError("Unknown Exposed Thing: {}".format(thing_id))

        return exp_thing

    def enable_td_catalogue(self, port):
        """Enables the servient TD catalogue in the given port."""

        self._catalogue_port = port

    def disable_td_catalogue(self):
        """Disables the servient TD catalogue."""

        self._catalogue_port = None

    @tornado.gen.coroutine
    def start(self):
        """Starts the servers and returns an instance of the WoT object."""

        yield [server.start() for server in six.itervalues(self._servers)]
        self._start_catalogue()

        raise tornado.gen.Return(WoT(servient=self))

    @tornado.gen.coroutine
    def shutdown(self):
        """Stops the server configured under this servient."""

        yield [server.stop() for server in six.itervalues(self._servers)]
        self._stop_catalogue()
