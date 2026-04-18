import datetime
import io
import json
import os
import random
import zipfile

import pandas as pd
import plotly.express as px
import requests
from dotenv import load_dotenv

# Opt-in to future pandas behavior to silence downcasting warnings
pd.set_option('future.no_silent_downcasting', True)

# ---------------------------------------------------------
# Constants and Configurations
# ---------------------------------------------------------
VALID_STATES = {
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
}

STATE_NAME_TO_ABBR = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
    'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT',
    'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI',
    'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
    'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME',
    'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI',
    'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM',
    'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND',
    'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA',
    'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD',
    'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
    'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC'
}

CENSUS_DIVISIONS = {
    'Pacific': ['CA', 'OR', 'WA', 'HI', 'AK'],
    'West South Central': ['TX', 'OK', 'AR', 'LA'],
    'New England': ['ME', 'NH', 'VT', 'MA', 'RI', 'CT']
}

CENSUS_AHS_MAPPING = {
    '1': ['CT', 'ME', 'MA', 'NH', 'RI', 'VT'],
    '2': ['NJ', 'NY', 'PA'],
    '3': ['IL', 'IN', 'MI', 'OH', 'WI'],
    '4': ['IA', 'KS', 'MN', 'MO', 'NE', 'ND', 'SD'],
    '5': ['DE', 'FL', 'GA', 'MD', 'NC', 'SC', 'VA', 'DC', 'WV'],
    '6': ['AL', 'KY', 'MS', 'TN'],
    '7': ['AR', 'LA', 'OK', 'TX'],
    '8': ['AZ', 'CO', 'ID', 'MT', 'NV', 'NM', 'UT', 'WY'],
    '9': ['AK', 'CA', 'HI', 'OR', 'WA']
}

DIVISION_NAMES = {
    '1': 'New England', '2': 'Middle Atlantic', '3': 'East North Central',
    '4': 'West North Central', '5': 'South Atlantic',
    '6': 'East South Central', '7': 'West South Central',
    '8': 'Mountain', '9': 'Pacific'
}

GITHUB_FONT = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, '
    'Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji"'
)

