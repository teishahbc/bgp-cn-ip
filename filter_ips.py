# filter_ips.py
import requests
import json
import sys
import os
from datetime import datetime

# --- Configuration ---
TARGET_ASNS = {4134, 56040}  # AS4134 (Chinanet), AS56040 (China Mobile)
BGP_TABLE_URL = "https://bgp.tools/table.jsonl"
OUTPUT_FILENAME = "cn_as4134_as56040_ipv4.txt"
# IMPORTANT: Set a descriptive User-Agent as required by bgp.tools
# Replace 'YourAppName/Version' and 'your-contact@example.com'
USER_AGENT = "GitHubAction-CNIPFilter/1.0 (https://github.com/YOUR_USERNAME/YOUR_REPO; mailto:your-contact@example.com)"
# --- End Configuration ---

def is_ipv4_cidr(cidr_string):
    """Checks if a CIDR string looks like IPv4."""
    return '.' in cidr_string

def fetch_and_filter():
    """Fetches bgp.tools table data and filters for target ASNs/IPv4."""
    print(f"Fetching data from {BGP_TABLE_URL}...")
    headers = {'User-Agent': USER_AGENT}
    filtered_cidrs = set() # Use a set to avoid duplicates

    try:
        response = requests.get(BGP_TABLE_URL, headers=headers, stream=True, timeout=120) # Increased timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)

        print("Processing data...")
        processed_lines = 0
        found_cidrs = 0
        # Process line by line to handle potentially large file
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    asn = data.get("ASN")
                    cidr = data.get("CIDR")

                    if asn in TARGET_ASNS and cidr and is_ipv4_cidr(cidr):
                        filtered_cidrs.add(cidr)
                        found_cidrs += 1

                    processed_lines += 1
                    if processed_lines % 50000 == 0:
                         print(f"  Processed {processed_lines} lines...")

                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON line: {line.decode('utf-8', errors='ignore')}", file=sys.stderr)
                except Exception as e:
                    print(f"Warning: Error processing line: {e}", file=sys.stderr)

        print(f"Finished processing {processed_lines} lines.")
        print(f"Found {len(filtered_cidrs)} unique matching IPv4 CIDRs for ASNs {TARGET_ASNS}.")

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        sys.exit(1) # Exit with error code if fetch fails

    return sorted(list(filtered_cidrs)) # Return sorted list

def write_output(cidrs, filename):
    """Writes the list of CIDRs to the output file."""
    print(f"Writing {len(cidrs)} CIDRs to {filename}...")
    try:
        with open(filename, 'w') as f:
            f.write(f"# IPv4 CIDRs for ASNs {', '.join(map(str, TARGET_ASNS))} (China Telecom/China Mobile)\n")
            f.write(f"# Data sourced from bgp.tools ({BGP_TABLE_URL})\n")
            f.write(f"# Last updated: {datetime.utcnow().isoformat()}Z\n")
            f.write("# WARNING: ASN Geo-location is not always precise. This list is based on ASN registration.\n")
            f.write("#-----------------------------------------------------------\n")
            for cidr in cidrs:
                f.write(f"{cidr}\n")
        print("Write complete.")
    except IOError as e:
        print(f"Error writing to file {filename}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # Ensure the script runs from the repo root for consistent pathing with the Action
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, '..')) # Assumes script is in a subdir like 'scripts' or repo root
    # If the script is in the root, use: repo_root = script_dir
    # Correct path if script is NOT in root:
    # repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) # Go up one level
    # os.chdir(repo_root) # Change working dir - ** Careful if script isn't in root **

    # Adjust OUTPUT_FILENAME path if script isn't in the root
    # For example, if script is in 'scripts/' dir:
    # output_path = os.path.join(repo_root, OUTPUT_FILENAME)
    # If script IS in root, this is fine:
    output_path = OUTPUT_FILENAME

    # --- IMPORTANT: User-Agent Check ---
    if "YOUR_USERNAME" in USER_AGENT or "your-contact@example.com" in USER_AGENT:
         print("ERROR: Please update the USER_AGENT variable in filter_ips.py with your actual GitHub details and contact email.", file=sys.stderr)
         sys.exit(1)

    filtered_data = fetch_and_filter()
    if filtered_data:
        write_output(filtered_data, output_path)
    else:
        print("No matching CIDRs found or error occurred during fetch.")
        # Decide if you want to exit with error or just not update the file
        # Exiting with error might be safer to signal a problem
        sys.exit(1)

    print("Script finished successfully.")
