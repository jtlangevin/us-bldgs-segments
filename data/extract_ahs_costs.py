import os

import pandas as pd


def extract_capital_costs():
    """
    Reads raw AHS microdata, filters for specific building upgrades,
    calculates weighted totals, and exports division-level summary.
    """
    print("Starting AHS Microdata Extraction...\n")

    base_file = os.path.join('data', 'household.csv')
    homimp_file = os.path.join('data', 'project.csv')
    output_file = os.path.join('data', 'division_cap_costs.csv')

    if not os.path.exists(base_file) or not os.path.exists(homimp_file):
        print(
            "ERROR: AHS PUF CSVs not found. Please ensure 'household.csv' "
            "and 'project.csv' are placed in the 'data/' folder."
        )
        return

    # --- 1. Dynamically Identify Columns ---
    hh_headers = pd.read_csv(base_file, nrows=0).columns.str.upper()
    proj_headers = pd.read_csv(homimp_file, nrows=0).columns.str.upper()

    # Find Weight (Substring match)
    weight_col = next(
        (c for c in hh_headers if 'WEIGHT' in c or 'WGT' in c), None
    )
    # Explicitly ignore imputation flag columns starting with 'J'
    valid_proj_cols = [c for c in proj_headers if not c.startswith('JJOB')]
    # Find Cost (Substring match for any amount or cost column in valid columns)
    cost_col = next(
        (c for c in valid_proj_cols if 'AMNT' in c or 'COST' in c or 'AMT' in c),
        None
    )
    # Find Type (Substring match in valid columns)
    jobtype_col = next(
        (c for c in valid_proj_cols if 'TYPE' in c or 'TYP' in c or 'JOB' in c),
        None
    )

    if not all([weight_col, cost_col, jobtype_col]):
        print(
            f"ERROR: Missing columns.\n"
            f"Found Weight: {weight_col}, Cost: {cost_col}, "
            f"Type: {jobtype_col}\n"
        )
        print("Here are the columns actually found in project.csv:")
        print(list(proj_headers[:30]))  # Print first 30 to debug
        return

    print(f"Auto-detected Cost Column:   '{cost_col}'")
    print(f"Auto-detected Type Column:   '{jobtype_col}'")
    print(f"Auto-detected Weight Column: '{weight_col}'\n")

    # --- 2. Load the Files ---
    base_df = pd.read_csv(
        base_file,
        usecols=lambda x: x.upper() in ['CONTROL', 'DIVISION', weight_col]
    )
    base_df.columns = base_df.columns.str.upper()
    base_df.rename(columns={weight_col: 'WEIGHT'}, inplace=True)

    imp_df = pd.read_csv(
        homimp_file,
        usecols=lambda x: x.upper() in ['CONTROL', jobtype_col, cost_col]
    )
    imp_df.columns = imp_df.columns.str.upper()
    imp_df.rename(
        columns={jobtype_col: 'JOBTYPE', cost_col: 'JOBAMNT'}, inplace=True
    )

    print(f"Loaded {len(base_df):,} households and {len(imp_df):,} projects.")

    # --- 3. Clean Data Types & Strip Quotes ---
    base_df['CONTROL'] = (
        base_df['CONTROL'].astype(str)
        .str.replace("'", "").str.replace('"', '').str.strip()
    )
    imp_df['CONTROL'] = (
        imp_df['CONTROL'].astype(str)
        .str.replace("'", "").str.replace('"', '').str.strip()
    )

    imp_df['JOBTYPE'] = pd.to_numeric(
        imp_df['JOBTYPE'].astype(str).str.replace("'", ""), errors='coerce'
    )
    imp_df['JOBAMNT'] = pd.to_numeric(
        imp_df['JOBAMNT'].astype(str).str.replace("'", ""), errors='coerce'
    )

    # --- 4. Filter for Specific Jobs ---
    target_jobs = [
        11, 12, 13, 14,  # Envelope (Roof, Siding, Doors/Windows, Insulation)
        21, 22,          # HVAC (Central AC, Heating Equipment)
        31, 32,          # Plumbing (Pipes, Water Heater)
        33,              # Electrical Wiring
        43               # Major Appliances
    ]

    filtered_imp = imp_df[imp_df['JOBTYPE'].isin(target_jobs)].copy()
    filtered_imp = filtered_imp[filtered_imp['JOBAMNT'] > 0]

    print(
        f"Filtered down to {len(filtered_imp):,} target building "
        "upgrade projects."
    )

    # --- 5. Merge and Calculate Weighted Costs ---
    merged_df = pd.merge(filtered_imp, base_df, on='CONTROL', how='inner')
    print(
        f"Successfully matched {len(merged_df):,} projects to "
        "their household weights."
    )

    if merged_df.empty:
        print("\n[WARNING] Merge resulted in 0 rows. The CSV will be empty.")
        return

    merged_df['weighted_cost'] = merged_df['JOBAMNT'] * merged_df['WEIGHT']

    # --- 6. Aggregate by Census Division ---
    div_summary = (
        merged_df.groupby('DIVISION')['weighted_cost'].sum().reset_index()
    )

    # Convert total dollars to Millions of Dollars (M$)
    div_summary['Capital_Cost_M$'] = div_summary['weighted_cost'] / 1_000_000

    # Strip any decimal points from the division numbers
    div_summary['DIVISION'] = (
        div_summary['DIVISION'].astype(str).str.replace('.0', '', regex=False)
    )
    div_summary = div_summary[['DIVISION', 'Capital_Cost_M$']]

    # Export
    os.makedirs('data', exist_ok=True)
    div_summary.to_csv(output_file, index=False)
    print(f"\nExtraction complete! Saved to {output_file}")
    print(div_summary.head(9))


if __name__ == "__main__":
    extract_capital_costs()
