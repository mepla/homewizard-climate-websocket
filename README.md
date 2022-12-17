# homewizard-climate-websocket

API/Websocket to control Homewizard Climate devices

---

This library allows you to control your Homewizard Climate devices. There are a multitude of brands that use Homewizard apps for their smart controls.

This was developed in oder to be used in a [Home Assistant](https://www.home-assistant.io/) integration. It has not been thoroughly tested or worked with as a standalone code.

### Supported Devices
This library is in an early stage of development and only works for the following device types returned from the Homewizard Climate API:

- `heaterfan`

It has been tested on the following devices (even though it might work on others too):
- [Princess Smart Heating and Cooling Tower (01.347000.01.001)](https://www.princesshome.eu/en-gb/princess-01-347000-01-001-smart-heating-and-01.347000.01.001)

![](https://www.princesshome.eu/product/image/large/01.347000.01.001_3.jpg)

## Quick start
There's no separate `requirements.txt` file, the dependencies can be found and installed in `setup.py`

```
username = os.environ["HW_CLIMATE_USERNAME"]
password = os.environ["HW_CLIMATE_PASSWORD"]
api = HomeWizardClimateApi(username, password)
api.login()
devices = api.get_devices()
ws = HomeWizardClimateWebSocket(api, devices[0])
ws.connect_in_thread() # There's also a blocking `connect`
time.sleep(5)
```

## Installation

**Stable Release (PyPi):** `pip install homewizard_climate_websocket`<br>
**Local Development:** `pip install .`

## Development
Any help to increase the number of supported devices is much appreciated as I only had access to the one mentioned above.

See [CONTRIBUTING.md](CONTRIBUTING.md) for information related to developing the code.
