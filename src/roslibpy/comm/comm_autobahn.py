from __future__ import print_function

import json
import logging

from autobahn.twisted.websocket import WebSocketClientFactory, WebSocketClientProtocol
from twisted.internet.protocol import ReconnectingClientFactory

from . import RosBridgeProtocol, RosBridgeException
from .. import Message, ServiceResponse
from ..event_emitter import EventEmitterMixin

LOGGER = logging.getLogger('roslibpy')

class AutobahnRosBridgeProtocol(RosBridgeProtocol, WebSocketClientProtocol):
    def __init__(self, *args, **kwargs):
        super(AutobahnRosBridgeProtocol, self).__init__(*args, **kwargs)

    def onConnect(self, response):
        LOGGER.debug('Server connected: %s', response.peer)

    def onOpen(self):
        LOGGER.info('Connection to ROS MASTER ready.')
        self.factory.ready(self)

    def onMessage(self, payload, isBinary):
        if isBinary:
            raise NotImplementedError('Add support for binary messages')

        message = Message(json.loads(payload.decode('utf8')))
        handler = self._message_handlers.get(message['op'], None)
        if not handler:
            raise RosBridgeException(
                'No handler registered for operation "%s"' % message['op'])

        handler(message)

    def onClose(self, wasClean, code, reason):
        LOGGER.info('WebSocket connection closed: %s', reason)

    def send_message(self, payload):
        return self.sendMessage(payload, isBinary=False, fragmentSize=None, sync=False, doNotCompress=False)

    def send_close(self):
        self.sendClose()

class AutobahnRosBridgeClientFactory(EventEmitterMixin, ReconnectingClientFactory, WebSocketClientFactory):
    """Factory to construct instance of the ROS Bridge protocol."""
    protocol = AutobahnRosBridgeProtocol

    def __init__(self, *args, **kwargs):
        super(AutobahnRosBridgeClientFactory, self).__init__(*args, **kwargs)
        self._proto = None
        self.setProtocolOptions(closeHandshakeTimeout=5)

    def on_ready(self, callback):
        if self._proto:
            callback(self._proto)
        else:
            self.once('ready', callback)

    def ready(self, proto):
        self._proto = proto
        self.emit('ready', proto)

    def startedConnecting(self, connector):
        LOGGER.debug('Started to connect...')

    def clientConnectionLost(self, connector, reason):
        LOGGER.debug('Lost connection. Reason: %s', reason)
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
        self._proto = None

    def clientConnectionFailed(self, connector, reason):
        LOGGER.debug('Connection failed. Reason: %s', reason)
        ReconnectingClientFactory.clientConnectionFailed(
            self, connector, reason)
        self._proto = None
