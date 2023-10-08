import asyncio
import json
from asyncio import AbstractEventLoop
from http import HTTPStatus
from typing import Callable, Optional, Set

import websockets
from loging.logger import _LOGGER
from mediator.components.base_component import BaseComponent
from mediator.components.cover.cover_component import Cover
from mediator.components.light.light_component import Light
from mediator.components.switch.switch_component import Switch
from pydantic import ValidationError
from server.client.client_authenticator import ClientAuthenticator
from server.client.sense_client import SenseClient
from server.model.cover import *
from server.model.error import ErrorCode, ErrorResponse
from server.model.light import *
from server.model.server_credentials import ServerCredentials
from server.model.switch import *
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosedError
from websockets.http11 import Request, Response
from websockets.server import ServerConnection


class PanelSenseServer:
    client_authenticator: ClientAuthenticator

    SENSE_SERVER_PORT = 8652

    websocket_server: WebSocketClientProtocol

    connected_clients: Set[SenseClient] = set()
    client_connected_callbacks: Set[Callable[[SenseClient], None]] = set()
    client_diconnected_callbacks: Set[Callable[[SenseClient], None]] = set()
    callback: Callable[[BaseComponent], None]

    def __init__(self, loop: AbstractEventLoop, server_credentials: ServerCredentials):
        loop.create_task(self.start_sense_server())
        self.client_authenticator = ClientAuthenticator(server_credentials)

    async def message_handler(self, websocket: WebSocketClientProtocol):
        auth_message = await websocket.recv()

        sense_client = await self.client_authenticator.authenticate(
            auth_message, websocket
        )

        if not sense_client:
            _LOGGER.info(f"Client not authenticated! Close connection.")
            await websocket.close()
            return

        self.add_client(sense_client)

        try:
            async for message in websocket:
                self.handle_message(websocket, message)
                print(f"Reveived message:\n {message}")
        except websockets.exceptions.ConnectionClosedError as e:
            _LOGGER.error(f"Client disconnected! {e}")
        finally:
            _LOGGER.info(f"Client disconnected! {sense_client.details.name}")
            self.remove_client(sense_client)

    def add_client(self, client: SenseClient):
        self.connected_clients.add(client)
        for callback in self.client_connected_callbacks:
            callback(client)

    def remove_client(self, client: SenseClient):
        self.connected_clients.remove(client)
        for callback in self.client_diconnected_callbacks:
            callback(client)

    async def start_sense_server(self):
        print(f"Server starting at ws://localhost:{self.SENSE_SERVER_PORT}")
        self.websocket_server = await websockets.serve(
            self.message_handler, "0.0.0.0", self.SENSE_SERVER_PORT
        )
        await self.websocket_server.serve_forever()

    async def send_message_async(self, message: BaseComponent):
        _LOGGER.info(f"Connected clients: {len(self.connected_clients)}")
        for client in self.connected_clients:
            _LOGGER.info(f"SERVER ->: {message.get_message_for_client()}\n")
            await client.send(
                message.get_message_for_client().model_dump_json(exclude_none=True)
            )

    async def send_error_async(
        self, client: WebSocketClientProtocol, error: ErrorResponse
    ):
        await client.send(error.model_dump_json(exclude_none=True))

    def send_message(self, component: BaseComponent):
        asyncio.create_task(self.send_message_async(component))

    def send_error(
        self, client: WebSocketClientProtocol, error_code: ErrorCode, error_message: str
    ):
        asyncio.create_task(
            self.send_error_async(
                client, ErrorResponse(error_code=error_code, message=error_message)
            )
        )

    def handle_message(self, client: WebSocketClientProtocol, message):
        try:
            client_message = ClientIncomingMessage.model_validate_json(message)
            self.process_client_message_ha_action(client, client_message.type, message)
            _LOGGER.debug(f"CLIENT -> handle_message type: {client_message}")
        except ValidationError as e:
            print(f"SERVER ERROR -> {message}")
            self.send_error(client, ErrorCode.INVALID_DATA, "Invalid data")
            return

    def process_client_message_ha_action(
        self, client: WebSocketClientProtocol, type: MessageType, message
    ):
        if type == MessageType.HA_ACTION_LIGHT:
            light_incoming_message = LightIncomingMessage.model_validate_json(message)
            light = Light(None, light_incoming_message=light_incoming_message)
            self.callback(light)
        elif type == MessageType.HA_ACTION_COVER:
            cover_incoming_message = CoverIncomingMessage.model_validate_json(message)
            cover = Cover(None, cover_message=cover_incoming_message)
            self.callback(cover)
        elif type == MessageType.HA_ACTION_SWITCH:
            switch_incoming_message = SwitchIncomingMessage.model_validate_json(message)
            switch = Switch(switch_message=switch_incoming_message)
            self.callback(switch)

        _LOGGER.debug(f"CLIENT -> process_client_message_ha_action: {type}")

    def set_message_callback(self, callback: Callable[[BaseComponent], None]):
        self.callback = callback
