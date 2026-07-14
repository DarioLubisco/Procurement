"""
Extractor de datos vía MCP paginado.
Genera CSVs desde las queries del optimizador v3.2.
"""
import json
import csv
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")
os.makedirs(DATA_DIR, exist_ok=True)

# We'll call this script with the JSON data piped from MCP
# This is a helper to convert JSON arrays to CSV

def json_to_csv(json_data, output_file, append=False):
    """Convert a list of dicts to CSV."""
    if not json_data:
        return
    
    mode = 'a' if append else 'w'
    write_header = not append
    
    with open(output_file, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=json_data[0].keys())
        if write_header:
            writer.writeheader()
        writer.writerows(json_data)
    
    print(f"{'Appended' if append else 'Wrote'} {len(json_data)} rows to {output_file}")


if __name__ == "__main__":
    # Read JSON from stdin
    data = json.load(sys.stdin)
    output_file = sys.argv[1] if len(sys.argv) > 1 else "output.csv"
    append = sys.argv[2] == "append" if len(sys.argv) > 2 else False
    json_to_csv(data, output_file, append)
