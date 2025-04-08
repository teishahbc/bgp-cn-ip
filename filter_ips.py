import requests
import sys
import os
from datetime import datetime, timezone # Added timezone

# --- Configuration ---
TARGET_ASNS_PRIMARY = {4134, 56040}  # AS4134 (Chinanet), AS56040 (China Mobile)
TARGET_ASNS_SECONDARY = {4134, 9808, 4837, 4812, 24400, 17621, 4808, 56046, 56048, 56040, 17816, 17622, 56041, 24444, 56044, 24445, 56047, 24547, 38019}
BGP_TABLE_URL = "https://bgp.tools/table.txt"
OUTPUT_FILENAME_PRIMARY = "cn_as4134_as56040_ipv4.txt"
OUTPUT_FILENAME_SECONDARY = "cn_other_asns_ipv4.txt"

# --- CRITICAL CONFIGURATION ---
# User-Agent set according to user request.
# Note: 'no@thankyou.com' fulfills the format but not the intent of providing a real contact.
USER_AGENT = "GitHubAction-CNIPFilter/1.0 (https://github.com/teishahbc/bgp-cn-ip; mailto:no@thankyou.com)"
# --- End Configuration ---

def is_ipv4_cidr(cidr_string):
    """Checks if a CIDR string looks like IPv4 (contains a period and no colon)."""
    return '.' in cidr_string and ':' not in cidr_string

def fetch_and_filter(target_asns):
    """Fetches bgp.tools table.txt data and filters for target ASNs/IPv4."""
    print(f"Fetching data from {BGP_TABLE_URL} for ASNs: {target_asns}...")
    # Use the configured User-Agent
    headers = {'User-Agent': USER_AGENT}
    filtered_cidrs = set() # Use a set to avoid duplicates

    try:
        # Increased timeout slightly, added stream=True for memory efficiency
        response = requests.get(BGP_TABLE_URL, headers=headers, timeout=180, stream=True)
        response.raise_for_status()
        print(f"HTTP Status Code: {response.status_code}")

        print("Processing data...")
        processed_lines = 0
        # Process line by line using iter_lines for large files
        for line_bytes in response.iter_lines():
            if line_bytes:
                processed_lines += 1
                try:
                    # Decode from bytes, strip leading/trailing whitespace
                    line = line_bytes.decode('utf-8').strip()
                    # Skip empty lines or comments
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
                            continue # Skip this line if ASN is not an integer

                        # Check if the ASN is in our target list and the CIDR looks like IPv4
                        if asn in target_asns and is_ipv4_cidr(cidr):
                            filtered_cidrs.add(cidr)
                    else:
                        # Log only first few errors for malformed lines
                        if processed_lines < 100 and len(filtered_cidrs) < 10:
                             print(f"Warning: Unexpected line format: {line}", file=sys.stderr)

                    # Provide progress update periodically
                    if processed_lines % 100000 == 0:
                         print(f"  Processed {processed_lines} lines...")

                except Exception as e:
                    # Catch other potential errors during line processing (e.g., decoding errors)
                    print(f"Warning: Error processing line: {line_bytes.decode('utf-8', errors='ignore')}: {e}", file=sys.stderr)

        print(f"Finished processing {processed_lines} lines.")
        print(f"Found {len(filtered_cidrs)} unique matching IPv4 CIDRs for ASNs {target_asns}.")

    except requests.exceptions.RequestException as e:
        print(f"Fatal: Error fetching data from {BGP_TABLE_URL}: {e}", file=sys.stderr)
        # Provide more info if it's an HTTP error like 403 Forbidden
        if e.response is not None:
             print(f"Fatal: Received status code {e.response.status_code}", file=sys.stderr)
             if e.response.status_code == 403:
                  print("Fatal: Received 403 Forbidden. This might be due to the User-Agent or excessive requests.", file=sys.stderr)
        sys.exit(1) # Exit with error code if fetch fails

    # Return the found CIDRs as a sorted list
    return sorted(list(filtered_cidrs))

def write_output(cidrs, filename, target_asns):
    """Writes the list of CIDRs to the output file with headers."""
    print(f"Writing {len(cidrs)} CIDRs to {filename}...")
    try:
        with open(filename, 'w', encoding='utf-8') as f: # Specify encoding
            f.write(f"# IPv4 CIDRs for ASNs {', '.join(map(str, sorted(list(target_asns))))}\n") # Sort ASNs in header
            f.write(f"# Data sourced from bgp.tools ({BGP_TABLE_URL})\n")
            # Use timezone-aware UTC timestamp
            f.write(f"# Last updated: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}\n")
            f.write("# WARNING: ASN Geo-location is not always precise. This list is based on ASN registration only.\n")
            f.write("#-----------------------------------------------------------\n")
            for cidr in cidrs:
                f.write(f"{cidr}\n")
        print("Write complete.")
    except IOError as e:
        print(f"Fatal: Error writing to file {filename}: {e}", file=sys.stderr)
        sys.exit(1) # Exit with error code if file write fails

if __name__ == "__main__":
    print("Starting IP filter script...")

    # Fetch and filter the data for primary ASNs
    print("\n--- Processing Primary ASNs ---")
    filtered_data_primary = fetch_and_filter(TARGET_ASNS_PRIMARY)
    if filtered_data_primary:
        write_output(filtered_data_primary, OUTPUT_FILENAME_PRIMARY, TARGET_ASNS_PRIMARY)
    else:
        print(f"Warning: No matching CIDRs found or data fetch issue occurred for primary ASNs {TARGET_ASNS_PRIMARY}. Output file '{OUTPUT_FILENAME_PRIMARY}' will not be updated or created.")

    # Fetch and filter the data for secondary ASNs
    print("\n--- Processing Secondary ASNs ---")
    filtered_data_secondary = fetch_and_filter(TARGET_ASNS_SECONDARY)
    if filtered_data_secondary:
        write_output(filtered_data_secondary, OUTPUT_FILENAME_SECONDARY, TARGET_ASNS_SECONDARY)
    else:
        print(f"Warning: No matching CIDRs found or data fetch issue occurred for secondary ASNs {TARGET_ASNS_SECONDARY}. Output file '{OUTPUT_FILENAME_SECONDARY}' will not be updated or created.")

    print("\nScript finished.")