CSS_STYLES = f"""
    body {{
        font-family: {GITHUB_FONT}; margin: 0; padding: 0;
        background-color: #f9f9f9; color: #24292f;
    }}
    .container {{ padding: 20px; max-width: 1400px; margin: auto; }}
    .container-wide {{
        padding: 20px 40px; max-width: 98%; margin: auto;
        box-sizing: border-box;
    }}
    .map-grid {{
        display: flex; flex-wrap: wrap; justify-content: center;
        gap: 20px; margin-bottom: 20px;
    }}
    .map-box {{
        flex: 1 1 30%; min-width: 300px; background: white;
        padding: 15px; border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); box-sizing: border-box;
    }}
    .chart-row {{
        display: flex; flex-wrap: wrap; justify-content: space-between;
        margin-bottom: 40px; background: white; padding: 20px;
        border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        box-sizing: border-box;
    }}
    .chart-container {{ flex: 0 0 32%; box-sizing: border-box; }}
    @media (max-width: 900px) {{
        .chart-container {{ flex: 0 0 100%; margin-bottom: 20px; }}
    }}
    .nav-menu, .nav-menu ul {{ list-style: none; margin: 0; padding: 0; }}
    .nav-menu {{ background-color: #24292f; display: flex; }}
    .nav-menu > li {{ position: relative; }}
    .nav-menu a {{
        display: block; color: white; padding: 14px 16px;
        text-decoration: none; font-weight: 500;
    }}
    .nav-menu a:hover {{ background-color: #57606a; }}
    .nav-menu ul {{
        display: none; position: absolute; top: 100%; left: 0;
        background-color: #24292f; min-width: 200px; z-index: 1000;
        box-shadow: 0px 8px 16px rgba(0,0,0,0.4);
    }}
    .nav-menu li:hover > ul {{ display: block; }}
    .nav-menu ul ul {{ top: 0; left: 100%; background-color: #32383f; }}

    .tab-container {{
        display: flex; justify-content: center; gap: 10px;
        margin-bottom: 30px;
    }}
    .tab-btn {{
        padding: 10px 20px; cursor: pointer; background-color: #ebecf0;
        border: none; border-radius: 6px; font-size: 15px;
        font-weight: 600; font-family: inherit; color: #57606a;
        transition: 0.2s;
    }}
    .tab-btn:hover {{ background-color: #d0d7de; }}
    .tab-btn.active {{ background-color: #0969da; color: white; }}

    .tabs-wrapper {{ position: relative; width: 100%; }}
    .tab-content {{
        position: absolute; top: 0; left: 0; width: 100%;
        visibility: hidden; opacity: 0; transition: opacity 0.3s;
        z-index: 0;
    }}
    .tab-content.active {{
        position: relative; visibility: visible;
        opacity: 1; z-index: 1;
    }}

    @keyframes smoothLoad {{ 0% {{ opacity: 0; }} 100% {{ opacity: 1; }} }}
    .fade-in-section {{
        opacity: 0; animation: smoothLoad 0.4s ease-out forwards;
        animation-delay: 0.2s;
    }}

    .plotly-graph-div {{ opacity: 0; transition: opacity 0.4s ease-in-out; }}
    .ready .plotly-graph-div {{ opacity: 1 !important; }}

    .toggle-container {{
        margin: 20px 0; display: flex; align-items: center;
        justify-content: center; gap: 10px;
    }}
    .switch {{
        position: relative; display: inline-block;
        width: 50px; height: 26px;
    }}
    .switch input {{ opacity: 0; width: 0; height: 0; }}
    .slider {{
        position: absolute; cursor: pointer; top: 0; left: 0;
        right: 0; bottom: 0; background-color: #ccc;
        transition: .4s; border-radius: 34px;
    }}
    .slider:before {{
        position: absolute; content: ""; height: 18px; width: 18px;
        left: 4px; bottom: 4px; background-color: white;
        transition: .4s; border-radius: 50%;
    }}
    input:checked + .slider {{ background-color: #0969da; }}
    input:checked + .slider:before {{ transform: translateX(24px); }}
    .toggle-label {{ font-size: 14px; font-weight: 600; color: #57606a; }}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>US Buildings Energy Dashboard - {page_title}</title>
    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <style>{css_styles}</style>
</head>
<body>
    {nav_bar_html}
    <div class="container">
        <h1 style="text-align: center;">{page_title} Segment Projections</h1>

        <div class="tab-container">
            <button class="tab-btn" onclick="openTab(event, 'Energy')">
                Energy Use
            </button>
            <button class="tab-btn" onclick="openTab(event, 'PeakDemand')">
                Peak Demand
            </button>
            <button class="tab-btn" onclick="openTab(event, 'Emissions')">
                Emissions
            </button>
            <button class="tab-btn" onclick="openTab(event, 'CapCost')">
                Capital Cost
            </button>
            <button class="tab-btn" onclick="openTab(event, 'EnergyCost')">
                Energy Cost
            </button>
        </div>

        <div class="tabs-wrapper fade-in-section">
            <div id="Energy" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Energy Use (TBtu)
                </h2>
                <div class="chart-row">{energy_charts_html}</div>
            </div>

            <div id="PeakDemand" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Peak Demand (GW)
                </h2>
                <div class="chart-row">{peak_charts_html}</div>
            </div>

            <div id="Emissions" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Emissions (MTCO2e)
                </h2>
                <div class="chart-row">{emissions_charts_html}</div>
            </div>

            <div id="CapCost" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Capital Cost (M$)
                </h2>
                <div class="chart-row">{cap_cost_charts_html}</div>
            </div>

            <div id="EnergyCost" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Energy Cost (M$)
                </h2>
                <div class="chart-row">{energy_cost_charts_html}</div>
            </div>
        </div>
    </div>

    <script>
        var hash = window.location.hash.substring(1);
        var targetMetric = hash ? hash : 'Energy';

        var targetContent = document.getElementById(targetMetric);
        if (targetContent) {{
            targetContent.classList.add("active");
        }}

        var tabLinks = document.getElementsByClassName("tab-btn");
        for (var i = 0; i < tabLinks.length; i++) {{
            if (tabLinks[i].getAttribute('onclick').indexOf(targetMetric) !== -1) {{
                tabLinks[i].classList.add("active");
                break;
            }}
        }}

        function openTab(evt, metricName) {{
            var tabcontent = document.getElementsByClassName("tab-content");
            for (var i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].classList.remove("active");
            }}

            var tablinks = document.getElementsByClassName("tab-btn");
            for (var i = 0; i < tablinks.length; i++) {{
                tablinks[i].classList.remove("active");
            }}

            document.getElementById(metricName).classList.add("active");
            if (evt) {{
                evt.currentTarget.classList.add("active");
            }}

            window.dispatchEvent(new Event('resize'));
        }}

        const ro = new ResizeObserver(entries => {{
            entries.forEach(entry => {{
                const plot = entry.target.querySelector('.plotly-graph-div');
                if (plot && plot.layout) {{
                    Plotly.Plots.resize(plot).then(() => {{
                        entry.target.classList.add('ready');
                    }});
                }}
            }});
        }});

        window.addEventListener('load', function() {{
            document.querySelectorAll('.chart-container').forEach(container => {{
                ro.observe(container);
            }});
        }});
    </script>
</body>
</html>
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>US Buildings Dashboard - Home</title>
    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <style>{css_styles}</style>
</head>
<body>
    {nav_bar_html}
    <div class="container-wide">
        <h1 style="text-align: center; margin-bottom: 20px;">
            US Buildings Current Snapshot
        </h1>

        <div class="toggle-container">
            <span class="toggle-label">Absolute View</span>
            <label class="switch">
                <input type="checkbox" id="mode-toggle" onchange="updateMode()">
                <span class="slider"></span>
            </label>
            <span class="toggle-label">Per Capita View</span>
        </div>

        <div class="fade-in-section">
            <div class="map-grid">
                <div class="map-box" data-tab="Energy">
                    <div class="abs-map">{map_energy}</div>
                    <div class="pc-map" style="display:none">{map_energy_pc}</div>
                </div>
                <div class="map-box" data-tab="PeakDemand">
                    <div class="abs-map">{map_peak}</div>
                    <div class="pc-map" style="display:none">{map_peak_pc}</div>
                </div>
                <div class="map-box" data-tab="Emissions">
                    <div class="abs-map">{map_emissions}</div>
                    <div class="pc-map" style="display:none">{map_emissions_pc}</div>
                </div>
            </div>

            <div class="map-grid">
                <div class="map-box" data-tab="CapCost">
                    <div class="abs-map">{map_capcost}</div>
                    <div class="pc-map" style="display:none">{map_capcost_pc}</div>
                </div>
                <div class="map-box" data-tab="EnergyCost">
                    <div class="abs-map">{map_energycost}</div>
                    <div class="pc-map" style="display:none">{map_energycost_pc}</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function updateMode() {{
            const isPC = document.getElementById('mode-toggle').checked;
            document.querySelectorAll('.abs-map').forEach(
                el => el.style.display = isPC ? 'none' : 'block'
            );
            document.querySelectorAll('.pc-map').forEach(
                el => el.style.display = isPC ? 'block' : 'none'
            );

            const query = isPC ? '.pc-map' : '.abs-map';
            document.querySelectorAll(query).forEach(container => {{
                const plot = container.querySelector('.plotly-graph-div');
                if (plot && plot.layout) {{
                    Plotly.Plots.resize(plot);
                }}
            }});
        }}

        const ro = new ResizeObserver(entries => {{
            entries.forEach(entry => {{
                const plot = entry.target.querySelector('.plotly-graph-div');
                if (plot && plot.layout) {{
                    Plotly.Plots.resize(plot).then(() => {{
                        entry.target.classList.add('ready');
                    }});
                }}
            }});
        }});

        window.addEventListener('load', function() {{
            document.querySelectorAll('.abs-map, .pc-map').forEach(container => {{
                ro.observe(container);

                const checkPlot = setInterval(() => {{
                    const plot = container.querySelector('.plotly-graph-div');
                    if (plot && plot.on) {{
                        clearInterval(checkPlot);
                        plot.on('plotly_click', function(data) {{
                            let state = data.points[0].location;
                            let targetBox = container.closest('.map-box');
                            let targetTab = targetBox.getAttribute('data-tab');
                            window.location.href = state + '.html#' + targetTab;
                        }});
                    }}
                }}, 100);
            }});
        }});
    </script>
</body>
</html>
"""


