""" This script discovers Kasa devices on the local network and prints their details. """

import warnings
# Suppress warnings about unclosed client sessions and connectors
warnings.filterwarnings("ignore")
def no_warning(*args, **kwargs):
    pass
warnings.showwarning = no_warning

import logging
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp.client").setLevel(logging.CRITICAL)

import asyncio
from kasa import Discover



async def main():
    """Discover Kasa devices on the local network and print their details."""
    devices = await Discover.discover(username="kaver68@gmail.com", password="tl@hPQV6zjJYN87#")
    for dev in devices.values():
        try:
            await dev.update()
            print(dev.host, dev.mac, dev.model, dev.alias, dev.device_type)
        except Exception as e:
            # This continues to output your specific error for the IP/device
            print(f"Error querying device {dev.host}: {e}")

if __name__ == "__main__":
    asyncio.run(main())