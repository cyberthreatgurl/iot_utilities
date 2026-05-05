""" This script discovers Kasa devices and checks if they exist in Home Assistant. """
import asyncio
from kasa import Discover
from kasa.exceptions import KasaException
import requests
import os
import logging
import warnings
import json
import subprocess
import re
import argparse
from dotenv import load_dotenv

load_dotenv()

# Suppress warnings
warnings.filterwarnings("ignore")
def no_warning(*_args, **_kwargs): pass
warnings.showwarning = no_warning

logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp.client").setLevel(logging.CRITICAL)

def get_ha_device_map(api_url, api_key):
    """
    Uses a Jinja2 template to fetch a map of {IP_Address: Entity_ID} 
    from Home Assistant's Device Registry.
    """
    url = f"{api_url}/api/template"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # This template iterates through all entities, finds their device config, 
    # and extracts the 'mac' connection field.
    template = """
    {% set ns = namespace(mapping=[]) %}
    {% for state in states %}
      {% set dev_id = device_id(state.entity_id) %}
      {% if dev_id %}
        {% set conns = device_attr(dev_id, 'connections') %}
        {% if conns %}
          {% for conn in conns %}
            {% if conn[0] == 'mac' %}
              {% set ns.mapping = ns.mapping + [{'mac': conn[1], 'entity': state.entity_id}] %}
            {% endif %}
          {% endfor %}
        {% endif %}
      {% endif %}
    {% endfor %}
    {{ ns.mapping | to_json }}
    """

    try:
        response = requests.post(url, headers=headers, json={"template": template}, timeout=10)
        # If there's an error, print the message from HA
        if not response.ok:
            print(f"HA API Error: {response.text}")
        response.raise_for_status()
        
        # Convert list of dicts to a single lookup dict mapping MAC -> Entity ID
        data = response.json()
        
        # Normalise MAC addresses for matching (upper case)
        ha_map = {item['mac'].upper(): item['entity'] for item in data}
        
        print(f"Retrieving HA Data... Found {len(ha_map)} unique device MACs in Home Assistant.")
        return ha_map
            
    except requests.RequestException as e:
        print(f"Error querying Home Assistant API: {e}")
        return {}

def get_arp_devices():
    """ Runs 'arp -an' and returns a dictionary mapping MAC -> IP. """
    devices = {}
    try:
        out = subprocess.check_output(["arp", "-an"]).decode("utf-8")
        for line in out.splitlines():
            # Example macOS output: ? (192.168.1.159) at 48:22:54:a0:6f:cb on en0 ifscope [ether]
            match = re.search(r"\(([\d\.]+)\)\s+at\s+([a-fA-F0-9:]+)\s+", line)
            if match:
                ip = match.group(1)
                mac_raw = match.group(2)
                if mac_raw != "(incomplete)":
                    try:
                        # Normalize MAC address format to upper case, 2-digit hex parts (e.g. 0:1:2 -> 00:01:02)
                        mac = ":".join(f"{int(p, 16):02X}" for p in mac_raw.split(":"))
                        devices[mac] = ip
                    except ValueError:
                        pass
    except Exception as e:
        print(f"Error fetching ARP table: {e}")
    return devices

def get_oui_db(filename="oui.txt"):
    """ Parses the IEEE OUI database file into a prefix -> manufacturer dictionary. """
    oui_db = {}
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if "(hex)" in line:
                    parts = line.split("(hex)")
                    if len(parts) == 2:
                        prefix = parts[0].strip().replace("-", ":").upper()
                        manufacturer = parts[1].strip()
                        oui_db[prefix] = manufacturer
    except Exception as e:
        print(f"Error loading {filename}: {e}")
    return oui_db