# ---------------------------------------------------------
# API Handlers
# ---------------------------------------------------------

def fetch_state_population(census_key, target_year):
    """
    Fetches official state populations from Census API, dynamically
    stepping backwards in years to match the most recent EIA data.
    """
    if not census_key:
        print(
            "[WARNING] Census API Key missing. "
            "Using fallback population of 5,000,000."
        )
        return pd.DataFrame([
            {'Region': st, 'Population': 5_000_000} for st in VALID_STATES
        ])

    year = target_year
    while year >= 2021:
        url = f"https://api.census.gov/data/{year}/pep/population"
        params = {"get": f"POP_{year},NAME", "for": "state:*", "key": census_key}
        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                df = pd.DataFrame(data[1:], columns=data[0])
                df.rename(
                    columns={f"POP_{year}": "Population", "NAME": "StateName"},
                    inplace=True
                )
                df['Population'] = pd.to_numeric(df['Population'])
                df['Region'] = df['StateName'].map(STATE_NAME_TO_ABBR)
                print(f"Successfully fetched Census population for {year}.")
                return df[['Region', 'Population']].dropna()
        except Exception:
            pass

        print(f"Census data for {year} unavailable. Trying {year - 1}...")
        year -= 1

    print("[ERROR] Exhausted Census years. Using fallback population.")
    return pd.DataFrame([
        {'Region': st, 'Population': 5_000_000} for st in VALID_STATES
    ])


