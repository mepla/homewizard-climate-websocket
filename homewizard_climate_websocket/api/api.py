import logging
import os

import requests

from homewizard_climate_websocket.const import API_LOGIN, API_V1_PATH, API_DEVICES
from homewizard_climate_websocket.model.climate_device import (
    HomeWizardClimateDevice,
    HomeWizardClimateDeviceType,
)

_LOGGER = logging.getLogger(__name__)


class HomeWizardClimateApi:
    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._token = None

    @property
    def token(self) -> str:
        return self._token

    @property
    def username(self) -> str:
        return self._username

    @property
    def password(self) -> str:
        return self._password

    def login(self) -> str:
        login_path = os.path.join(API_V1_PATH, API_LOGIN)
        _LOGGER.debug(f"Logging in to {login_path} with username {self._username}")

        resp = requests.get(login_path, auth=(self._username, self._password))
        _LOGGER.debug(f"Login ({self._username}) status code: {resp.status_code}")
        if (
            resp.status_code == 200
            and "application/json" in resp.headers.get("content-type")
            and "token" in resp.json()
        ):
            self._token = resp.json().get("token")
            _LOGGER.debug(f"Login successful with token for username {self._username}")
            return self._token
        else:
            _LOGGER.error(
                f"Login failed for username {self._username}, response was: {resp}"
            )
            raise InvalidHomewizardAuth()

    def get_devices(self) -> list[HomeWizardClimateDevice]:
        resp = requests.get(
            os.path.join(API_V1_PATH, API_DEVICES),
            auth=(self._username, self._password),
        )
        if (
            resp.status_code == 200
            and resp.headers.get("content-type") == "application/json"
            and "devices" in resp.json()
        ):
            supported_device_types = [t.value for t in HomeWizardClimateDeviceType]
            _LOGGER.debug(
                f'Received {len(resp.json().get("devices"))} device(s) for user '
                f"({self._username}), filtering the supported ones. "
                f"supported_device_types: {supported_device_types}"
            )
            devices_list = list(
                map(
                    HomeWizardClimateDevice.from_dict,
                    # Filter only known device types in: HomeWizardClimateDeviceType
                    filter(
                        lambda x: x.get("type") in supported_device_types,
                        resp.json().get("devices"),
                    ),
                )
            )
            _LOGGER.debug(
                f"Creating {len(devices_list)} device(s) for user "
                f"({self._username}): {[x.identifier for x in devices_list]}"
            )
            return devices_list
        else:
            _LOGGER.error(
                f"Could not get user's ({self._username}) device, response was: {resp}"
            )
            return []


class InvalidHomewizardAuth(RuntimeError):
    pass
