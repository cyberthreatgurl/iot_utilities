""" This script discovers Kasa devices on the local network and prints their details. """
import asyncio
from kasa import Discover
from kasa.exceptions import KasaException
import requests
import os
import logging
import warnings
from dotenv import load_dotenv

load_dotenv()

# Suppress warnings about unclosed client sessions and connectors
warnings.filterwarnings("ignore")

def no_warning(*_args, **_kwargs):
    """Ignore all warning emissions by replacing the default warning handler."""

warnings.showwarning = no_warning

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp.client").setLevel(logging.CRITICAL)


def query_home_assistant_api(api_key):
    """Query the Home Assistant API to retrieve device information."""

    url = "http://10.0.0.100:8123/api/states"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=(5, 10))
        response.raise_for_status()
        devices = response.json()
        print(f"Retrieved {len(devices)} devices from Home Assistant API.")
        # You can further process the devices as needed
        print("Devices from Home Assistant API:")
        for device in devices:
            print(device)
            
    except requests.RequestException as e:
        print(f"Error querying Home Assistant API: {e}")

async def main():
    """Discover Kasa devices on the local network and print their details."""
    devices = await Discover.discover(username="kaver68@gmail.com", password="tl@hPQV6zjJYN87#")
    
    # Sort by the last two bytes (last 5 characters like "XX:XX") of the MAC address
    sorted_devices = sorted(
        devices.values(), 
        key=lambda dev: dev.mac[-5:] if dev.mac else ""
    )
    
    for dev in sorted_devices:
        try:
            await dev.update()
            print(dev.host, dev.mac, dev.model, dev.alias, dev.device_type)
        except (KasaException, asyncio.TimeoutError, OSError) as e:
            # This continues to output your specific error for the IP/device
            print(f"Error querying device \033[91m{dev.host}\033[0m with MAC \033[91m{dev.mac}\033[0m: {e}")

if __name__ == "__main__":
    api_key = os.getenv("HA_API_KEY")
    if not api_key:
        print("Home Assistant API key not found in environment variables.")
        exit(1)

    asyncio.run(main())
    query_home_assistant_api(api_key)