async def main(target=None):
    # Configuration
    ha_base_url = "http://10.0.0.100:8123"
    api_key = os.getenv("HA_API_KEY")
    kasa_username = os.getenv("KASA_USERNAME")
    kasa_password = os.getenv("KASA_PASSWORD")
    
    if target:
        target = target.strip().upper()
        print(f"Auditing specific target: {target}")
    
    if not api_key:
        print("Error: HA_API_KEY not found in environment variables.")
        exit(1)

    if not kasa_username or not kasa_password:
        print("Error: KASA_USERNAME or KASA_PASSWORD not found in environment variables.")
        exit(1)

    # 1. Get the Map from Home Assistant
    ha_mac_map = get_ha_device_map(ha_base_url, api_key)

    print("\nScanning local network for Kasa devices...")
    
    # 2. Discover Kasa Devices
    devices = await Discover.discover(username=kasa_username, password=kasa_password, timeout=3)
    
    sorted_devices = sorted(
        devices.values(), 
        key=lambda dev: dev.mac[-5:] if dev.mac else ""
    )

    # Load known MAC OUIs from macs.json
    try:
        with open("macs.json", "r") as f:
            macs_data = json.load(f)
            tapo_kasa_ouis = [mac.strip().upper() for mac in macs_data[0].get("kasa_macs", [])]
    except Exception as e:
        print(f"Error loading macs.json: {e}")
        tapo_kasa_ouis = []

    print("\nScanning ARP table for other local network devices...")
    arp_devices = get_arp_devices()
    oui_db = get_oui_db()
    
    # We will track the MACs of the Kasas we discover
    processed_kasa_macs = set()
    output_rows = []

    for dev in sorted_devices:
        dev_mac = dev.mac.upper() if dev.mac else ""
        oui = dev_mac[:8] if dev_mac else ""
        processed_kasa_macs.add(dev_mac)

        if target and target not in (dev_mac, dev.host.upper()):
            continue
        
        # Check OUI prefix (first 8 characters like 'AA:BB:CC')
        if tapo_kasa_ouis and oui not in tapo_kasa_ouis:
            status = "\033[93mSKIPPED (OUI)\033[0m"
            manufacturer = oui_db.get(oui, "Unknown Manufacturer")
            output_rows.append({"manufacturer": manufacturer, "oui": oui, "ip": dev.host, "mac": dev_mac, "status": status, "display": "N/A"})
            continue

        try:
            await dev.update()
            
            # Cross-reference with HA data using MAC
            ha_entity = ha_mac_map.get(dev_mac) if dev.mac else None
            
            if ha_entity:
                # Device is already managed in HA, skip printing
                continue
                
            status = "\033[91mUNLINKED (KASA)\033[0m"
            entity_display = f"\033[93m{dev.alias}\033[0m"
            manufacturer = oui_db.get(oui, "Unknown Manufacturer")

            output_rows.append({"manufacturer": manufacturer, "oui": oui, "ip": dev.host, "mac": dev_mac, "status": status, "display": entity_display})

        except (KasaException, asyncio.TimeoutError, OSError) as e:
            status = "\033[91mNON-COM\033[0m"
            manufacturer = oui_db.get(oui, "Unknown Manufacturer")
            entity_display = f"\033[36m{manufacturer}\033[0m"
            output_rows.append({"manufacturer": manufacturer, "oui": oui, "ip": dev.host, "mac": dev_mac, "status": status, "display": entity_display})

    # Now iterate the rest of the ARP table
    for mac, ip in arp_devices.items():
        if target and target not in (mac, ip.upper()):
            continue
            
        if mac in processed_kasa_macs or mac == "FF:FF:FF:FF:FF:FF":
            continue

        ha_entity = ha_mac_map.get(mac)
        
        if ha_entity:
            # Device is already managed in HA, skip printing
            continue
            
        oui_prefix = mac[:8].upper()
        status = "\033[93mUNLINKED (OTHER)\033[0m"
        # OUI fallback
        manufacturer = oui_db.get(oui_prefix, "Unknown Manufacturer")
        entity_display = f"\033[36m{manufacturer}\033[0m"

        output_rows.append({"manufacturer": manufacturer, "oui": oui_prefix, "ip": ip, "mac": mac, "status": status, "display": entity_display})

    # Sort the rows by manufacturer first, then by full MAC address
    output_rows.sort(key=lambda x: (x["manufacturer"], x["mac"]))

    print(f"\n{'IP Address':<16} | {'MAC Address':<18} | {'Status':<19} | {'HA Entity / Manufacturer Info'}")
    print("-" * 85)

    last_manuf = None
    for row in output_rows:
        # Print a blank line between different manufacturer groups
        if last_manuf is not None and row["manufacturer"] != last_manuf:
            print("")
        last_manuf = row["manufacturer"]
        
        print(f"{row['ip']:<16} | {row['mac']:<18} | {row['status']:<28} | {row['display']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit local IoT devices against Home Assistant.")
    parser.add_argument("target", nargs="?", help="Optional IP address or MAC address to specifically analyze.")
    args = parser.parse_args()

    asyncio.run(main(args.target))
