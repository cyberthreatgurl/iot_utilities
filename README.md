# iot_utilities
Tools for finding IoT devices on your local network and integrating them with Home Assistant.

This repository contains several utility scripts designed to audit and manage locally connected smart devices, cross-reference them with Home Assistant configurations, and identify unmanaged hardware via MAC OUI (Organizationally Unique Identifier) lookups.

## Features

- **Home Assistant Verification**: Connects to HA via Long-Lived Access Tokens and audits local Kasa plugs and generic network devices against active HA entities.
- **Kasa / Tapo Plug Discovery**: Employs heavily localized Kasa UDP discovery (via `python-kasa`) with authorized credentials.
- **MAC OUI Resolution & ARP Scanning**: Reads the local ARP cache (`arp -an`) to uncover other local networked entities gracefully and resolves their hardware manufacturer.
- **Hue Bridge Pairing**: Simple utilities to interact with a local Philips Hue bridge.

## File Breakdown

### 1. `audit_iot.py`
The primary auditing tool. It cross-references devices found locally on the network (both Kasa plugs via Discovery and generic devices via the system ARP table) against your Home Assistant instance to tell you what devices are internally "Managed" vs "Unlinked".

- **Usage**:  
  `python audit_iot.py [IP_OR_MAC_ADDRESS]`
  - If executed with no arguments, audits the whole local network. 
  - If executed with a specific IP or MAC, it only scans that specific device.
  
- **Requirements**: Requires a `.env` file containing `HA_API_KEY=your_token_here`.

### 2. `kasa_util.py`
A lightweight script purely to discover and print local TP-Link Kasa / Tapo devices using the local network broadcast payload without checking against Home Assistant. Sorts the output nicely by MAC address.

- **Usage**:  
  `python kasa_util.py`

### 3. `tp-scan2.py`
A robust `scapy` network scanner that generates active ARP requests across a given subnet (e.g., `192.168.1.0/24`) and filters the responses looking specifically for TP-Link hardware OUIs. It can force-download the latest IEEE OUI database if out of date.

- **Usage**:  
  `python tp-scan2.py [--update-oui]`

### 4. `hue_util.py`
A quick integration script bridging with Philips Hue hardware via `phue`, authenticating, retrieving bridge state, and registering API connectivity.

- **Usage**:  
  `python hue_util.py`

### 5. `arpToOui.sh`
A bash utility script utilizing standard unix CLI tools (`arp -a`) to grep out IPs/MACs and convert MAC addresses to their respective hardware makers natively via standard OUI formats formatting.

## Configuration & Setup

1. **Python Environment**  
   Ensure you are using your provided virtual environment:
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt # (install python-dotenv, python-kasa, requests, scapy, phue)
   ```

2. **Environment Variables**  
   Create a `.env` file in the root of the repository:
   ```env
   HA_API_KEY=your_home_assistant_long_lived_access_token
   ```

3. **Known MAC Definitions (`macs.json`)**  
   The scanner uses `macs.json` to keep track of known Kasa / Tapo prefixes (OUIs). 

4. **IEEE OUI Definitions (`oui.txt`)**
   Used to map MAC address prefixes to actual manufacturing companies (like Amazon, TP-Link, Google, etc.).