def find_latest_eia_861_year():
    """
    Finds the latest available EIA-861 data year by dynamically checking
    if the zip file actually exists on the EIA servers.
    """
    year = datetime.datetime.now().year
    headers = {'User-Agent': 'Mozilla/5.0'}
    while year >= 2018:
        urls = [
            f"https://www.eia.gov/electricity/data/eia861/zip/f861{year}.zip",
            f"https://www.eia.gov/electricity/data/eia861/archive/zip/f861{year}.zip"
        ]
        for url in urls:
            try:
                resp = requests.get(url, headers=headers, stream=True, timeout=5)
                with resp as r:
                    if r.status_code == 200:
                        chunk = r.raw.read(2)
                        if chunk == b'PK':
                            return year
            except Exception:
                pass
        year -= 1
    return 2023


def extract_peak_data_zip(year):
    """
    Extracts True Peak Demand directly from the operational_data Excel file.
    """
    urls = [
        f"https://www.eia.gov/electricity/data/eia861/zip/f861{year}.zip",
        "https://www.eia.gov/electricity/data/eia861/archive/zip/"
        f"f861{year}.zip"
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = None
    for url in urls:
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200 and resp.content.startswith(b'PK'):
                r = resp
                break
        except Exception:
            continue

    if r is None:
        return pd.DataFrame(columns=['Region', 'Peak_Demand_GW'])

    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            target = next(
                (f for f in z.namelist() if 'operational_data' in f.lower()
                 and not f.startswith('~')), None
            )
            if not target:
                target = next(
                    (f for f in z.namelist() if 'utility_data' in f.lower()
                     and not f.startswith('~')), None
                )
            if not target:
                return pd.DataFrame(columns=['Region', 'Peak_Demand_GW'])

            df_top = pd.read_excel(z.open(target), header=None, nrows=15)
            mask = df_top.apply(
                lambda row: row.astype(str).str.contains(
                    'Utility Number|Utility ID|Data Year',
                    case=False, na=False
                ).any(), axis=1
            )
            header_start = mask.idxmax()

            df_h = pd.read_excel(
                z.open(target), header=None, skiprows=header_start, nrows=3
            )
            df_h.iloc[0] = df_h.iloc[0].ffill()

            flat_cols = []
            for col_idx in range(len(df_h.columns)):
                combined = "_".join(
                    df_h.iloc[:, col_idx].astype(str)
                    .replace('nan', '').str.lower().str.strip()
                )
                flat_cols.append(combined)

            df_raw = pd.read_excel(
                z.open(target), skiprows=header_start + 3, header=None
            )
            df_raw.columns = flat_cols

            def find_idx(keys):
                for i, h in enumerate(flat_cols):
                    if all(k in h for k in keys):
                        return i
                return None

            idx_st = find_idx(['state'])

            idx_sum = find_idx(['summer', 'peak'])
            if idx_sum is None:
                idx_sum = find_idx(['summer', 'demand'])
            if idx_sum is None:
                idx_sum = find_idx(['summer', 'max'])

            if idx_st is None or idx_sum is None:
                return pd.DataFrame(columns=['Region', 'Peak_Demand_GW'])

            df_peak = pd.DataFrame({
                'State': df_raw.iloc[:, idx_st].astype(str).str.strip().str.upper(),
                'Peak_MW': pd.to_numeric(
                    df_raw.iloc[:, idx_sum], errors='coerce'
                ).fillna(0)
            })

            df_peak = df_peak[df_peak['State'].isin(VALID_STATES)]
            state_peak = df_peak.groupby('State')['Peak_MW'].sum().reset_index()
            state_peak['Peak_Demand_GW'] = state_peak['Peak_MW'] / 1000.0
            state_peak.rename(columns={'State': 'Region'}, inplace=True)

            return state_peak[['Region', 'Peak_Demand_GW']]

    except Exception as e:
        print(f"Error parsing peak zip: {e}")
        return pd.DataFrame(columns=['Region', 'Peak_Demand_GW'])


def fetch_live_home_page_data(eia_key, census_key):
    """
    Pulls live SEDS data via API, extracts Peak Demand from ZIPs,
    matches Census data dynamically, and calculates normalized metrics.
    """
    if not eia_key:
        raise RuntimeError("EIA_API_KEY missing. Cannot fetch live map data.")

    print("Fetching live data from EIA API...")
    try:
        # 1. EIA SEDS (Energy, Emissions, Expenditures)
        # ---------------------------------------------------------
        seds_url = "https://api.eia.gov/v2/seds/data/"
        seds_params = {
            "frequency": "annual",
            "data": ["value"],
            "facets": {
                "seriesId": ["TERCB", "TECCB", "TERCV", "TECCV", "TERCE", "TECCE"]
            },
            "sort": [{"column": "period", "direction": "desc"}],
            "length": 5000
        }

        seds_resp = requests.get(
            seds_url,
            params={"api_key": eia_key},
            headers={"X-Params": json.dumps(seds_params)},
            timeout=20
        )
        if not seds_resp.ok:
            raise RuntimeError(f"SEDS API Error: {seds_resp.text}")

        seds_raw = seds_resp.json().get('response', {}).get('data', [])
        seds_df = pd.DataFrame(seds_raw)

        if not seds_df.empty:
            seds_df.columns = seds_df.columns.str.lower()
            seds_df['seriesid'] = seds_df['seriesid'].astype(str).str.upper()
            seds_df['value'] = pd.to_numeric(seds_df['value'], errors='coerce')
            seds_df = seds_df.sort_values('period', ascending=False)
            seds_df = seds_df.drop_duplicates(
                subset=['stateid', 'seriesid'], keep='first'
            )

            try:
                # Find the most commonly occurring year to sync Census against
                seds_year = int(seds_df['period'].mode()[0])
            except (ValueError, TypeError, IndexError):
                seds_year = 2022

            seds_grouped = (
                seds_df.groupby(['stateid', 'seriesid'])['value']
                .sum().unstack(fill_value=0).reset_index()
            )
            seds_grouped.rename(columns={'stateid': 'Region'}, inplace=True)
            seds_grouped['Region'] = seds_grouped['Region'].str.upper()

            eng_total = (
                seds_grouped.get('TERCB', 0) + seds_grouped.get('TECCB', 0)
            )
            seds_grouped['Energy_Use_TBtu'] = eng_total / 1000

            cost_total = (
                seds_grouped.get('TERCV', 0) + seds_grouped.get('TECCV', 0)
            )
            seds_grouped['Energy_Cost_M$'] = cost_total

            emi_total = (
                seds_grouped.get('TERCE', 0) + seds_grouped.get('TECCE', 0)
            )
            seds_grouped['Emissions_MMTCO2e'] = emi_total
        else:
            seds_year = 2022
            seds_grouped = pd.DataFrame(
                columns=['Region', 'Energy_Use_TBtu', 'Emissions_MMTCO2e',
                         'Energy_Cost_M$']
            )

        # 2. EIA 861 Peak Demand via Zip File Extraction
        # ---------------------------------------------------------
        peak_year = find_latest_eia_861_year()
        print(f"Extracting Peak Demand from EIA-861 zip for {peak_year}...")
        state_peak_df = extract_peak_data_zip(peak_year)

        # 3. Load locally processed Census AHS Division Data
        # ---------------------------------------------------------
        ahs_path = os.path.join('data', 'division_cap_costs.csv')
        expanded_rows = []

        if os.path.exists(ahs_path):
            print("Loading local AHS Capital Cost data...")
            ahs_df = pd.read_csv(ahs_path)
            for _, row in ahs_df.iterrows():

                raw_div = str(
                    row.get('DIVISION', '')
                ).replace("'", "").replace('"', '').strip()
                raw_cost = str(
                    row.get('Capital_Cost_M$', 0)
                ).replace("'", "").replace('"', '').strip()

                try:
                    div_code = str(int(float(raw_div)))
                except ValueError:
                    continue

                try:
                    div_value = float(raw_cost)
                except ValueError:
                    div_value = 0.0

                div_name = DIVISION_NAMES.get(div_code, "Unknown Division")
                states_in_div = CENSUS_AHS_MAPPING.get(div_code, [])

                for st in states_in_div:
                    expanded_rows.append({
                        'Region': st,
                        'Capital_Cost_M$': div_value,
                        'Division_Name': div_name
                    })
        else:
            print("[WARNING] division_cap_costs.csv not found. Skipping AHS.")

        state_cap_df = pd.DataFrame(expanded_rows)

        # 4. Dynamically Fetch Matching Population Data
        # ---------------------------------------------------------
        target_year = max(seds_year, peak_year)
        pop_df = fetch_state_population(census_key, target_year)

        # 5. Merge everything for final output
        # ---------------------------------------------------------
        map_df_all = pd.DataFrame(list(VALID_STATES), columns=['Region'])
        map_df_all = map_df_all.merge(seds_grouped, on='Region', how='left')
        map_df_all = map_df_all.merge(state_peak_df, on='Region', how='left')

        if not state_cap_df.empty:
            map_df_all = map_df_all.merge(
                state_cap_df, on='Region', how='left'
            )
        else:
            map_df_all['Capital_Cost_M$'] = 0.0
            map_df_all['Division_Name'] = "Unknown Division"

        map_df_all = map_df_all.merge(pop_df, on='Region', how='left')
        map_df_all = map_df_all.fillna(0)

        # Ensure Population is safely > 0 for division math
        map_df_all.loc[map_df_all['Population'] == 0, 'Population'] = 1

        # Calculate Normalized Values
        map_df_all['Energy_pc'] = (
            map_df_all['Energy_Use_TBtu'] * 1_000_000
        ) / map_df_all['Population']
        map_df_all['Peak_pc'] = (
            map_df_all['Peak_Demand_GW'] * 1_000_000
        ) / map_df_all['Population']
        map_df_all['Emissions_pc'] = (
            map_df_all['Emissions_MMTCO2e'] * 1_000_000
        ) / map_df_all['Population']
        map_df_all['Cost_pc'] = (
            map_df_all['Energy_Cost_M$'] * 1_000_000
        ) / map_df_all['Population']

        # Normalizing Regional Capital Cost by Regional Population
        div_pop = map_df_all.groupby(
            'Division_Name'
        )['Population'].transform('sum')
        div_pop = div_pop.replace(0, 1)
        map_df_all['CapCost_pc'] = (
            map_df_all['Capital_Cost_M$'] * 1_000_000
        ) / div_pop

        map_df_all = map_df_all[map_df_all['Region'].isin(VALID_STATES)]

        return map_df_all

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API Fetch Request failed entirely: {e}")


def create_dummy_data():
    """Creates dummy dataset strictly for the detail page charts."""
    random.seed(42)
    regions = ['CA', 'TX', 'ME', 'NY', 'FL', 'IL', 'WA']
    years = [2026, 2035, 2050]
    sectors = {
        'Residential': ['SF Home', 'MF Home', 'Mobile Home'],
        'Commercial': [
            'Lg. Office', 'S/M Office', 'Retail', 'Hospitality',
            'Healthcare', 'Education', 'Other', 'Warehouse'
        ]
    }
    branches = [
        ('Electricity', 'Space Heating', 'Heat Pump'),
        ('Electricity', 'Water Heating', 'Heat Pump Water Heater'),
        ('Electricity', 'Lighting', 'LED'),
        ('Electricity', 'HVAC', 'Rooftop Unit'),
        ('Natural Gas', 'Space Heating', 'Gas Boiler'),
        ('Natural Gas', 'Cooking', 'Gas Range'),
        ('Propane', 'Space Heating', 'Propane Furnace'),
        ('Fuel Oil', 'Space Heating', 'Oil Boiler')
    ]

    data = []
    for r in regions:
        for y in years:
            for sector, b_types in sectors.items():
                for b_type in b_types:
                    for fuel, end_use, tech in branches:
                        if sector == 'Residential' and end_use == 'HVAC':
                            continue

                        val = random.randint(5, 50)
                        if fuel in ['Propane', 'Fuel Oil']:
                            val *= 0.15
                        if y == 2035:
                            if fuel in ['Natural Gas', 'Fuel Oil', 'Propane']:
                                val *= 0.7
                            if 'Heat Pump' in tech or tech == 'LED':
                                val *= 1.5
                        elif y == 2050:
                            if fuel in ['Natural Gas', 'Fuel Oil', 'Propane']:
                                val *= 0.2
                            if 'Heat Pump' in tech or tech == 'LED':
                                val *= 3.0

                        val_ex = val * 0.85
                        val_nw = val * 0.15
                        e_fact = 0.5 if fuel == 'Natural Gas' else (
                            0.6 if fuel == 'Propane' else (
                                0.7 if fuel == 'Fuel Oil' else 0.1
                            )
                        )
                        p_fact = 0.2 if fuel == 'Electricity' else 0.0

                        for c_type, v in [('Existing', val_ex), ('New', val_nw)]:
                            data.append([
                                r, y, sector, b_type, fuel, end_use, tech,
                                c_type, round(v, 1), round(v * e_fact, 1),
                                round(v * p_fact, 1), round(v * 1.5, 1),
                                round(v * 0.8, 1)
                            ])

    cols = [
        'Region', 'Year', 'Sector', 'Building_Type', 'Fuel_Type',
        'End_Use', 'Technology', 'Construction_Type', 'Energy_Use_TBtu',
        'Emissions_MMTCO2e', 'Peak_Demand_GW', 'Capital_Cost_M$',
        'Energy_Cost_M$'
    ]
    return pd.DataFrame(data, columns=cols)


# ---------------------------------------------------------
# HTML & Plot Generation Functions
# ---------------------------------------------------------
def generate_navbar_html(divisions_dict):
    """Dynamically builds a nested list dropdown HTML."""
    nav_html = (
        '<ul class="nav-menu">\n'
        '    <li><a href="index.html">Home</a></li>\n'
        '    <li><a href="national.html">National Overview</a></li>\n'
        '    <li>\n'
        '        <a href="#" style="cursor: default;">Select State ▼</a>\n'
        '        <ul>\n'
    )
    for division, states in divisions_dict.items():
        nav_html += (
            f'            <li>\n'
            f'                <a href="#">{division} ▶</a>\n'
            f'                <ul>\n'
        )
        for state in states:
            nav_html += (
                f'                    <li>'
                f'<a href="{state}.html">{state}</a></li>\n'
            )
        nav_html += (
            '                </ul>\n'
            '            </li>\n'
        )
    nav_html += '        </ul>\n    </li>\n</ul>\n'
    return nav_html


def generate_sunburst_row(df_subset, metric_col, path_cols, color_dict=None):
    """Generates 3 Sunbursts using a flexible path and color mapping."""
    row_html = ""
    years = [2026, 2035, 2050]

    df_disp = df_subset.copy()
    for col in path_cols:
        df_disp[col] = df_disp[col].astype(str).str.replace(' ', '<br>')

    for year in years:
        df_year = df_disp[df_disp['Year'] == year]

        if df_year.empty or df_year[metric_col].sum() == 0:
            row_html += (
                f"<div class='chart-container'>"
                f"<p style='text-align:center;'>No {metric_col} "
                f"data for {year}</p></div>"
            )
            continue

        fig = px.sunburst(
            df_year, path=path_cols, values=metric_col,
            color=path_cols[0], color_discrete_map=color_dict,
            title=f"Year {year}"
        )

        fig.update_traces(
            hovertemplate=(
                "<b>%{label}</b><br>"
                f"{metric_col}: %{{value}}<br>"
                "Share of Parent: %{percentParent:.1%}<extra></extra>"
            ),
            marker=dict(line=dict(color='white', width=1.5))
        )

        fig.update_layout(
            font=dict(family=GITHUB_FONT),
            margin=dict(t=30, l=0, r=0, b=0),
            autosize=True, uniformtext=dict(minsize=11, mode='hide')
        )

        chart_div = fig.to_html(
            full_html=False, include_plotlyjs=False,
            default_width='100%', config={'responsive': True}
        )
        row_html += f"<div class='chart-container'>{chart_div}</div>"

    return row_html


# ---------------------------------------------------------
# Main Execution
# ---------------------------------------------------------
def main():
    load_dotenv()
    eia_key = os.environ.get('EIA_API_KEY')
    census_key = os.environ.get('CENSUS_API_KEY')

    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)

    # Fetch strictly live map data
    map_df_all = fetch_live_home_page_data(eia_key, census_key)

    # Note: State Detail pages still use synthetic dummy data
    df = create_dummy_data()
    dynamic_navbar = generate_navbar_html(CENSUS_DIVISIONS)

    std_path = [
        'Fuel_Type', 'End_Use', 'Technology',
        'Building_Type', 'Construction_Type'
    ]
    std_colors = {
        'Electricity': '#19D3F3', 'Natural<br>Gas': '#FFA15A',
        'Propane': '#B6E880', 'Fuel<br>Oil': '#FF97FF'
    }

    peak_path = ['End_Use', 'Technology', 'Building_Type', 'Construction_Type']
    peak_colors = {
        'Space<br>Heating': '#EF553B', 'Water<br>Heating': '#00CC96',
        'Lighting': '#AB63FA', 'HVAC': '#1F77B4'
    }

    def build_page_html(data_slice, page_title):
        html_eng = generate_sunburst_row(
            data_slice, 'Energy_Use_TBtu', std_path, std_colors)
        html_emi = generate_sunburst_row(
            data_slice, 'Emissions_MMTCO2e', std_path, std_colors)
        html_cap = generate_sunburst_row(
            data_slice, 'Capital_Cost_M$', std_path, std_colors)
        html_enc = generate_sunburst_row(
            data_slice, 'Energy_Cost_M$', std_path, std_colors)

        peak_df = data_slice[data_slice['Fuel_Type'] == 'Electricity']
        html_peak = generate_sunburst_row(
            peak_df, 'Peak_Demand_GW', peak_path, peak_colors)

        return HTML_TEMPLATE.format(
            css_styles=CSS_STYLES, nav_bar_html=dynamic_navbar,
            page_title=page_title, energy_charts_html=html_eng,
            emissions_charts_html=html_emi, peak_charts_html=html_peak,
            cap_cost_charts_html=html_cap, energy_cost_charts_html=html_enc
        )

    print("Generating National view...")
    with open(os.path.join(output_dir, "national.html"), "w") as f:
        f.write(build_page_html(df, "National"))

    for state in df['Region'].unique():
        print(f"Generating view for {state}...")
        state_df = df[df['Region'] == state]
        with open(os.path.join(output_dir, f"{state}.html"), "w") as f:
            f.write(build_page_html(state_df, state))

    print("Generating Multi-Panel Home page...")
    if not map_df_all.empty:

        def generate_map_panel(data, metric, title, is_ahs=False, fmt=",.1f"):
            fig = px.choropleth(
                data, locations='Region', locationmode="USA-states",
                color=metric, scope="usa", title=title,
                color_continuous_scale="Teal"
            )

            # Add clean white borders
            fig.update_traces(marker_line_color='white', marker_line_width=1.0)

            # Format hover labels to cleanly denote Census Divisions for AHS data
            if is_ahs and 'Division_Name' in data.columns:
                fig.update_traces(
                    customdata=data[['Division_Name']],
                    hovertemplate=(
                        "<b>%{location} (%{customdata[0]})</b><br>" +
                        title + ": %{z:" + fmt + "}<extra></extra>")
                )
            else:
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{location}</b><br>" +
                        title + ": %{z:" + fmt + "}<extra></extra>")
                )

            fig.update_layout(
                font=dict(family=GITHUB_FONT, size=12),
                margin=dict(t=40, l=0, r=0, b=0),
                coloraxis_colorbar=dict(title=None, thickness=10, len=0.7),
                autosize=True
            )
            return fig.to_html(
                full_html=False, include_plotlyjs=False,
                default_width='100%', default_height='400px',
                config={'responsive': True}
            )

        # Standard Absolute Data Maps
        map_eng = generate_map_panel(
            map_df_all, 'Energy_Use_TBtu', "Energy Use (TBtu)"
        )
        map_peak = generate_map_panel(
            map_df_all, 'Peak_Demand_GW', "Peak Demand (GW)"
        )
        map_emi = generate_map_panel(
            map_df_all, 'Emissions_MMTCO2e', "Emissions (MMTCO2e)"
        )
        map_cap = generate_map_panel(
            map_df_all, 'Capital_Cost_M$', "Capital Expenditures (M$)",
            is_ahs=True
        )
        map_enc = generate_map_panel(
            map_df_all, 'Energy_Cost_M$', "Energy Cost (M$)"
        )

        # Per Capita Data Maps
        map_eng_pc = generate_map_panel(
            map_df_all, 'Energy_pc', "Energy (MMBtu/Capita)", fmt=",.0f"
        )
        map_peak_pc = generate_map_panel(
            map_df_all, 'Peak_pc', "Peak Demand (kW/Capita)", fmt=",.2f"
        )
        map_emi_pc = generate_map_panel(
            map_df_all, 'Emissions_pc', "Emissions (MTCO2e/Capita)", fmt=",.1f"
        )
        map_cap_pc = generate_map_panel(
            map_df_all, 'CapCost_pc', "CapEx ($/Capita)",
            is_ahs=True, fmt="$,.0f"
        )
        map_enc_pc = generate_map_panel(
            map_df_all, 'Cost_pc', "Energy Cost ($/Capita)", fmt="$,.0f"
        )

        final_idx_html = INDEX_TEMPLATE.format(
            css_styles=CSS_STYLES, nav_bar_html=dynamic_navbar,
            map_energy=map_eng, map_energy_pc=map_eng_pc,
            map_peak=map_peak, map_peak_pc=map_peak_pc,
            map_emissions=map_emi, map_emissions_pc=map_emi_pc,
            map_capcost=map_cap, map_capcost_pc=map_cap_pc,
            map_energycost=map_enc, map_energycost_pc=map_enc_pc
        )

        with open(os.path.join(output_dir, "index.html"), "w") as f:
            f.write(final_idx_html)
        print("All pages generated successfully!")
    else:
        print("Failed to generate index.html. Dataframe was empty.")


if __name__ == "__main__":
    main()
