""" This script discovers Kasa devices on the local network and prints their details. """

import asyncio
import warnings

from kasa import Discover

# Suppress warnings about unclosed client sessions and connectors
warnings.filterwarnings("ignore", category=ResourceWarning)



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