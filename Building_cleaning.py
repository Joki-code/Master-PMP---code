import csv
from pathlib import Path

# ==================== USER CONFIGURATION ====================
# 1. Path to the CSV file containing the EGID list (one column named "EGID")
EGID_LIST_FILE = r"C:\Users\Joki\Desktop\Science Po\Master PMP\Mémoire\Data\OFS-Stat-Bl\files - work\common_egids.csv"

# 2. Define the years and corresponding .txt files (semicolon separated, with EGID and GENH1S columns)
#    Format: (year, file_path)
TXT_FILES = [
    (2021, r"x\files\GWS2021_GEB_Uni Lausanne_20260602.txt"),
    (2022, r"x\files\GWS2022_GEB_Uni Lausanne_20260602.txt"),
    (2023, r"xl\files\GWS2023_GEB_Uni Lausanne_20260602.txt"),
    (2024, r"xl\files\GWS2024_GEB_Uni Lausanne_20260602.txt"),
]

# 3. Output CSV file name
OUTPUT_FILE = "GENH1S_2021_2024.csv"
# ============================================================

def read_egid_list(csv_path):
    """Read the EGID list from a one‑column CSV (header 'EGID')."""
    egids = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # skip header row
        if header[0].strip() != 'EGID':
            print(f"Warning: First column header is '{header[0]}', expected 'EGID'")
        for row in reader:
            if row:
                egids.append(row[0].strip())
    return egids

def read_genh1s_from_txt(txt_path, year, egid_list=None):
    """
    Read a semicolon‑delimited .txt file.
    Returns a dict {egid: genh1s} for all rows.
    If egid_list is given, only those EGIDs are kept.
    """
    data = {}
    with open(txt_path, 'r', encoding='utf-8') as f:
        # Read header to find column indices
        header = f.readline().rstrip('\n').split(';')
        try:
            egid_idx = header.index('EGID')
            genh1s_idx = header.index('GENH1S')
        except ValueError as e:
            raise ValueError(f"File {txt_path} missing required column: {e}")
        
        for line in f:
            parts = line.rstrip('\n').split(';')
            if len(parts) <= max(egid_idx, genh1s_idx):
                continue  # skip malformed lines (should not happen)
            egid = parts[egid_idx].strip()
            genh1s = parts[genh1s_idx].strip()
            if egid_list is None or egid in egid_list:
                data[egid] = genh1s
    return data

def main():
    # Check that input files exist
    if not Path(EGID_LIST_FILE).exists():
        print(f"ERROR: EGID list file not found: {EGID_LIST_FILE}")
        return
    
    egids = read_egid_list(EGID_LIST_FILE)
    print(f"Loaded {len(egids)} EGIDs.")
    
    # Validate TXT files
    years = []
    txt_paths = []
    for year, path in TXT_FILES:
        if not Path(path).exists():
            print(f"ERROR: File not found: {path} for year {year}")
            return
        years.append(year)
        txt_paths.append(path)
    
    # Extract GENH1S for each year
    year_data = {}  # {year: {egid: genh1s}}
    egid_set = set(egids)  # for fast lookup
    for year, path in zip(years, txt_paths):
        print(f"Reading {year} from {path}...")
        year_data[year] = read_genh1s_from_txt(path, year, egid_set)
        # Verify that all EGIDs are present
        missing = [eg for eg in egids if eg not in year_data[year]]
        if missing:
            print(f"Warning: {len(missing)} EGIDs missing in {year} (first few: {missing[:3]})")
    
    # Write output CSV
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        header = ['EGID'] + [f'GENH1S - {year}' for year in years]
        writer.writerow(header)
        for egid in egids:
            row = [egid]
            for year in years:
                row.append(year_data[year].get(egid, ''))
            writer.writerow(row)
    
    print(f"\nDone! Output saved to {OUTPUT_FILE}")

if __name__ == '__main__':
    main()
