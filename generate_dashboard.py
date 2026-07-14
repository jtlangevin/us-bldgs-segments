import datetime
import io
import json
import os
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
# Excludes 'AK' and 'HI' for now
VALID_STATES = {
    'AL', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
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
    'New England': ['CT', 'ME', 'MA', 'NH', 'RI', 'VT'],
    'Middle Atlantic': ['NJ', 'NY', 'PA'],
    'East North Central': ['IL', 'IN', 'MI', 'OH', 'WI'],
    'West North Central': ['IA', 'KS', 'MN', 'MO', 'NE', 'ND', 'SD'],
    'South Atlantic': ['DE', 'FL', 'GA', 'MD', 'NC', 'SC', 'VA', 'DC', 'WV'],
    'East South Central': ['AL', 'KY', 'MS', 'TN'],
    'West South Central': ['AR', 'LA', 'OK', 'TX'],
    'Mountain': ['AZ', 'CO', 'ID', 'MT', 'NV', 'NM', 'UT', 'WY'],
    'Pacific': ['CA', 'OR', 'WA']
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
    '9': ['CA', 'OR', 'WA']
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
    .nav-menu li {{ position: relative; }}
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

    /* CSS GRID FOR PERFECT ZERO-SNAP LAYOUTS */
    .tabs-wrapper, .stack-grid {{
        display: grid;
        grid-template-columns: 1fr;
        width: 100%;
    }}
    .tab-content, .stack-layer {{
        grid-row: 1;
        grid-column: 1;
        visibility: hidden;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.3s ease;
        z-index: 0;
        min-width: 0; /* Prevents grid blowout */
    }}
    .tab-content.active, .stack-layer.active-layer {{
        visibility: visible;
        opacity: 1;
        pointer-events: auto;
        z-index: 1;
    }}

    @keyframes smoothLoad {{
        0% {{ opacity: 0; }}
        100% {{ opacity: 1; }}
    }}
    .fade-in-section {{
        opacity: 0; animation: smoothLoad 0.4s ease-out forwards;
        animation-delay: 0.2s;
    }}

    .plotly-graph-div {{ opacity: 0; transition: opacity 0.4s ease-in-out; }}
    .ready .plotly-graph-div {{ opacity: 1 !important; }}

    /* SEGMENTED CONTROLS FOR FILTERS */
    .segmented-control {{
        display: inline-flex;
        background-color: #ebecf0;
        border-radius: 6px;
        padding: 4px;
    }}
    .segmented-control input[type="radio"] {{
        display: none;
    }}
    .segmented-control label {{
        padding: 6px 16px;
        cursor: pointer;
        border-radius: 4px;
        font-size: 14px;
        font-weight: 500;
        color: #57606a;
        transition: background-color 0.2s, color 0.2s;
        margin: 0;
    }}
    .segmented-control input[type="radio"]:checked + label {{
        background-color: #ffffff;
        color: #24292f;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}

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

    /* ANTI-SNAP CSS CLASSES FOR MAP AND CHART TOGGLES */
    .map-hidden {{
        height: 0; overflow: hidden; opacity: 0;
        pointer-events: none; visibility: hidden;
    }}
    .map-visible {{
        height: auto; opacity: 1;
        pointer-events: auto; visibility: visible;
    }}

    /* LOADING SPINNER */
    #loader-overlay {{
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: #f9f9f9; z-index: 9999;
        display: flex; flex-direction: column; justify-content: center;
        align-items: center; transition: opacity 0.4s ease;
    }}
    .spinner {{
        border: 6px solid #ebecf0; border-top: 6px solid #0969da;
        border-radius: 50%; width: 50px; height: 50px;
        animation: spin 1s linear infinite;
    }}
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}
    .loader-hidden {{ opacity: 0; pointer-events: none; }}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>US Buildings Energy Dashboard - {page_title}</title>

    <script async src="https://www.googletagmanager.com/gtag/js?id=G-K7XJSGS9GG"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());

      gtag('config', 'G-K7XJSGS9GG');
    </script>

    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <style>{css_styles}</style>
</head>
<body>
    <div id="loader-overlay">
        <div class="spinner"></div>
        <h2 style="color: #57606a; margin-top: 20px; font-weight: 400;">
            Loading Projections...
        </h2>
    </div>

    {nav_bar_html}
    <div class="container">
        <h1 style="text-align: center;">{page_title} Segment Projections</h1>

        <div class="tab-container">
            <button class="tab-btn" onclick="openTab(event, 'Energy')">
                Site Energy Use
            </button>
            <button class="tab-btn"
                    onclick="openTab(event, 'PeakDemand_Summer')">
                Summer Peak
            </button>
            <button class="tab-btn"
                    onclick="openTab(event, 'PeakDemand_Winter')">
                Winter Peak
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

        <p style="text-align: center; font-size: 13px; color: #57606a; margin-top: -15px;
        margin-bottom: 30px;">
            All projections are drawn from the
            <a href="https://github.com/scout-bto/scout/tree/pathways-2026"
            target="_blank" style="color: #0969da; text-decoration: none;">Scout baseline</a>
            and reflect the <a href="https://www.eia.gov/outlooks/aeo/"
            target="_blank" style="color: #0969da; text-decoration: none;
            ">Annual Energy Outlook 2026 Reference Case forecast</a>.
        </p>

        <div class="tabs-wrapper fade-in-section">
            <div id="Energy" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Site Energy Use (TBtu)
                </h2>
                <div class="chart-row">{energy_charts_html}</div>
            </div>

            <div id="PeakDemand_Summer" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Peak Demand, Summer (GW)
                </h2>
                <div class="chart-row">{summer_peak_charts_html}</div>
            </div>

            <div id="PeakDemand_Winter" class="tab-content">
                <h2 id="WinterPeakAnchor"
                    style="text-align: center; font-weight: 400;
                    margin-top: 40px;">
                    Peak Demand, Winter (GW)
                </h2>
                <div class="chart-row">{winter_peak_charts_html}</div>
            </div>

            <div id="Emissions" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Emissions (CO2e)
                </h2>
                <div class="chart-row">{emissions_charts_html}</div>
            </div>

            <div id="CapCost" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Capital Cost (Bn.$)
                </h2>
                <div class="chart-row">{cap_cost_charts_html}</div>
            </div>

            <div id="EnergyCost" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">
                    Energy Cost (Bn.$)
                </h2>
                <div class="chart-row">{energy_cost_charts_html}</div>
            </div>
        </div>
    </div>

    <script>
        var hash = window.location.hash.substring(1);
        var targetMetric = hash ? hash : 'Energy';
        var scrollToId = null;

        var targetContent = document.getElementById(targetMetric);
        if (targetContent) {{
            targetContent.classList.add("active");
        }}

        var tabLinks = document.getElementsByClassName("tab-btn");
        for (var i = 0; i < tabLinks.length; i++) {{
            if (tabLinks[i].getAttribute('onclick')
                    .indexOf(targetMetric) !== -1) {{
                tabLinks[i].classList.add("active");
                break;
            }}
        }}

        function renderVisibleCharts() {{
            const activeScripts = document.querySelectorAll(
                '.tab-content.active .active-layer script.lazy-plotly'
            );
            activeScripts.forEach(template => {{
                // Skip if hidden by the Year/Combined filters
                const plotContainer = template.closest(
                    '.thermal-plot-container'
                );
                if (plotContainer &&
                    plotContainer.style.display === 'none') return;

                const script = document.createElement('script');
                script.textContent = template.textContent;
                document.body.appendChild(script);
                template.classList.remove('lazy-plotly');
                template.type = "text/executed";

                const container = template.closest('.chart-container');
                if (container) {{
                    setTimeout(() => container.classList.add('ready'), 50);
                }}
            }});

            setTimeout(() => {{
                document.querySelectorAll(
                    '.tab-content.active .active-layer .plotly-graph-div'
                ).forEach(plot => {{
                    const plotContainer = plot.closest(
                        '.thermal-plot-container'
                    );
                    if (plotContainer &&
                        plotContainer.style.display === 'none') return;

                    if (plot && plot.layout) {{
                        Plotly.Plots.resize(plot);
                    }}
                }});
            }}, 100);
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

            renderVisibleCharts();
        }}

        function updateSunburstFilters(element) {{
            const container = element.closest('.tab-content');

            const hierChecked = container.querySelector(
                'input[name^="hierarchy-"]:checked'
            );
            const hierarchy = hierChecked ? hierChecked.value : 'fuel';

            const sectorChecked = container.querySelector(
                'input[name^="sector-"]:checked'
            );
            const sector = sectorChecked ? sectorChecked.value : 'all';

            const unknownChecked = container.querySelector(
                'input[name^="unknown-"]:checked'
            );
            const unknown = unknownChecked ? unknownChecked.value : 'inc';

            const targetClass = 'view-' + hierarchy + '-' + sector + '-'
                                + unknown;

            container.querySelectorAll('.sunburst-view').forEach(el => {{
                if (el.classList.contains(targetClass)) {{
                    el.classList.add('active-layer');
                }} else {{
                    el.classList.remove('active-layer');
                }}
            }});

            renderVisibleCharts();
        }}

        function scrollToThermal(el) {{
            const tab = el.closest('.tab-content');
            if (!tab) return;
            const activeLayer = tab.querySelector('.active-layer');
            if (!activeLayer) return;
            const thermalWrapper = activeLayer.querySelector('[id^="thermal-wrapper-"]');
            if (thermalWrapper) {{
                thermalWrapper.scrollIntoView({{behavior: 'smooth', block: 'start'}});
            }}
        }}

        function updateThermalView(viewId) {{
            const viewType = document.querySelector(
                `input[name='env-view-${{viewId}}']:checked`
            ).value;
            const year = document.querySelector(
                `input[name='env-year-${{viewId}}']:checked`
            ).value;

            const containers = document.querySelectorAll(
                `#thermal-wrapper-${{viewId}} .thermal-plot-container`
            );
            containers.forEach(c => {{
                if (c.dataset.year === year && c.dataset.view === viewType) {{
                    c.style.display = 'flex';
                }} else {{
                    c.style.display = 'none';
                }}
            }});
            renderVisibleCharts();
        }}

        const ro = new ResizeObserver(entries => {{
            entries.forEach(entry => {{
                if (!entry.target.closest('.active-layer')) return;
                const plot = entry.target.querySelector('.plotly-graph-div');
                if (plot && plot.layout) {{
                    Plotly.Plots.resize(plot);
                }}
            }});
        }});

        window.addEventListener('load', function() {{
            const loader = document.getElementById('loader-overlay');
            if (loader) {{
                loader.classList.add('loader-hidden');
                setTimeout(() => loader.style.display = 'none', 400);
            }}

            renderVisibleCharts();

            document.querySelectorAll('.chart-container').forEach(
                container => {{
                    ro.observe(container);
                }}
            );

            if (typeof scrollToId !== 'undefined' && scrollToId) {{
                setTimeout(() => {{
                    var el = document.getElementById(scrollToId);
                    if (el) el.scrollIntoView({{behavior: 'smooth'}});
                }}, 600);
            }}
        }});
    </script>
