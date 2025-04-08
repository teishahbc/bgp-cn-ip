# filter_ips.py
import requests
import sys
import os
from datetime import datetime

# --- Configuration ---
TARGET_ASNS = {4134, 56040}  # AS4134 (Chinanet), AS56040 (China Mobile)
BGP_TABLE_URL = "https://bgp.tools/table.txt"
OUTPUT_FILENAME = "cn_as4134_as56040_ipv4.txt"

# --- CRITICAL CONFIGURATION ---
# User-Agent set according to user request.
# Note: 'no@thankyou.com' fulfills the format but not the intent of providing a real contact.
USER_AGENT = "GitHubAction-CNIPFilter/1.0 (https://github.com/teishahbc/bgp-cn-ip; mailto:no@thankyou.com)"
# --- End Configuration ---

def is_ipv4_cidr(cidr_string):
    """Checks if a CIDR string looks like IPv4 (contains a period and no colon)."""
    return '.' in cidr_string and ':' not in cidr_string

def fetch_and_filter():
    """Fetches bgp.tools table.txt data and filters for target ASNs/IPv4."""
    print(f"Fetching data from {BGP_TABLE_URL}...")
    # Use the configured User-Agent
    headers = {'User-Agent': USER_AGENT}
    filtered_cidrs = set() # Use a set to avoid duplicates

    # --- Optional User-Agent Placeholder Check ---
    # You might want to keep this check *during development* if you switch emails,
    # but since you explicitly set 'no@thankyou.com', the original placeholder check isn't needed.
    # You could add a check for the generic placeholders if you copied old code:
    if "YOUR_USERNAME" in USER_AGENT or "YOUR_REPO" in USER_AGENT or "your-contact@example.com" in USER_AGENT:
         print("\nFATAL ERROR: Generic placeholder detected in USER_AGENT. Please review.", file=sys.stderr)
         sys.exit(1)
    # --- End User-Agent Placeholder Check ---

    try:
        response = requests.get(BGP_TABLE_URL, headers=headers, timeout=180, stream=True)
        response.raise_for_status()
        print(f"HTTP Status Code: {response.status_code}")

        print("Processing data...")
        processed_lines = 0
        for line_bytes in response.iter_lines():
            if line_bytes:
                processed_lines += 1
                try:
                    line = line_bytes.decode('utf-8').strip()
                    if not line or line.startswith('#'):
                        continue

                    parts = line.split()
                    if len(parts) >= 2:
                        cidr = parts[0]
                        asn_str = parts[1]
                        try:
                            asn = int(asn_str)
                        except ValueError:
                            # Log only first few errors to avoid spamming logs
                            if processed_lines < 100 and len(filtered_cidrs) < 10:
                                print(f"Warning: Could not parse ASN '{asn_str}' from line: {line}", file=sys.stderr)
                            continue

                        if asn in TARGET_ASNS and is_ipv4_cidr(cidr):
                            filtered_cidrs.add(cidr)
                    else:
                        # Log only first few errors
                        if processed_lines < 100 and len(filtered_cidrs) < 10:
                             print(f"Warning: Unexpected line format: {line}", file=sys.stderr)

                    # Progress update
                    if processed_lines % 100000 == 0:
                         print(f"  Processed {processed_lines} lines...")
                except Exception as e:
                    # Catch other potential errors during line processing
                    print(f"Warning: Error processing line: {line_bytes.decode('utf-8', errors='ignore')}: {e}", file=sys.stderr)

        print(f"Finished processing {processed_lines} lines.")
        print(f"Found {len(filtered_cidrs)} unique matching IPv4 CIDRs for ASNs {TARGET_ASNS}.")

    except requests.exceptions.RequestException as e:
        print(f"Fatal: Error fetching data from {BGP_TABLE_URL}: {e}", file=sys.stderr)
        # Check if the error is client-side (e.g., 403 Forbidden), which might indicate a User-Agent issue despite the format being correct.
        if e.response is not None:
             print(f"Fatal: Received status code {e.response.status_code}", file=sys.stderr)
             if e.response.status_code == 403:
                  print("Fatal: Received 403 Forbidden. This might be due to the User-Agent or excessive requests.", file=sys.stderr)
        sys.exit(1) # Exit with error code if fetch fails

    return sorted(list(filtered_cidrs))

def write_output(cidrs, filename):
    """Writes the list of CIDRs to the output file with headers."""
    print(f"Writing {len(cidrs)} CIDRs to {filename}...")
    try:
        with open(filename, 'w') as f:
            f.write(f"# IPv4 CIDRs for ASNs {', '.join(map(str, TARGET_ASNS))} (China Telecom/China Mobile)\n")
            f.write(f"# Data sourced from bgp.tools ({BGP_TABLE_URL})\n")
            f.write(f"# Last updated: {datetime.utcnow().isoformat()}Z\n")
            f.write("# WARNING: ASN Geo-location is not always precise. This list is based on ASN registration only.\n")
            f.write("#-----------------------------------------------------------\n")
            for cidr in cidrs:
                f.write(f"{cidr}\n")
        print("Write complete.")
    except IOError as e:
        print(f"Fatal: Error writing to file {filename}: {e}", file=sys.stderr)
        sys.exit(1) # Exit with error code if file write fails

if __name__ == "__main__":
    output_path = OUTPUT_FILENAME
    # Fetch and filter the data
    filtered_data = fetch_and_filter()

    if filtered_data:
        write_output(filtered_data, output_path)
    else:
        print("No matching CIDRs found or data fetch issue occurred. Output file will not be updated.")
        pass # Exit successfully, GitHub Action won't commit if file is unchanged

    print("Script finished.")
