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


def diff_states(
    first_state: HomeWizardClimateDeviceState,
    second_state: HomeWizardClimateDeviceState,
) -> str:
    result = ""
    for k, v in first_state.to_dict().items():
        # fix for HEATER type
        if k in second_state.to_dict():
            second_value = second_state.to_dict().get(k)
            if v != second_value:
                result += f"{k}: {v} -> {second_value}, "
    
    return result