</body>
</html>
"""

INDEX_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>US Buildings Dashboard - Home</title>

    <script async src="https://www.googletagmanager.com/gtag/js?id=G-K7XJSGS9GG"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());

      gtag('config', 'G-K7XJSGS9GG');
    </script>

    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <style>{css_styles}</style>
</head>
<body>
    <div id="loader-overlay">
        <div class="spinner"></div>
        <h2 style="color: #57606a; margin-top: 20px; font-weight: 400;">
            Loading Snapshot...
        </h2>
    </div>

    {nav_bar_html}
    <div class="container-wide">
        <h1 style="text-align: center; margin-bottom: 20px;">
            US Buildings Current Snapshot
        </h1>

        <div class="toggle-container">
            <span class="toggle-label">Absolute View</span>
            <label class="switch">
                <input type="checkbox" id="mode-toggle"
                       onchange="updateMode()">
                <span class="slider"></span>
            </label>
            <span class="toggle-label">Per Capita View</span>
        </div>

        <div class="fade-in-section">
            <div class="map-grid">
                <div class="map-box" data-tab="Energy">
                    <div class="stack-grid">
                        <div class="abs-map stack-layer active-layer">
                            {map_energy}
                        </div>
                        <div class="pc-map stack-layer">
                            {map_energy_pc}
                        </div>
                    </div>
                </div>
                <div class="map-box" data-tab="PeakDemand_Summer">
                    <div class="stack-grid">
                        <div class="abs-map stack-layer active-layer">
                            {map_summer_peak}
                        </div>
                        <div class="pc-map stack-layer">
                            {map_summer_peak_pc}
                        </div>
                    </div>
                </div>
                <div class="map-box" data-tab="PeakDemand_Winter">
                    <div class="stack-grid">
                        <div class="abs-map stack-layer active-layer">
                            {map_winter_peak}
                        </div>
                        <div class="pc-map stack-layer">
                            {map_winter_peak_pc}
                        </div>
                    </div>
                </div>
            </div>

            <div class="map-grid">
                <div class="map-box" data-tab="Emissions">
                    <div class="stack-grid">
                        <div class="abs-map stack-layer active-layer">
                            {map_emissions}
                        </div>
                        <div class="pc-map stack-layer">
                            {map_emissions_pc}
                        </div>
                    </div>
                </div>
                <div class="map-box" data-tab="CapCost">
                    <div class="stack-grid">
                        <div class="abs-map stack-layer active-layer">
                            {map_capcost}
                        </div>
                        <div class="pc-map stack-layer">
                            {map_capcost_pc}
                        </div>
                    </div>
                </div>
                <div class="map-box" data-tab="EnergyCost">
                    <div class="stack-grid">
                        <div class="abs-map stack-layer active-layer">
                            {map_energycost}
                        </div>
                        <div class="pc-map stack-layer">
                            {map_energycost_pc}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        function renderVisibleCharts() {{
            const activeScripts = document.querySelectorAll(
                '.active-layer script.lazy-plotly'
            );
            activeScripts.forEach(template => {{
                const script = document.createElement('script');
                script.textContent = template.textContent;
                document.body.appendChild(script);
                template.classList.remove('lazy-plotly');
                template.type = "text/executed";

                const container = template.closest('.stack-layer');
                if (container) {{
                    setTimeout(() => container.classList.add('ready'), 50);
                }}
            }});

            setTimeout(() => {{
                document.querySelectorAll(
                    '.active-layer .plotly-graph-div'
                ).forEach(plot => {{
                    if (plot && plot.layout) {{
                        Plotly.Plots.resize(plot);
                    }}
                }});
            }}, 100);
        }}

        function updateMode() {{
            const isPC = document.getElementById('mode-toggle').checked;

            document.querySelectorAll('.abs-map').forEach(el => {{
                if (isPC) {{
                    el.classList.remove('active-layer');
                }} else {{
                    el.classList.add('active-layer');
                }}
            }});
            document.querySelectorAll('.pc-map').forEach(el => {{
                if (isPC) {{
                    el.classList.add('active-layer');
                }} else {{
                    el.classList.remove('active-layer');
                }}
            }});

            renderVisibleCharts();
        }}

        const ro = new ResizeObserver(entries => {{
            entries.forEach(entry => {{
                if (!entry.target.classList.contains('active-layer')) return;
                const plot = entry.target.querySelector('.plotly-graph-div');
                if (plot && plot.layout) {{
                    Plotly.Plots.resize(plot);
                }}
            }});
        }});

        window.addEventListener('load', function() {{
            const loader = document.getElementById('loader-overlay');
            if (loader) {{
                loader.classList.add('loader-hidden');
                setTimeout(() => loader.style.display = 'none', 400);
            }}

            renderVisibleCharts();

            document.querySelectorAll('.stack-layer').forEach(container => {{
                ro.observe(container);

                const checkPlot = setInterval(() => {{
                    const plot = container.querySelector('.plotly-graph-div');
                    if (plot && plot.on) {{
                        clearInterval(checkPlot);
                        plot.on('plotly_click', function(data) {{
                            let state = data.points[0].location;
                            let targetBox = container.closest('.map-box');
                            let targetTab = targetBox.getAttribute('data-tab');
                            window.location.href = state + '.html#'
                                + targetTab;
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
        params = {
            "get": f"POP_{year},NAME",
            "for": "state:*",
            "key": census_key
        }
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
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
    }
    while year >= 2018:
        urls = [
            f"https://www.eia.gov/electricity/data/eia861/zip/f861{year}.zip",
            f"https://www.eia.gov/electricity/data/eia861/archive/zip/"
            f"f861{year}.zip"
        ]
        for url in urls:
            try:
                resp = requests.get(
                    url, headers=headers, stream=True, timeout=15
                )
                if resp.status_code == 200:
                    chunk = next(resp.iter_content(chunk_size=2), b'')
                    if chunk == b'PK':
                        return year
            except requests.exceptions.RequestException:
                pass
        year -= 1
    return 2024


def extract_peak_data_zip(year):
    """
    Extracts True Peak Demand directly from the operational_data Excel file,
    filtering out entities that would result in double-counting load.
    """
    urls = [
        f"https://www.eia.gov/electricity/data/eia861/zip/f861{year}.zip",
        f"https://www.eia.gov/electricity/data/eia861/archive/zip/"
        f"f861{year}.zip"
    ]
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
    }
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
        return pd.DataFrame(columns=[
            'Region', 'Summer_Peak_Demand_GW', 'Winter_Peak_Demand_GW'
        ])

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
                return pd.DataFrame(columns=[
                    'Region', 'Summer_Peak_Demand_GW', 'Winter_Peak_Demand_GW'
                ])

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
            idx_name = find_idx(['utility', 'name'])
            idx_ent = find_idx(['entity'])

            if idx_ent is None:
                idx_ent = find_idx(['ownership'])

            idx_sum = find_idx(['summer', 'peak'])
            if idx_sum is None:
                idx_sum = find_idx(['summer', 'demand'])
            if idx_sum is None:
                idx_sum = find_idx(['summer', 'max'])

            idx_win = find_idx(['winter', 'peak'])
            if idx_win is None:
                idx_win = find_idx(['winter', 'demand'])
            if idx_win is None:
                idx_win = find_idx(['winter', 'max'])

            if idx_st is None or idx_sum is None:
                return pd.DataFrame(columns=[
                    'Region', 'Summer_Peak_Demand_GW', 'Winter_Peak_Demand_GW'
                ])

            st_s = df_raw.iloc[:, idx_st].astype(str).str.strip().str.upper()
            ent_s = (
                df_raw.iloc[:, idx_ent].astype(str).str.lower()
                if idx_ent is not None else ''
            )
            nm_s = (
                df_raw.iloc[:, idx_name].astype(str).str.lower()
                if idx_name is not None else ''
            )

            s_mw = pd.to_numeric(df_raw.iloc[:, idx_sum], errors='coerce')
            w_mw = pd.to_numeric(
                df_raw.iloc[:, idx_win], errors='coerce'
            ) if idx_win is not None else pd.Series(0, index=df_raw.index)

            df_peak = pd.DataFrame({
                'State': st_s,
                'Utility_Name': nm_s,
                'Entity': ent_s,
                'Summer_MW': s_mw.fillna(0),
                'Winter_MW': w_mw.fillna(0)
            })

            exclude_types = (
                'marketer|retail power|community choice aggregator|'
                'mktg authority|transmission'
            )
            df_peak = df_peak[
                ~df_peak['Entity'].str.contains(exclude_types, na=False)
            ]

            exclude_names = 'power agency|power pooling|wholesale'
            df_peak = df_peak[
                ~df_peak['Utility_Name'].str.contains(exclude_names, na=False)
            ]

            df_peak = df_peak[df_peak['State'].isin(VALID_STATES)]
            state_peak = df_peak.groupby(
                'State'
            )[['Summer_MW', 'Winter_MW']].sum().reset_index()

            state_peak['Summer_Peak_Demand_GW'] = (
                state_peak['Summer_MW'] / 1000.0
            )
            state_peak['Winter_Peak_Demand_GW'] = (
                state_peak['Winter_MW'] / 1000.0
            )
            state_peak.rename(columns={'State': 'Region'}, inplace=True)

            return state_peak[[
                'Region', 'Summer_Peak_Demand_GW', 'Winter_Peak_Demand_GW'
            ]]

    except Exception as e:
        print(f"Error parsing peak zip: {e}")
        return pd.DataFrame(columns=[
            'Region', 'Summer_Peak_Demand_GW', 'Winter_Peak_Demand_GW'
        ])


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
                "seriesId": [
                    "TNRCB", "TNCCB", "TERCV", "TECCV", "TERCE", "TECCE",
                    "TEEIE", "ESRCB", "ESCCB", "ESTXB", "ESTCB"
                ]
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
                seds_year = int(seds_df['period'].mode()[0])
            except (ValueError, TypeError, IndexError):
                seds_year = 2022

            seds_grouped = (
                seds_df.groupby(['stateid', 'seriesid'])['value']
                .sum().unstack(fill_value=0).reset_index()
            )
            seds_grouped.rename(columns={'stateid': 'Region'}, inplace=True)
            seds_grouped['Region'] = seds_grouped['Region'].str.upper()

            def get_series(col_name):
                if col_name in seds_grouped.columns:
                    return seds_grouped[col_name]
                return pd.Series(0.0, index=seds_grouped.index)

            eng_total = get_series('TNRCB') + get_series('TNCCB')
            seds_grouped['Energy_Use_TBtu'] = eng_total / 1000

            cost_total = get_series('TERCV') + get_series('TECCV')
            seds_grouped['Energy_Cost_M$'] = cost_total

            power_emi = get_series('TEEIE')
            res_sales = get_series('ESRCB')
            com_sales = get_series('ESCCB')

            tot_sales = get_series('ESTXB')
            tot_sales = tot_sales.where(tot_sales > 0, get_series('ESTCB'))
            tot_sales = tot_sales.where(tot_sales > 0, res_sales + com_sales)
            tot_sales = tot_sales.replace(0, 1)  # Prevent division by zero

            res_allocated = get_series('TERCE') + (
                power_emi * (res_sales / tot_sales)
            )
            com_allocated = get_series('TECCE') + (
                power_emi * (com_sales / tot_sales)
            )
            seds_grouped['Emissions_MMTCO2e'] = res_allocated + com_allocated
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
        map_df_all['Summer_Peak_pc'] = (
            map_df_all['Summer_Peak_Demand_GW'] * 1_000_000
        ) / map_df_all['Population']
        map_df_all['Winter_Peak_pc'] = (
            map_df_all['Winter_Peak_Demand_GW'] * 1_000_000
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

        # Return the years so we can build dynamic titles
        return map_df_all, seds_year, peak_year

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API Fetch Request failed entirely: {e}")


def load_segs_data(csv_path="data/segs_env.csv"):
    """
    Loads and cleans data from data/segs.csv for the state detail pages.
    """
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found.")
        return pd.DataFrame()

    df = pd.read_csv(csv_path, low_memory=False)
    df.columns = df.columns.str.strip()

    # Standardize column naming just in case
    if 'Buildings Sector' in df.columns:
        df.rename(
            columns={'Buildings Sector': 'Building Sector'},
            inplace=True
        )

    # Protect the Building Sector from dropping entirely in aggregations
    if 'Building Sector' in df.columns:
        df['Building Sector'] = (
            df['Building Sector'].fillna('Unknown').astype(str).str.strip()
        )

    if 'Building Type' in df.columns:
        df = df[df['Building Type'].astype(str).str.lower() != 'all']

    if 'Region' in df.columns:
        df = df[~df['Region'].isin(['AK', 'HI'])]

    if 'Envelope Flag' not in df.columns:
        df['Envelope Flag'] = 'equipment'
    df['Envelope Flag'] = (
        df['Envelope Flag'].fillna('equipment')
        .astype(str).str.strip().str.lower()
    )

    metrics = [
        'Site Energy (TWh)', 'Peak Demand, Summer (GW)',
        'Peak Demand, Winter (GW)',
        'Energy Costs (Bn.$)', 'Emissions (CO2e)', 'Capital Costs (Bn.$)'
    ]
    for m in metrics:
        if m in df.columns:
            df[m] = pd.to_numeric(df[m], errors='coerce').fillna(0)
            equip_mask = df['Envelope Flag'] != 'envelope'
            df.loc[equip_mask, m] = df.loc[equip_mask, m].clip(lower=0)

    # Automatically convert TWh to TBtu for consistency with maps
    if 'Site Energy (TWh)' in df.columns:
        df['Site Energy Use (TBtu)'] = df['Site Energy (TWh)'] * 3.412142

    # Ensure path cols AND tooltip cols exist and handle nulls
    path_cols = [
        'Fuel Type', 'End Use', 'Segment Name', 'Building Type', 'Vintage'
    ]
    tooltip_cols = [
        'Fuel Type Tooltip', 'End Use Tooltip', 'Segment Tooltip',
        'Building Type Tooltip', 'Vintage Tooltip'
    ]

    for p in path_cols + tooltip_cols:
        if p in df.columns:
            df[p] = df[p].fillna('Unknown')

    return df


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


def generate_sunburst_row(
    df_subset, metric_col, path_cols, alt_path_cols,
    color_dict=None, tooltip_mapping_by_col=None
):
    """Generates Multi-Filtered Sunbursts, grouped with Segmented Toggles."""
    if tooltip_mapping_by_col is None:
        tooltip_mapping_by_col = {}

    years = [2026, 2035, 2050]

    def build_charts(data, current_path, view_id):
        if 'Envelope Flag' in data.columns:
            df_equip = data[data['Envelope Flag'] != 'envelope']
            df_env = data[data['Envelope Flag'] == 'envelope'].copy()

            # Suppress Solar Windows and rename Conduction Windows for Cap Costs
            if metric_col == 'Capital Costs (Bn.$)':
                mask_solar = df_env[
                    'Segment Name'].astype(str).str.contains(
                        r'Windows.*\(Solar\)', case=False, regex=True)
                df_env = df_env[~mask_solar]

                df_env['Segment Name'] = (
                    df_env['Segment Name'].astype(str)
                    .str.replace(r'Windows.*\(Conduction\)', 'Windows', case=False, regex=True)
                )
                if 'Segment Tooltip' in df_env.columns:
                    df_env['Segment Tooltip'] = (
                        df_env['Segment Tooltip'].astype(str)
                        .str.replace(r'Windows.*\(Conduction\)', 'Windows', case=False, regex=True)
                    )
        else:
            df_equip = data
            df_env = pd.DataFrame()

        row_html = (
            "<div style='display: flex; flex-wrap: wrap; "
            "justify-content: space-between; width: 100%;'>"
        )

        # Extract unit safely from metric name (e.g., 'TBtu')
        unit = ""
        if "(" in metric_col and ")" in metric_col:
            unit = metric_col.split('(')[-1].split(')')[0]

        for year in years:
            df_year = df_equip[df_equip['Year'] == year].copy()

            if df_year.empty or df_year[metric_col].sum() == 0:
                row_html += (
                    f"<div class='chart-container'>"
                    f"<p style='text-align:center;'>No {metric_col} "
                    f"data for {year}</p></div>"
                )
                continue

            total_val = df_year[metric_col].sum()
            unit_str = f" {unit}" if unit else ""

            fig = px.sunburst(
                df_year, path=current_path, values=metric_col,
                color=current_path[0], color_discrete_map=color_dict,
                title=f"Year {year}: {total_val:,.1f}{unit_str}"
            )

            mapped_hover_text = []
            for i, label in enumerate(fig.data[0].labels):
                node_id = fig.data[0].ids[i]
                parts = str(node_id).split('/')
                col_idx = len(parts) - 1

                if col_idx >= 0 and col_idx < len(current_path):
                    col_name = current_path[col_idx]
                    tooltip = tooltip_mapping_by_col.get(col_name, {}).get(label, label)
                else:
                    tooltip = label

                mapped_hover_text.append([tooltip])

            fig.update_traces(
                customdata=mapped_hover_text,
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    f"{metric_col}: %{{value:,.1f}}<br>"
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
            ).replace(
                '<script type="text/javascript">',
                '<script type="text/template" class="lazy-plotly">'
            )
            row_html += f"<div class='chart-container'>{chart_div}</div>"

        row_html += "</div>\n"

        # Append Envelope Diverging Bar Charts (Filtered by Year and View)
        if not df_env.empty and (df_env[metric_col] != 0).any():
            row_html += (
                f"<div id='thermal-wrapper-{view_id}' "
                f"style='display: flex; flex-direction: column; "
                f"width: 100%;'>\n"
                f"<h2 style='text-align:center; font-weight:400; "
                f"margin-top:40px; margin-bottom:10px;'>"
                f"Thermal Load Components</h2>\n"
            )

            if metric_col == 'Peak Demand, Winter (GW)':
                row_html += (
                    "<p style='text-align:center; font-size:13px; "
                    "color:#6e7781; margin-top:-5px; "
                    "margin-bottom:15px; max-width:800px; "
                    "margin-left:auto; margin-right:auto;'>\n"
                    "* Heating components exclude internal gains and "
                    "windows solar, which currently lack load shapes "
                    "needed to determine impacts on peak heating loads.\n</p>\n"
                )

            # Toggles for View (Split/Combined) and Year
            is_cap_cost = (metric_col == 'Capital Costs (Bn.$)')

            if is_cap_cost:
                # Hide the view toggle, but keep a checked radio button so JS works
                view_toggle_html = (
                    f"<div style='display: none;'>\n"
                    f"    <input type='radio' id='env-comb-{view_id}' "
                    f"name='env-view-{view_id}' value='combined' checked>\n"
                    f"</div>\n"
                )
            else:
                # Standard visible toggle
                view_toggle_html = (
                    f"    <div class='segmented-control'>\n"
                    f"        <input type='radio' id='env-comb-{view_id}' "
                    f"name='env-view-{view_id}' value='combined' checked "
                    f"onchange=\"updateThermalView('{view_id}')\">\n"
                    f"        <label for='env-comb-{view_id}'>Combined "
                    f"Impact</label>\n"
                    f"        <input type='radio' id='env-split-{view_id}' "
                    f"name='env-view-{view_id}' value='split' "
                    f"onchange=\"updateThermalView('{view_id}')\">\n"
                    f"        <label for='env-split-{view_id}'>Heating vs. "
                    f"Cooling</label>\n"
                    f"    </div>\n"
                )

            row_html += (
                f"<div style='display: flex; justify-content: center; "
                f"gap: 20px; margin-bottom: 20px; flex-wrap: wrap;'>\n"
                f"{view_toggle_html}"
                f"    <div class='segmented-control'>\n"
                f"        <input type='radio' id='yr-2026-{view_id}' "
                f"name='env-year-{view_id}' value='2026' checked "
                f"onchange=\"updateThermalView('{view_id}')\">\n"
                f"        <label for='yr-2026-{view_id}'>2026</label>\n"
                f"        <input type='radio' id='yr-2035-{view_id}' "
                f"name='env-year-{view_id}' value='2035' "
                f"onchange=\"updateThermalView('{view_id}')\">\n"
                f"        <label for='yr-2035-{view_id}'>2035</label>\n"
                f"        <input type='radio' id='yr-2050-{view_id}' "
                f"name='env-year-{view_id}' value='2050' "
                f"onchange=\"updateThermalView('{view_id}')\">\n"
                f"        <label for='yr-2050-{view_id}'>2050</label>\n"
                f"    </div>\n"
                f"</div>\n"
            )

            for year in years:
                df_yr = df_env[df_env['Year'] == year].copy()
                if not df_yr.empty and (df_yr[metric_col] != 0).any():
                    df_res = df_yr[
                        df_yr['Building Sector'].fillna('').str.lower()
                        .str.contains('res')
                    ]
                    df_com = df_yr[
                        df_yr['Building Sector'].fillna('').str.lower()
                        .str.contains('com')
                    ]

                    # --- SPLIT VIEW (HEATING AND COOLING) ---
                    # Only build split view if this is NOT the Capital Costs tab
                    if not is_cap_cost:
                        row_html += (
                            f"<div class='thermal-plot-container' "
                            f"data-year='{year}' data-view='split' "
                            f"style='display: none; "
                            f"flex-direction: column; width: 100%;'>\n"
                        )

                        for s_name, s_df in [
                            ("Residential", df_res), ("Commercial", df_com)
                        ]:
                            if not s_df.empty and (s_df[metric_col] != 0).any():
                                # Calculate global x-axis range for this sector
                                max_x = 0
                                min_x = 0
                                for end_use in ['Heat.', 'Cool.']:
                                    eu_df = s_df[s_df['End Use'] == end_use]
                                    if not eu_df.empty:
                                        agg = eu_df.groupby(
                                            ['Segment Name',
                                             'Building Type Tooltip']
                                        )[metric_col].sum().reset_index()

                                        p_sum = agg[agg[metric_col] > 0].groupby(
                                            'Segment Name'
                                        )[metric_col].sum()
                                        n_sum = agg[agg[metric_col] < 0].groupby(
                                            'Segment Name'
                                        )[metric_col].sum()

                                        if not p_sum.empty:
                                            max_x = max(max_x, p_sum.max())
                                        if not n_sum.empty:
                                            min_x = min(min_x, n_sum.min())

                                range_span = max_x - min_x
                                pad = range_span * 0.25 if range_span != 0 else 1
                                x_range = [min_x - pad, max_x + pad]

                                row_html += (
                                    f"<h3 style='text-align:center; "
                                    f"font-weight:500; color:#57606a; "
                                    f"margin-top:30px;'>"
                                    f"{s_name} Components</h3>\n"
                                    f"<div style='display: flex; flex-wrap: wrap; "
                                    f"justify-content: center; gap: 20px; "
                                    f"width: 100%;'>\n"
                                )

                                for eu_val, eu_lbl in [
                                    ('Heat.', 'Heating'), ('Cool.', 'Cooling')
                                ]:
                                    eu_df = s_df[s_df['End Use'] == eu_val]

                                    if not eu_df.empty and (
                                        eu_df[metric_col] != 0
                                    ).any():
                                        df_agg = eu_df.groupby(
                                            ['Segment Name',
                                             'Building Type Tooltip']
                                        )[metric_col].sum().reset_index()

                                        df_agg = df_agg[df_agg[metric_col] != 0]

                                        fig_bar = px.bar(
                                            df_agg,
                                            y='Segment Name',
                                            x=metric_col,
                                            color='Building Type Tooltip',
                                            custom_data=['Building Type Tooltip'],
                                            orientation='h',
                                            barmode='relative',
                                            title=f"{eu_lbl}"
                                        )

                                        ht_split = (
                                            "Component: %{y}<br>"
                                            "Building Type: %{customdata[0]}<br>"
                                            f"{metric_col}: "
                                            "%{x:,.1f}<extra></extra>"
                                        )

                                        fig_bar.update_traces(
                                            hovertemplate=ht_split
                                        )

                                        # Add total labels at the end of each bar
                                        agg_totals = df_agg.groupby(
                                            'Segment Name')[metric_col].sum().reset_index()
                                        for _, r_tot in agg_totals.iterrows():
                                            net_val = r_tot[metric_col]
                                            seg_data = df_agg[
                                                df_agg['Segment Name'] == r_tot[
                                                    'Segment Name']][metric_col]
                                            if net_val >= 0:
                                                edge_val = seg_data[seg_data > 0].sum() if (
                                                    seg_data > 0).any() else 0
                                                xanchor = 'left'
                                                xshift = 5
                                            else:
                                                edge_val = seg_data[seg_data < 0].sum() if (
                                                    seg_data < 0).any() else 0
                                                xanchor = 'right'
                                                xshift = -5

                                            fig_bar.add_annotation(
                                                x=edge_val, y=r_tot['Segment Name'],
                                                text=f"<b>{net_val:,.1f}</b>",
                                                showarrow=False, xanchor=xanchor, xshift=xshift,
                                                font=dict(
                                                    family=GITHUB_FONT, size=11, color='#24292f')
                                            )

                                        fig_bar.update_layout(
                                            font=dict(family=GITHUB_FONT),
                                            margin=dict(t=40, l=0, r=0, b=80),
                                            autosize=True, height=450,
                                            xaxis_title=metric_col,
                                            yaxis_title="",
                                            legend_title_text="",
                                            legend=dict(
                                                orientation="h", yanchor="top",
                                                y=-0.25, xanchor="center", x=0.5
                                            )
                                        )
                                        fig_bar.update_yaxes(
                                            categoryorder='total ascending'
                                        )
                                        fig_bar.update_xaxes(range=x_range)

                                        bar_div = fig_bar.to_html(
                                            full_html=False,
                                            include_plotlyjs=False,
                                            default_width='100%',
                                            config={'responsive': True}
                                        ).replace(
                                            '<script type="text/javascript">',
                                            '<script type="text/template" '
                                            'class="lazy-plotly">'
                                        )
                                        row_html += (
                                            f"<div class='chart-container' "
                                            f"style='flex: 1 1 45%; "
                                            f"min-width:300px; background: white; "
                                            f"padding: 20px; border-radius: 8px; "
                                            f"box-shadow: 0 2px 4px "
                                            f"rgba(0,0,0,0.1);'>{bar_div}"
                                            f"</div>\n"
                                        )
                                    else:
                                        row_html += (
                                            f"<div class='chart-container' "
                                            f"style='flex: 1 1 45%; "
                                            f"min-width:300px; background: white; "
                                            f"padding: 20px; border-radius: 8px; "
                                            f"box-shadow: 0 2px 4px "
                                            f"rgba(0,0,0,0.1); display:flex; "
                                            f"align-items:center; "
                                            f"justify-content:center;'>"
                                            f"<p style='color:#57606a;'>"
                                            f"No {eu_lbl} data</p></div>\n"
                                        )

                                row_html += "</div>\n"
                        row_html += "</div>\n"

                    # --- COMBINED VIEW (NET IMPACT) ---
                    disp_comb = 'flex' if year == 2026 else 'none'
                    row_html += (
                        f"<div class='thermal-plot-container' "
                        f"data-year='{year}' data-view='combined' "
                        f"style='display: {disp_comb}; flex-wrap: wrap; "
                        f"justify-content: center; gap: 20px; "
                        f"width: 100%; margin-top:30px;'>\n"
                    )

                    max_c = 0
                    min_c = 0
                    for s_name, s_df in [
                        ("Residential", df_res), ("Commercial", df_com)
                    ]:
                        if not s_df.empty and (s_df[metric_col] != 0).any():
                            agg = s_df.groupby(
                                ['Segment Name', 'Building Type Tooltip']
                            )[metric_col].sum().reset_index()

                            p_sum = agg[agg[metric_col] > 0].groupby(
                                'Segment Name'
                            )[metric_col].sum()
                            n_sum = agg[agg[metric_col] < 0].groupby(
                                'Segment Name'
                            )[metric_col].sum()

                            if not p_sum.empty:
                                max_c = max(max_c, p_sum.max())
                            if not n_sum.empty:
                                min_c = min(min_c, n_sum.min())

                    range_span_c = max_c - min_c
                    pad_c = range_span_c * 0.25 if range_span_c != 0 else 1
                    x_range_c = [min_c - pad_c, max_c + pad_c]

                    for s_name, s_df in [
                        ("Residential", df_res), ("Commercial", df_com)
                    ]:
                        if not s_df.empty and (s_df[metric_col] != 0).any():
                            df_agg = s_df.groupby(
                                ['Segment Name', 'Building Type Tooltip']
                            )[metric_col].sum().reset_index()

                            df_agg = df_agg[df_agg[metric_col] != 0]

                            fig_bar = px.bar(
                                df_agg,
                                y='Segment Name',
                                x=metric_col,
                                color='Building Type Tooltip',
                                custom_data=['Building Type Tooltip'],
                                orientation='h',
                                barmode='relative',
                                title=f"{s_name} Combined Impact"
                            )

                            ht_comb = (
                                "Component: %{y}<br>"
                                "Building Type: %{customdata[0]}<br>"
                                f"{metric_col}: "
                                "%{x:,.1f}<extra></extra>"
                            )

                            fig_bar.update_traces(hovertemplate=ht_comb)

                            # Add total labels at the end of each bar
                            agg_totals = df_agg.groupby(
                                'Segment Name')[metric_col].sum().reset_index()
                            for _, r_tot in agg_totals.iterrows():
                                net_val = r_tot[metric_col]
                                seg_data = df_agg[df_agg[
                                    'Segment Name'] == r_tot['Segment Name']][metric_col]
                                if net_val >= 0:
                                    edge_val = seg_data[
                                        seg_data > 0].sum() if (seg_data > 0).any() else 0
                                    xanchor = 'left'
                                    xshift = 5
                                else:
                                    edge_val = seg_data[
                                        seg_data < 0].sum() if (seg_data < 0).any() else 0
                                    xanchor = 'right'
                                    xshift = -5

                                fig_bar.add_annotation(
                                    x=edge_val, y=r_tot['Segment Name'],
                                    text=f"<b>{net_val:,.1f}</b>",
                                    showarrow=False, xanchor=xanchor, xshift=xshift,
                                    font=dict(family=GITHUB_FONT, size=11, color='#24292f')
                                )

                            fig_bar.update_layout(
                                font=dict(family=GITHUB_FONT),
                                margin=dict(t=40, l=0, r=0, b=80),
                                autosize=True, height=450,
                                xaxis_title=metric_col,
                                yaxis_title="",
                                legend_title_text="",
                                legend=dict(
                                    orientation="h", yanchor="top",
                                    y=-0.25, xanchor="center", x=0.5
                                )
                            )
                            fig_bar.update_yaxes(
                                categoryorder='total ascending'
                            )
                            fig_bar.update_xaxes(range=x_range_c)

                            bar_div = fig_bar.to_html(
                                full_html=False, include_plotlyjs=False,
                                default_width='100%',
                                config={'responsive': True}
                            ).replace(
                                '<script type="text/javascript">',
                                '<script type="text/template" '
                                'class="lazy-plotly">'
                            )
                            row_html += (
                                f"<div class='chart-container' "
                                f"style='flex: 1 1 45%; min-width:300px; "
                                f"background: white; padding: 20px; "
                                f"border-radius: 8px; box-shadow: 0 2px 4px "
                                f"rgba(0,0,0,0.1);'>{bar_div}</div>\n"
                            )

                    row_html += "</div>\n"

            row_html += "</div>\n"

        return row_html

    # Safely extract unique ID base for the tab controls
    tab_id = "".join(e for e in metric_col if e.isalnum())

    def get_filtered_df(df, sector_val, unknown_val, p_cols):
        tmp = df.copy()

        if sector_val == 'res' and 'Building Sector' in tmp.columns:
            b_sec = tmp['Building Sector'].astype(str).str.lower()
            mask = b_sec == 'residential'
            tmp = tmp[mask]
        elif sector_val == 'com' and 'Building Sector' in tmp.columns:
            b_sec = tmp['Building Sector'].astype(str).str.lower()
            mask = b_sec == 'commercial'
            tmp = tmp[mask]

        if unknown_val == 'exc' and 'End Use' in tmp.columns:
            tmp = tmp[tmp['End Use'] != 'Unknown']

        for col in p_cols:
            if col in tmp.columns:
                tmp[col] = tmp[col].astype(str).str.replace(' ', '<br>')

        return tmp

    # Dynamically build the 12 HTML combinations
    html_combinations = ""
    for hier_val, p_cols in [('fuel', path_cols), ('bldg', alt_path_cols)]:
        for sec_val in ['all', 'res', 'com']:
            for unk_val in ['inc', 'exc']:
                view_id = f"{tab_id}-{hier_val}-{sec_val}-{unk_val}"
                df_filtered = get_filtered_df(
                    df_subset, sec_val, unk_val, p_cols
                )
                charts_html = build_charts(df_filtered, p_cols, view_id)

                active_cls = (
                    "active-layer" if hier_val == 'fuel' and
                    sec_val == 'all' and unk_val == 'inc' else ""
                )

                html_combinations += (
                    f"<div class='sunburst-view "
                    f"view-{hier_val}-{sec_val}-{unk_val} "
                    f"stack-layer {active_cls}'>\n"
                    f"    {charts_html}\n"
                    f"</div>\n"
                )

    combined_html = (
        "<div class='filter-panel' style='display: flex; "
        "justify-content: center; gap: 20px; margin-bottom: 20px; "
        "flex-wrap: wrap;'>\n"
        "    <div style='display: flex; align-items: center; gap: 8px;'>\n"
        "        <span class='toggle-label'>Grouping:</span>\n"
        "        <div class='segmented-control'>\n"
        f"            <input type='radio' id='hier-fuel-{tab_id}' "
        f"name='hierarchy-{tab_id}' value='fuel' checked "
        "onchange='updateSunburstFilters(this)'>\n"
        f"            <label for='hier-fuel-{tab_id}'>Fuel First</label>\n"
        f"            <input type='radio' id='hier-bldg-{tab_id}' "
        f"name='hierarchy-{tab_id}' value='bldg' "
        "onchange='updateSunburstFilters(this)'>\n"
        f"            <label for='hier-bldg-{tab_id}'>Building First</label>\n"
        "        </div>\n"
        "    </div>\n"
        "    <div style='display: flex; align-items: center; gap: 8px;'>\n"
        "        <span class='toggle-label'>Sector:</span>\n"
        "        <div class='segmented-control'>\n"
        f"            <input type='radio' id='sec-all-{tab_id}' "
        f"name='sector-{tab_id}' value='all' checked "
        "onchange='updateSunburstFilters(this)'>\n"
        f"            <label for='sec-all-{tab_id}'>All</label>\n"
        f"            <input type='radio' id='sec-res-{tab_id}' "
        f"name='sector-{tab_id}' value='res' "
        "onchange='updateSunburstFilters(this)'>\n"
        f"            <label for='sec-res-{tab_id}'>Residential</label>\n"
        f"            <input type='radio' id='sec-com-{tab_id}' "
        f"name='sector-{tab_id}' value='com' "
        "onchange='updateSunburstFilters(this)'>\n"
        f"            <label for='sec-com-{tab_id}'>Commercial</label>\n"
        "        </div>\n"
        "    </div>\n"
        "    <div style='display: flex; align-items: center; gap: 8px;'>\n"
        "        <span class='toggle-label'>Unknowns:</span>\n"
        "        <div class='segmented-control'>\n"
        f"            <input type='radio' id='unk-inc-{tab_id}' "
        f"name='unknown-{tab_id}' value='inc' checked "
        "onchange='updateSunburstFilters(this)'>\n"
        f"            <label for='unk-inc-{tab_id}'>Include</label>\n"
        f"            <input type='radio' id='unk-exc-{tab_id}' "
        f"name='unknown-{tab_id}' value='exc' "
        "onchange='updateSunburstFilters(this)'>\n"
        f"            <label for='unk-exc-{tab_id}'>Exclude</label>\n"
        "        </div>\n"
        "    </div>\n"
    )

    # Conditionally add the "View Thermal Loads" link
    has_thermal = False
    if 'Envelope Flag' in df_subset.columns:
        if not df_subset[df_subset['Envelope Flag'] == 'envelope'].empty:
            has_thermal = True

    if has_thermal:
        combined_html += (
            "    <div style='display: flex; align-items: center; "
            "gap: 8px; margin-left: 10px;'>\n"
            "        <a href='javascript:void(0);' "
            "onclick='scrollToThermal(this)' "
            "style='color: #0969da; font-weight: 600; font-size: 14px; "
            "text-decoration: none;'>\n"
            "        View Thermal Loads ↓</a>\n"
            "    </div>\n"
        )

    combined_html += (
        "</div>\n"
        "<div class='stack-grid'>\n"
        f"{html_combinations}\n"
        "</div>\n"
    )
    return combined_html


# ---------------------------------------------------------
# Main Execution
# ---------------------------------------------------------
def main():
    load_dotenv()
    eia_key = os.environ.get('EIA_API_KEY')
    census_key = os.environ.get('CENSUS_API_KEY')

    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)

    # Fetch strictly live map data and capture dynamic years
    map_df_all, seds_year, peak_year = fetch_live_home_page_data(
        eia_key, census_key
    )

    # Load Real Detail Data from CSV
    df = load_segs_data("data/segs_env.csv")
    dynamic_navbar = generate_navbar_html(CENSUS_DIVISIONS)

    std_path = [
        'Fuel Type', 'End Use', 'Segment Name', 'Building Type', 'Vintage'
    ]
    alt_path = [
        'Building Type', 'Vintage', 'Fuel Type', 'End Use', 'Segment Name'
    ]

    # Dynamically build the tooltip mapping dictionary based on real CSV keys
    tooltip_mapping_by_col = {}
    if not df.empty:
        pairs = [
            ('Fuel Type', 'Fuel Type Tooltip'),
            ('End Use', 'End Use Tooltip'),
            ('Segment Name', 'Segment Tooltip'),
            ('Building Type', 'Building Type Tooltip'),
            ('Vintage', 'Vintage Tooltip')
        ]
        for short_col, long_col in pairs:
            tooltip_mapping_by_col[short_col] = {}
            if short_col in df.columns and long_col in df.columns:
                for s, l in zip(df[short_col], df[long_col]):
                    tooltip_mapping_by_col[short_col][str(s)] = str(l)
                    # Map the `<br>` replaced version exactly as Plotly sees it
                    tooltip_mapping_by_col[short_col][str(s).replace(' ', '<br>')] = str(l)

    std_colors = {
        'Elec.': '#19D3F3',
        'NG': '#FFA15A',
        'Prop.': '#B6E880',
        'Dist.': '#FF97FF',
        'Other': '#7F7F7F',
        'Bio.': '#2CA02C'
    }

    # Helper function to generate individual pages
    def build_page_html(data_slice, page_title):
        html_eng = generate_sunburst_row(
            data_slice, 'Site Energy Use (TBtu)', std_path, alt_path,
            std_colors, tooltip_mapping_by_col
        )
        html_emi = generate_sunburst_row(
            data_slice, 'Emissions (CO2e)', std_path, alt_path,
            std_colors, tooltip_mapping_by_col
        )
        html_cap = generate_sunburst_row(
            data_slice, 'Capital Costs (Bn.$)', std_path, alt_path,
            std_colors, tooltip_mapping_by_col
        )
        html_enc = generate_sunburst_row(
            data_slice, 'Energy Costs (Bn.$)', std_path, alt_path,
            std_colors, tooltip_mapping_by_col
        )

        # For Peak Demand we want Electricity for equipment,
        # but ALL envelope loads
        peak_mask = (
            (data_slice['Fuel Type'] == 'Elec.') |
            (data_slice['Envelope Flag'] == 'envelope')
        )
        peak_df = data_slice[peak_mask]

        peak_path = std_path[1:]
        alt_peak_path = alt_path.copy()
        alt_peak_path.remove('Fuel Type')

        html_summer_peak = generate_sunburst_row(
            peak_df, 'Peak Demand, Summer (GW)', peak_path, alt_peak_path,
            std_colors, tooltip_mapping_by_col
        )
        html_winter_peak = generate_sunburst_row(
            peak_df, 'Peak Demand, Winter (GW)', peak_path, alt_peak_path,
            std_colors, tooltip_mapping_by_col
        )

        return HTML_TEMPLATE.format(
            css_styles=CSS_STYLES, nav_bar_html=dynamic_navbar,
            page_title=page_title, energy_charts_html=html_eng,
            emissions_charts_html=html_emi,
            summer_peak_charts_html=html_summer_peak,
            winter_peak_charts_html=html_winter_peak,
            cap_cost_charts_html=html_cap, energy_cost_charts_html=html_enc
        )

    if not df.empty:
        print("Generating National view from aggregated CSV...")
        metrics = [
            'Site Energy Use (TBtu)', 'Peak Demand, Summer (GW)',
            'Peak Demand, Winter (GW)',
            'Energy Costs (Bn.$)', 'Emissions (CO2e)', 'Capital Costs (Bn.$)'
        ]

        # Include tooltip columns so they survive the National aggregation
        tooltip_cols_to_keep = [
            'Fuel Type Tooltip', 'End Use Tooltip', 'Segment Tooltip',
            'Building Type Tooltip', 'Vintage Tooltip'
        ]

        # Include 'Building Sector' and 'Envelope Flag' in groupby
        group_cols = (
            ['Year', 'Building Sector', 'Envelope Flag'] +
            list(set(std_path + alt_path + tooltip_cols_to_keep))
        )
        actual_group_cols = [c for c in group_cols if c in df.columns]

        # Use dropna=False so 'Unknown' or missing data isn't destroyed
        df_nat = df.groupby(
            actual_group_cols, dropna=False
        )[metrics].sum().reset_index()
        df_nat['Region'] = 'National'

        with open(os.path.join(output_dir, "national.html"), "w") as f:
            f.write(build_page_html(df_nat, "National"))

        # Generate State Views
        for state in df['Region'].unique():
            if state in ['AK', 'HI', 'National']:
                continue
            print(f"Generating view for {state}...")
            state_df = df[df['Region'] == state]
            with open(os.path.join(output_dir, f"{state}.html"), "w") as f:
                f.write(build_page_html(state_df, state))
    else:
        print("[WARNING] No real data available. Detail pages skipped.")

    print("Generating Multi-Panel Home page...")
    if not map_df_all.empty:

        def generate_map_panel(
            data, metric, title, hover_title, is_ahs=False, fmt=",.1f"
        ):
            fig = px.choropleth(
                data, locations='Region', locationmode="USA-states",
                color=metric, scope="usa",
                color_continuous_scale="Teal"
            )

            fig.update_traces(marker_line_color='white', marker_line_width=1.0)

            if is_ahs and 'Division_Name' in data.columns:
                fig.update_traces(
                    customdata=data[['Division_Name']],
                    hovertemplate=(
                        "<b>%{location} (%{customdata[0]})</b><br>" +
                        hover_title + ": %{z:" + fmt + "}<extra></extra>")
                )
            else:
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{location}</b><br>" +
                        hover_title + ": %{z:" + fmt + "}<extra></extra>")
                )

            fig.update_layout(
                font=dict(family=GITHUB_FONT, size=12),
                margin=dict(t=10, l=0, r=0, b=0),
                coloraxis_colorbar=dict(title=None, thickness=10, len=0.7),
                autosize=True
            )
            chart_div = fig.to_html(
                full_html=False, include_plotlyjs=False,
                default_width='100%', default_height='380px',
                config={'responsive': True}
            ).replace(
                '<script type="text/javascript">',
                '<script type="text/template" class="lazy-plotly">'
            )

            return (
                f"<div style='text-align: center; font-size: 16px; "
                f"font-weight: 600; padding: 0 10px;'>{title}</div>\n"
                f"{chart_div}"
            )

        # Calculate Absolute Totals
        tot_eng = map_df_all['Energy_Use_TBtu'].sum()
        tot_summer_peak = map_df_all['Summer_Peak_Demand_GW'].sum()
        tot_winter_peak = map_df_all['Winter_Peak_Demand_GW'].sum()
        tot_emi = map_df_all['Emissions_MMTCO2e'].sum()

        # Calculate Billions for Financials
        tot_cap_bn = map_df_all['Capital_Cost_M$'].sum() / 1000
        tot_enc_bn = map_df_all['Energy_Cost_M$'].sum() / 1000

        # Build Source Attributions (Clean formatting, contiguous strings)
        s_seds = (
            "<span style='font-size:11px; font-weight:normal; color:#6e7781;'>Source: "
            "<a href='https://www.eia.gov/state/seds/' target='_blank' style='color:#0969da; "
            "text-decoration:none;'>EIA State Energy Data System</a></span>")
        s_ahs = (
            "<span style='font-size:11px; font-weight:normal; color:#6e7781;'>Source: "
            "<a href='https://www.census.gov/programs-surveys/ahs/data/2023/ahs-2023-public-use-"
            "file--puf-/ahs-2023-national-public-use-file--puf-.html' target='_blank' "
            "style='color:#0969da; text-decoration:none;'>American Housing Survey</a></span>")
        s_peak = (
            "<span style='font-size:11px; font-weight:normal; color:#6e7781;'>Source: "
            "<a href='https://www.eia.gov/electricity/data/eia861/' target='_blank' "
            "style='color:#0969da; text-decoration:none;'>EIA-861</a></span>")

        # Build Map Titles
        title_eng = f"{seds_year} Site Energy Use: {tot_eng:,.0f} TBtu<br>{s_seds}"
        title_summer_peak = (
            f"{peak_year} Summer Peak: {tot_summer_peak:,.0f} GW<br>"
            f"<span style='font-size:12px; font-weight:normal;'>"
            f"*Total system peak demand.</span><br>{s_peak}"
        )
        title_winter_peak = (
            f"{peak_year} Winter Peak: {tot_winter_peak:,.0f} GW<br>"
            f"<span style='font-size:12px; font-weight:normal;'>"
            f"*Total system peak demand.</span><br>{s_peak}"
        )
        title_emi = f"{seds_year} Emissions: {tot_emi:,.0f} MMTCO2e<br>{s_seds}"
        title_cap = (
            f"2023 Capital Costs: {tot_cap_bn:,.1f} Bn.$<br>"
            f"<span style='font-size:12px; font-weight:normal;'>"
            f"*Annual equipment and envelope upgrades.</span><br>{s_ahs}"
        )
        title_enc = f"{seds_year} Energy Cost: {tot_enc_bn:,.1f} Bn.$<br>{s_seds}"

        # Build Per Capita Map Titles
        title_eng_pc = (
            f"{seds_year} Site Energy Use (MMBtu/Capita)<br>{s_seds}"
        )
        title_summer_peak_pc = (
            f"{peak_year} Summer Peak (kW/Capita)<br>"
            f"<span style='font-size:12px; font-weight:normal;'>"
            f"*Total system peak demand.</span><br>{s_peak}"
        )
        title_winter_peak_pc = (
            f"{peak_year} Winter Peak (kW/Capita)<br>"
            f"<span style='font-size:12px; font-weight:normal;'>"
            f"*Total system peak demand.</span><br>{s_peak}"
        )
        title_emi_pc = (
            f"{seds_year} Emissions (MTCO2e/Capita)<br>{s_seds}"
        )
        title_cap_pc = (
            "2023 Capital Costs ($/Capita)<br>"
            "<span style='font-size:12px; font-weight:normal;'>"
            "Equipment replacements only.</span><br>"
            f"{s_ahs}"
        )
        title_enc_pc = (
            f"{seds_year} Energy Cost ($/Capita)<br>{s_seds}"
        )

        map_eng = generate_map_panel(
            map_df_all, 'Energy_Use_TBtu', title_eng,
            "Site Energy Use (TBtu)"
        )
        map_summer_peak = generate_map_panel(
            map_df_all, 'Summer_Peak_Demand_GW', title_summer_peak,
            "Peak Demand, Summer (GW)"
        )
        map_winter_peak = generate_map_panel(
            map_df_all, 'Winter_Peak_Demand_GW', title_winter_peak,
            "Peak Demand, Winter (GW)"
        )
        map_emi = generate_map_panel(
            map_df_all, 'Emissions_MMTCO2e', title_emi,
            "Emissions (MMTCO2e)"
        )
        map_cap = generate_map_panel(
            map_df_all, 'Capital_Cost_M$', title_cap,
            "Capital Expenditures (M$)", is_ahs=True
        )
        map_enc = generate_map_panel(
            map_df_all, 'Energy_Cost_M$', title_enc,
            "Energy Cost (M$)"
        )

        map_eng_pc = generate_map_panel(
            map_df_all, 'Energy_pc', title_eng_pc,
            "Site Energy Use (MMBtu/Capita)", fmt=",.0f"
        )
        map_summer_peak_pc = generate_map_panel(
            map_df_all, 'Summer_Peak_pc', title_summer_peak_pc,
            "Peak Demand, Summer (kW/Capita)", fmt=",.2f"
        )
        map_winter_peak_pc = generate_map_panel(
            map_df_all, 'Winter_Peak_pc', title_winter_peak_pc,
            "Peak Demand, Winter (kW/Capita)", fmt=",.2f"
        )
        map_emi_pc = generate_map_panel(
            map_df_all, 'Emissions_pc', title_emi_pc,
            "Emissions (MTCO2e/Capita)", fmt=",.1f"
        )
        map_cap_pc = generate_map_panel(
            map_df_all, 'CapCost_pc', title_cap_pc,
            "CapEx ($/Capita)", is_ahs=True, fmt="$,.0f"
        )
        map_enc_pc = generate_map_panel(
            map_df_all, 'Cost_pc', title_enc_pc,
            "Energy Cost ($/Capita)", fmt="$,.0f"
        )

        final_idx_html = INDEX_TEMPLATE.format(
            css_styles=CSS_STYLES, nav_bar_html=dynamic_navbar,
            map_energy=map_eng, map_energy_pc=map_eng_pc,
            map_summer_peak=map_summer_peak,
            map_summer_peak_pc=map_summer_peak_pc,
            map_winter_peak=map_winter_peak,
            map_winter_peak_pc=map_winter_peak_pc,
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
