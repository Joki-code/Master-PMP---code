import csv
from pathlib import Path

# ==================== USER CONFIGURATION ====================
# Define the years and corresponding .txt files (semicolon separated)
TXT_FILES = [
    (2021, r"x\files\GWS2021_GEB_Uni Lausanne_20260602.txt"),
    (2022, r"x\files\GWS2022_GEB_Uni Lausanne_20260602.txt"),
    (2023, r"xl\files\GWS2023_GEB_Uni Lausanne_20260602.txt"),
    (2024, r"xl\files\GWS2024_GEB_Uni Lausanne_20260602.txt"),
]

# Output CSV file name
OUTPUT_FILE = "GENH1S_2021_2024.csv"
# ============================================================

DELIM = ';'   # semicolon separated


def get_egid_set_and_row_count(filepath):
    """
    Read a semicolon-delimited file and return:
      - set of all EGIDs in the file
      - total number of rows (excluding header)
    """
    egids = set()
    row_count = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=DELIM)
        for row in reader:
            egids.add(row["EGID"].strip())
            row_count += 1
    return egids, row_count


def read_genh1s_for_egids(filepath, egid_set):
    """
    Read the file and return a dict {egid: genh1s} only for EGIDs
    that are in the given set.
    """
    data = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=DELIM)
        # The reader uses the first row as header, so we can access by column name
        for row in reader:
            egid = row["EGID"].strip()
            if egid in egid_set:
                data[egid] = row["GENH1S"].strip()
    return data


def main():
    # Validate that all input files exist
    years = []
    file_paths = []
    for year, path in TXT_FILES:
        if not Path(path).exists():
            print(f"ERROR: File not found: {path} for year {year}")
            return
        years.append(year)
        file_paths.append(path)

    # ---------- Step 1: Find common EGIDs across all files ----------
    all_sets = []
    total_rows_all_files = 0
    file_info = []

    for fpath in file_paths:
        egid_set, row_count = get_egid_set_and_row_count(fpath)
        all_sets.append(egid_set)
        total_rows_all_files += row_count
        file_info.append((fpath, len(egid_set), row_count))
        print(f"{Path(fpath).name}: {row_count} rows, {len(egid_set)} distinct EGIDs")

    common_egids = set.intersection(*all_sets)
    print(f"\nEGIDs present in all four files: {len(common_egids)}")

    # ---------- Step 2: Extract GENH1S for common EGIDs ----------
    year_data = {}  # {year: {egid: genh1s}}
    for year, path in zip(years, file_paths):
        print(f"Reading {year} data for common EGIDs...")
        year_data[year] = read_genh1s_for_egids(path, common_egids)

    # ---------- Step 3: Write output CSV ----------
    with open(OUTPUT_FILE, 'w', encoding='utf-8', newline='') as fout:
        writer = csv.writer(fout)
        header = ['EGID'] + [f'GENH1S - {year}' for year in years]
        writer.writerow(header)

        for egid in sorted(common_egids):   # sorted for readability
            row = [egid]
            for year in years:
                row.append(year_data[year].get(egid, ''))  # should always exist, but keep safe
            writer.writerow(row)

    print(f"Common EGIDs with GENH1S written to {OUTPUT_FILE}")

    # ---------- Step 4: Calculate rows kept / erased (summary) ----------
    rows_retained = 0
    for fpath in file_paths:
        with open(fpath, 'r', encoding='utf-8') as fin:
            reader = csv.DictReader(fin, delimiter=DELIM)
            for row in reader:
                if row["EGID"].strip() in common_egids:
                    rows_retained += 1

    rows_erased = total_rows_all_files - rows_retained
    percent_erased = (rows_erased / total_rows_all_files) * 100 if total_rows_all_files else 0

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total rows across all files     : {total_rows_all_files}")
    print(f"Rows that would be kept (common EGIDs) : {rows_retained}")
    print(f"Rows erased (not in all four)   : {rows_erased} ({percent_erased:.1f}%)")
    print("=" * 50)


if __name__ == "__main__":
    main()
