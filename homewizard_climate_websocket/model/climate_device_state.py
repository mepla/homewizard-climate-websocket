from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class HomeWizardClimateDeviceState:
    power_on: bool
    mode: str
    current_temperature: int
    target_temperature: int
    fan_speed: int
    oscillate: bool
    timer: int
    error: list[str]
    heat_status: str
    vent_heat: bool
    silent: bool
    heater: bool
    ext_mode: list[str]
    ext_current_temperature: int
    ext_target_temperature: int


def default_state():
    return HomeWizardClimateDeviceState.from_dict(
        {
            "power_on": False,
            "mode": "normal",
            "current_temperature": 0,
            "target_temperature": 0,
            "fan_speed": 0,
            "oscillate": False,
            "timer": 0,
            "ext_mode": [],
            "heat_status": "idle",
            "vent_heat": False,
            "silent": False,
            "heater": False,
            "error": [],
            "ext_current_temperature": 0,
            "ext_target_temperature": 0,
        }
    )
