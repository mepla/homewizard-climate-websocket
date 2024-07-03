import inspect
import json
import logging
import threading
from collections.abc import Callable
from dataclasses import replace
from enum import Enum
from ssl import SSLEOFError

import websocket
from websocket._exceptions import WebSocketConnectionClosedException

from homewizard_climate_websocket.api.api import HomeWizardClimateApi
from homewizard_climate_websocket.const import API_WS_PATH
from homewizard_climate_websocket.model.climate_device import (
    HomeWizardClimateDevice,
)
from homewizard_climate_websocket.model.climate_device_state import (
    HomeWizardClimateDeviceState,
    default_state,
    diff_states,
)
from homewizard_climate_websocket.ws.hw_websocket_payloads import (
    HomeWizardClimateWSPayloads,
)


class SocketStatus(Enum):
    PRE_INITIALIZATION = 0
    INITIALIZING = 1
    INITIALIZED = 2
    NOT_INITIALIZED = 3


class HomeWizardClimateWebSocket:
    def __init__(
        self,
        api: HomeWizardClimateApi,
        device: HomeWizardClimateDevice,
        on_initialized: Callable[[HomeWizardClimateDevice], None] = None,
        on_state_change: Callable[[HomeWizardClimateDeviceState, str], None] = None,
    ):
        self._socket_status: SocketStatus = SocketStatus.PRE_INITIALIZATION
        self._last_state: HomeWizardClimateDeviceState = default_state()
        self._api = api
        self._device = device
        self._payloads = HomeWizardClimateWSPayloads(api, device)
        self._on_initialized = on_initialized
        self._on_state_change = on_state_change
        self._disconnect_requested = False
        self._LOGGER = logging.getLogger(f"{__name__}.{self._device.identifier}")

        self._socket_app = websocket.WebSocketApp(
            API_WS_PATH,
            on_message=self._on_message,
            on_open=self._on_open,
            on_ping=self._on_ping,
            on_close=self._on_close,
        )

    @property
    def initialized(self) -> SocketStatus:
        return self._socket_status

    @property
    def device(self) -> HomeWizardClimateDevice:
        return self._device

    @property
    def last_state(self) -> HomeWizardClimateDeviceState:
        return self._last_state

    def set_on_state_change(
        self, on_state_change: Callable[[HomeWizardClimateDeviceState, str], None]
    ) -> None:
        self._on_state_change = on_state_change

    def is_device_online(self) -> bool:
        return self.initialized and self._last_state != default_state()

    def connect(self) -> None:
        if self._socket_status not in [
            SocketStatus.INITIALIZED,
            SocketStatus.INITIALIZING,
        ]:
            self._socket_status = SocketStatus.INITIALIZING
            self._LOGGER.info(f"Connecting to websocket ({API_WS_PATH})")
            self._socket_app.run_forever()
        else:
            self._LOGGER.info(
                f"Can not attempt socket connection because of current "
                f"socket status: {self._socket_status}"
            )

    def connect_in_thread(self) -> None:
        thread = threading.Thread(target=self.connect)
        thread.daemon = True
        thread.start()

    def disconnect(self) -> None:
        self._disconnect_requested = True
        self._socket_app.close()

    def _send_message(self, payload: str) -> None:
        calling_method = inspect.stack()[1].function
        self._LOGGER.debug(
            f"Sending message for command {calling_method}: "
            f"{self._safe_payload_log(payload)}"
        )
        try:
            self._socket_app.send(payload)
        except (WebSocketConnectionClosedException, SSLEOFError):
            self._auto_reconnect_if_needed()

    def turn_on(self) -> None:
        self._send_message(self._payloads.turn_on())

    def turn_off(self) -> None:
        self._send_message(self._payloads.turn_off())

    def set_fan_speed(self, speed: int) -> None:
        self._send_message(self._payloads.set_fan_speed(speed))

    def set_target_temperature(self, temp: int) -> None:
        self._send_message(self._payloads.set_target_temperature(temp))

    def turn_on_heater(self) -> None:
        self._send_message(self._payloads.set_heater())

    def turn_on_cooler(self) -> None:
        self._send_message(self._payloads.set_cooler())

    def turn_on_oscillation(self) -> None:
        self._send_message(self._payloads.turn_on_oscillate())

    def turn_off_oscillation(self) -> None:
        self._send_message(self._payloads.turn_off_oscillate())

    def _hello(self):
        self._send_message(self._payloads.hello())

    def _on_open(self, ws: websocket.WebSocket) -> None:
        self._LOGGER.debug("Websocket opened")
        self._hello()

    def _on_ping(self, ws: websocket.WebSocket) -> None:
        self._socket_app.sock.pong()

    def _on_message(self, ws: websocket.WebSocket, message: str) -> None:
        self._LOGGER.debug(f"Received message: {message}")

        message_dict: dict = json.loads(message)
        message_device = message_dict.get("device")

        if message_device and message_device != self._device.identifier:
            self._LOGGER.error(
                f"Got a message for a different device. Expected: "
                f'{self._device.identifier}, got: {message_dict.get("device")}'
            )

            return

        message_type = message_dict.get("type", "")
        if message_type == "response":
            self._handle_response_update(message_dict)
        elif message_type == "json_patch":
            self._handle_state_update(message_dict)
        elif message_type == self._device.type.value:
            self._handle_device_update(message_dict)
        else:
            self._LOGGER.error(f"Got unknown message of type: {message_type}")

    def _on_close(self, ws: websocket.WebSocket, close_code: int, close_message: str):
        self._LOGGER.debug(
            f"Socket closed. Code: {close_code}, message: {close_message}"
        )
        self._auto_reconnect_if_needed()

    def _handle_response_update(self, received_message: dict) -> None:
        message_id = received_message.get("message_id")
        status_code = received_message.get("status")
        self._LOGGER.debug(f"Received response update: {received_message}")

        if message_id == "hello" and status_code == 200:
            self._LOGGER.debug("Auto responding to `hello` response with `subscribe`")
            self._send_message(self._payloads.subscribe())

        elif message_id == "subscribe" and status_code == 200:
            # We need to wait for a device update message right after subscribe,
            # otherwise the device is deemed to be offline,
            # so we shouldn't set initiated=True.
            pass

        elif status_code == 401:
            self._api.login()

    def _handle_device_update(self, received_message: dict) -> None:
        if self._socket_status == SocketStatus.INITIALIZING:
            self._socket_status = SocketStatus.INITIALIZED
            self._LOGGER.debug("Socket initialized.")
            if self._on_initialized:
                self._on_initialized(self._device)

        self._LOGGER.debug(f"Received full device update: {received_message}")
        self._update_last_state(
            HomeWizardClimateDeviceState.from_dict(received_message.get("state"))
        )

    def _handle_state_update(self, received_message: dict) -> None:
        if received_message.get("patch"):
            kw = {}
            for patch in received_message.get("patch"):
                if patch.get("op", "") == "replace":
                    path_split = patch.get("path", "").strip("/").split("/")
                    if len(path_split) == 2 and path_split[0] == "state":
                        kw.update({path_split[1]: patch.get("value")})

            if kw:
                self._update_last_state(replace(self._last_state, **kw))

    def _update_last_state(self, new_last_state) -> None:
        diff = diff_states(self._last_state, new_last_state)
        self._LOGGER.debug(f"Received state update, diff: {diff}")
        self._last_state = new_last_state
        if self._on_state_change:
            self._on_state_change(self._last_state, diff)

    def _auto_reconnect_if_needed(self, command: str = None):
        self._socket_status = SocketStatus.NOT_INITIALIZED
        if not self._disconnect_requested:
            self._LOGGER.debug(
                f"Automatically reconnecting on unwanted closed socket. {command}"
            )
            self.connect_in_thread()
        else:
            self._LOGGER.debug(
                "Disconnect was explicitly requested, not attempting to reconnect"
            )

    def _safe_payload_log(self, payload: str):
        if '"token": ' in payload:
            payload_dict: dict = json.loads(payload)
            if "token" in payload_dict:
                token = payload_dict["token"]
                safe_token = token[:10] + "..." + token[-10:]
                payload_dict["token"] = safe_token
                return json.dumps(payload_dict)
            else:
                return payload
        else:
            return payload
