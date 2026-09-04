import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import time
import re
from urllib.parse import quote

CSV_FILE = "vaud_npa_communes.csv"          # NPA,Municipality
OUTPUT_FILE = "chauffage_vaud.xlsx"
DELAY_SECONDS = 1.5                     # polite pause between requests
TIMEOUT = 20

def slugify(npa, name):
    """Build the URL path: <NPA>-<Name> (spaces replaced by hyphens, encoded)."""
    clean = re.sub(r"\s+", "-", name.strip())
    clean = re.sub(r"-{2,}", "-", clean)   # remove double hyphens
    return quote(f"{npa}-{clean}", safe="/-")

def fetch_chauffage_data(url):
    """Return a list of {Programme, Proposé_par} from the Chauffage table, or None."""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        print(f"  HTTP error: {e}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    comp_div = soup.find("div", attrs={"data-svelte-component": "subsidies"})
    if not comp_div:
        print("  Could not find subsidies component div")
        return None

    props_raw = comp_div.get("data-svelte-props")
    if not props_raw:
        print("  No data-svelte-props attribute")
        return None

    try:
        data = json.loads(props_raw)
    except json.JSONDecodeError as e:
        print(f"  JSON decode error: {e}")
        return None

    fields = data.get("town", {}).get("fields", [])
    for field in fields:
        if (field.get("key") == "heizung" and
            field.get("sector") == "building" and
            field.get("kind") == "personal"):
            subsidies = field.get("subsidies", [])
            rows = []
            for sub in subsidies:
                rows.append({
                    "Programme": sub.get("name", ""),
                    "Proposé_par": sub.get("contributor", {}).get("name", "")
                })
            return rows

    return []   # Chauffage section not found, but page loaded fine

def main():
    try:
        df_in = pd.read_csv(CSV_FILE, dtype={"NPA": str})
    except Exception as e:
        print(f"Failed to read {CSV_FILE}: {e}")
        return

    all_rows = []
    for idx, row in df_in.iterrows():
        npa = str(row["NPA"]).zfill(4)
        name = str(row["Municipality"])
        slug = slugify(npa, name)
        url = f"https://www.francsenergie.ch/fr/{slug}/building/personal"
        print(f"[{idx+1}/{len(df_in)}] {npa} {name} → {url}")

        chauff_rows = fetch_chauffage_data(url)
        if chauff_rows is None:
            print("  Skipping due to error")
            continue
        if not chauff_rows:
            print("  No Chauffage subsidies found")
            continue

        for r in chauff_rows:
            r["NPA"] = npa
            r["Municipality"] = name
        all_rows.extend(chauff_rows)
        print(f"  Extracted {len(chauff_rows)} subsidies")

        time.sleep(DELAY_SECONDS)

    if all_rows:
        df_out = pd.DataFrame(all_rows, columns=["NPA", "Municipality", "Programme", "Proposé_par"])
        df_out.to_excel(OUTPUT_FILE, index=False)
        print(f"\nDone! {len(df_out)} rows saved to {OUTPUT_FILE}")
    else:
        print("\nNo data collected.")

if __name__ == "__main__":
    main()
input("Press Enter to exit...")
