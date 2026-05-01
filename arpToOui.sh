#!/bin/bash

OUI_FILE="out.txt"

if [ ! -f "$OUI_FILE" ]; then
    echo "Error: $OUI_FILE not found."
    exit 1
fi

TMP_DATA=$(mktemp)

# 1. Process ARP and normalize data
arp -a | while read -r line; do
    mac=$(echo "$line" | grep -oE '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}')
    ip=$(echo "$line" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+')

    if [ -n "$mac" ]; then
        # Create the lookup string (XX-XX-XX) for the file search
        oui_lookup=$(echo "$mac" | cut -d: -f1-3 | tr '[:lower:]' '[:upper:]' | tr ':' '-')
        
        # Create the display string (xx:xx:xx) for the final output
        oui_display=$(echo "$oui_lookup" | tr '[:upper:]' '[:lower:]' | tr '-' ':')
        
        # Vendor Lookup
        vendor=$(grep "^$oui_lookup" "$OUI_FILE" | sed 's/.*(hex)\s*//' | xargs)
        [ -z "$vendor" ] && vendor="Unknown"

        echo "$oui_display|$mac|$ip|$vendor" >> "$TMP_DATA"
    fi
done

# 2. Sort by OUI and Print
current_oui=""
sort -t'|' -k1 "$TMP_DATA" | while IFS='|' read -r oui mac ip vendor; do
    
    if [[ -n "$current_oui" && "$oui" != "$current_oui" ]]; then
        echo ""
    fi

    printf "%-10s  %-17s  %-15s  %s\n" "$oui" "$mac" "$ip" "$vendor"
    
    current_oui="$oui"
done

rm "$TMP_DATA"