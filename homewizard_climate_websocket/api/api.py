import os

import requests

from homewizard_climate_websocket.const import API_LOGIN, API_V1_PATH, API_DEVICES
from homewizard_climate_websocket.model.climate_device import (
    HomeWizardClimateDevice,
    HomeWizardClimateDeviceType,
)


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
        resp = requests.get(
            os.path.join(API_V1_PATH, API_LOGIN), auth=(self._username, self._password)
        )

        if (
            resp.status_code == 200
            and resp.headers.get("content-type") == "application/json"
            and "token" in resp.json()
        ):
            self._token = resp.json().get("token")
            return self._token
        else:
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
            return list(
                map(
                    HomeWizardClimateDevice.from_dict,
                    # Filter only known device types in: HomeWizardClimateDeviceType
                    filter(
                        lambda x: x.get("type")
                        in [t.value for t in HomeWizardClimateDeviceType],
                        resp.json().get("devices"),
                    ),
                )
            )


class InvalidHomewizardAuth(RuntimeError):
    pass
