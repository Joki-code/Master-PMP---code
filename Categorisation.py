import pandas as pd

# ------------------------------------------------------------
# 1. Load your CSV file (adjust the path)
# ------------------------------------------------------------
input_file = r'v'
output_file = r''   # output file
import pandas as pd

df = pd.read_csv(input_file)

# ------------------------------------------------------------
# 2. New categorization function
# ------------------------------------------------------------
def new_categorize(c2021, c2022, c2023, c2024):
    values = [c2021, c2022, c2023, c2024]
    
    # Helper: find first non-99 index and value
    first_non_99 = None
    for i, v in enumerate(values):
        if v != 99:
            first_non_99 = (i, v)
            break
    
    # Case: all 99
    if first_non_99 is None:
        return 99   # all four 99 -> ANOMALIES
    
    start_idx, start_val = first_non_99
    
    # Case: C4 is 99 and effective start is 0 or 1
    if c2024 == 99 and start_val in (0, 1):
        return 98   # UNKNOWN
    
    # Check contiguity of 99s: after first non-99, there should be no 99 later
    # Actually, contiguity means all 99s appear only before the first non-99.
    # If any 99 appears after a non-99, it's non-contiguous -> anomalies.
    for j in range(start_idx + 1, 4):
        if values[j] == 99:
            return 99   # ANOMALIES (non-contiguous 99s)
    
    # Now we have contiguous 99s at the beginning (possibly none), and no 99 after start.
    # Also C4 is not 99 (otherwise already caught).
    
    # Determine if there is any 99 at all
    has_99 = any(v == 99 for v in values)
    
    if not has_99:
        # No 99s at all
        if all(v == 0 for v in values):
            return 0
        if all(v == 1 for v in values):
            return 2
        if c2021 == 0 and c2024 == 1:
            return 1
        if c2021 == 1 and c2024 == 0:
            return 3
        # Should not happen per rules, but fallback
        return 99
    else:
        # Has contiguous leading 99s (one or more), and C4 != 99
        if start_val == 0 and c2024 == 0:
            return 0
        if start_val == 1 and c2024 == 1:
            return 2
        if start_val == 0 and c2024 == 1:
            return 1
        if start_val == 1 and c2024 == 0:
            return 3
        # If none matched, anomalies
        return 99

# ------------------------------------------------------------
# 3. Apply the new function
# ------------------------------------------------------------
df['category'] = df.apply(
    lambda row: new_categorize(
        row['Clean - 2021'],
        row['Clean - 2022'],
        row['Clean - 2023'],
        row['Clean - 2024']
    ), axis=1
)

# ------------------------------------------------------------
# 4. Save result
# ------------------------------------------------------------
df.to_csv(output_file, index=False)
print(f"✅ Updated category column saved to: {output_file}")

# Optional preview
print("\nFirst 10 rows (Clean columns + new category):")
preview_cols = ['Clean - 2021', 'Clean - 2022', 'Clean - 2023', 'Clean - 2024', 'category']
print(df[preview_cols].head(10))
