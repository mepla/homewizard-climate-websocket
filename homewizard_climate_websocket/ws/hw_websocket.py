import json
from collections.abc import Callable
from dataclasses import replace

import websocket

from homewizard_climate_websocket.api.api import HomeWizardClimateApi
from homewizard_climate_websocket.const import API_WS_PATH
from homewizard_climate_websocket.model.climate_device import (
    HomeWizardClimateDevice,
)
from homewizard_climate_websocket.model.climate_device_state import (
    HomeWizardClimateDeviceState,
    default_state,
)
from homewizard_climate_websocket.ws.hw_websocket_payloads import (
    HomeWizardClimateWSPayloads,
)


class HomeWizardClimateWebSocket:
    def __init__(
        self,
        api: HomeWizardClimateApi,
        device: HomeWizardClimateDevice,
        on_initialize: Callable = None,
        on_state_change: Callable[[HomeWizardClimateDeviceState], None] = None,
    ):
        self._initialized = False
        self._last_state: HomeWizardClimateDeviceState = default_state()
        self._api = api
        self._device = device
        self._payloads = HomeWizardClimateWSPayloads(api, device)
        self._on_initialize = on_initialize
        self._on_state_change = on_state_change

        self._socket_app = websocket.WebSocketApp(
            API_WS_PATH,
            on_message=self._on_message,
            on_open=self._on_open,
            on_ping=self._on_ping,
        )

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def device(self) -> HomeWizardClimateDevice:
        return self._device

    @property
    def last_state(self) -> HomeWizardClimateDeviceState:
        return self._last_state

    def set_on_state_change(
        self, on_state_change: Callable[[HomeWizardClimateDeviceState], None]
    ):
        self._on_state_change = on_state_change

    def is_device_online(self) -> bool:
        return self.initialized and self._last_state != default_state()

    def connect(self):
        self._socket_app.run_forever()

    async def async_connect(self):
        self._socket_app.run_forever()

    def turn_on(self):
        self._socket_app.send(self._payloads.turn_on())

    def turn_off(self):
        self._socket_app.send(self._payloads.turn_off())

    def set_fan_speed(self, speed: int):
        self._socket_app.send(self._payloads.set_fan_speed(speed))

    def set_target_temperature(self, temp: int):
        self._socket_app.send(self._payloads.set_target_temperature(temp))

    def turn_on_heater(self):
        self._socket_app.send(self._payloads.set_heater())

    def turn_on_cooler(self):
        self._socket_app.send(self._payloads.set_cooler())

    def turn_on_oscillation(self):
        self._socket_app.send(self._payloads.turn_on_oscillate())

    def turn_off_oscillation(self):
        self._socket_app.send(self._payloads.turn_off_oscillate())

    def _on_open(self, ws: websocket.WebSocket):
        self._socket_app.send(self._payloads.hello())

    def _on_ping(self, ws: websocket.WebSocket):
        self._socket_app.sock.pong()

    def _on_message(self, ws: websocket.WebSocket, message: str):
        print(message)

        message_dict: dict = json.loads(message)
        message_device = message_dict.get("device")

        if message_device and message_device != self._device.identifier:
            print(
                "Got a message for a different device. Expected: {}, got: {}".format(
                    self._device.identifierm, message_dict.get("device")
                )
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
            print(f"Got unknown message of type: {message_type}")

    def _handle_response_update(self, received_message: dict):
        message_id = received_message.get("message_id")
        status_code = received_message.get("status")

        if message_id == "hello" and status_code == 200:
            self._socket_app.send(self._payloads.subscribe())

        elif message_id == "subscribe" and status_code == 200:
            pass

    def _handle_device_update(self, received_message: dict):
        if self._last_state == default_state() and not self._initialized:
            self._initialized = True
            if self._on_initialize:
                self._on_initialize()

        self._update_last_state(
            HomeWizardClimateDeviceState.from_dict(received_message.get("state"))
        )

    def _handle_state_update(self, received_message: dict):
        if received_message.get("patch"):
            kw = {}
            for patch in received_message.get("patch"):
                if patch.get("op", "") == "replace":
                    path_split = patch.get("path", "").strip("/").split("/")
                    if len(path_split) == 2 and path_split[0] == "state":
                        kw.update({path_split[1]: patch.get("value")})

            if kw:
                print("updateing: {}".format(kw))
                self._update_last_state(replace(self._last_state, **kw))

    def _update_last_state(self, new_last_state):
        self._last_state = new_last_state
        if self._on_state_change:
            self._on_state_change(self._last_state)
