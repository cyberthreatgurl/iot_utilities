import subprocess
def get_arp_table():
    out = subprocess.check_output(["arp", "-a"]).decode("utf-8")
    devices = {}
    for line in out.splitlines():
        if " at " in line and " on " in line:
            try:
                ip_part = line.split("(")[1].split(")")[0]
                mac_part = line.split(" at ")[1].split(" on ")[0].strip()
                if mac_part != "(incomplete)" and ":" in mac_part:
                    parts = mac_part.split(":")
                    mac_normalized = ":".join(f"{p:>02}" if len(p) == 2 else f"0{p}".upper() for p in parts).upper()
                    devices[mac_normalized] = ip_part
            except Exception as e:
                pass
    return list(devices.items())[:5]
print(get_arp_table())
