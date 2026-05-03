""" Scans the network for TP-Link smart plugs and retrieves their names.   """
from collections import Counter

import socket
import sys
import json
import os
import time
import urllib.request
from scapy.layers.l2 import ARP, Ether
import scapy.all as scapy

IEEE_OUI_URL = "https://standards-oui.ieee.org/oui/oui.txt"
IEEE_OUI_FILE = "oui.txt"
OUI_MAX_AGE_DAYS = 30

def get_oui_db(force_update=False):
    """Download and cache the IEEE OUI database, returning a dict of OUI prefix -> manufacturer."""
    needs_update = force_update or (
        not os.path.exists(IEEE_OUI_FILE)
        or (time.time() - os.path.getmtime(IEEE_OUI_FILE)) > OUI_MAX_AGE_DAYS * 86400
    )
    if needs_update:
        print("Updating OUI database from IEEE...")
        req = urllib.request.Request(IEEE_OUI_URL, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/plain,text/html,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=30) as response, open(IEEE_OUI_FILE, "wb") as out:
            out.write(response.read())

    oui_db = {}
    with open(IEEE_OUI_FILE, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "(hex)" in line:
                parts = line.split("(hex)")
                if len(parts) == 2:
                    prefix = parts[0].strip().replace("-", ":").upper()
                    manufacturer = parts[1].strip()
                    oui_db[prefix] = manufacturer
    return oui_db

def get_kasa_macs():
    """read the TCP_LINK MAC prefixes from the JSON file"""
    try:
        with open("macs.json", "r", encoding="utf-8") as file:
            # Use json.load() to deserialize the JSON data into a Python dictionary
            data = json.load(file)
            # Extract the macs array from the nested structure
            macs = data[0]["kasa_macs"]
            return macs
    except FileNotFoundError:
        print("Error: The file 'macs.json' was not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(
            "Error: Could not decode JSON from the file. Check for valid JSON syntax."
        )
        sys.exit(1)


def scan(ip, force_update=False):
    """
    Scans the network for TP-Link smart plugs and retrieves their names.

    Args:
      ip: The IP address or range to scan.
      force_update: If True, force refresh of the OUI database.

    Returns:
      A list of dictionaries, where each dictionary represents a TP-Link smart plug
      and contains its IP address, MAC address, and device name.
    """

    arp_request = ARP(pdst=ip)
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    arp_request_broadcast = broadcast / arp_request
    answered_list = scapy.srp(arp_request_broadcast, timeout=1, verbose=True)[0]

    macs = get_kasa_macs()
    oui_db = get_oui_db(force_update=force_update)
    tp_link_devices = []
    for element in answered_list:
        # Check if the MAC address is from a TP-Link vendor
        device_mac_prefix = element[1].hwsrc[:8].lower()
        if device_mac_prefix in macs:
            ip_address = element[1].psrc
            mac_address = element[1].hwsrc
            try:
                # Attempt to resolve the hostname using the IP address
                hostname = socket.gethostbyaddr(ip_address)[0]
            except socket.herror:
                hostname = "Unknown"  # Set hostname to "Unknown" if it cannot be resolved
            oui = mac_address[:8].upper()
            manufacturer = oui_db.get(oui, "Unknown")
            device = {"ip": ip_address, "mac": mac_address, "oui": oui, "manufacturer": manufacturer, "name": hostname}
            tp_link_devices.append(device)

    return tp_link_devices


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scan for TP-Link Kasa devices.")
    parser.add_argument("--update-oui", action="store_true", help="Force refresh of the OUI database.")
    args = parser.parse_args()

    # You can modify the target IP address or range as needed
    TARGET_IP_RANGE= "192.168.1.0/24"
    scan_results = scan(TARGET_IP_RANGE, force_update=args.update_oui)

    if scan_results:
        print("TP-Link Smart Plugs found:")
        for kasa_device in scan_results:
            print(
                f"IP Address: {kasa_device['ip']}, "
                f"MAC Address: {kasa_device['mac']}, "
                f"OUI: {kasa_device['oui']}, "
                f"Manufacturer: {kasa_device['manufacturer']}, "
                f"Name: {kasa_device['name']}"
            )

        print("\n--- OUI / Manufacturer Summary ---")
        oui_counts = Counter((d["oui"], d["manufacturer"]) for d in scan_results)
        for (oui, manufacturer), count in sorted(oui_counts.items(), key=lambda x: -x[1]):
            print(f"  {oui}  {manufacturer}: {count}")
    else:
        print("No TP-Link Smart Plugs found on the network.")
