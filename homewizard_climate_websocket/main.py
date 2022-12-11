import asyncio
import os

from homewizard_climate_websocket.api.api import HomeWizardClimateApi
from homewizard_climate_websocket.ws.hw_websocket import HomeWizardClimateWebSocket


async def main():
    username = os.environ["HW_CLIMATE_USERNAME"]
    password = os.environ["HW_CLIMATE_PASSWORD"]
    api = HomeWizardClimateApi(username, password)
    api.login()
    devices = api.get_devices()
    print(devices)
    ws = HomeWizardClimateWebSocket(api, devices[0])
    await ws.async_connect()


if __name__ == "__main__":
    asyncio.run(main())
