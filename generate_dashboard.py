import os
import random

import pandas as pd
import plotly.express as px


# ---------------------------------------------------------
# Constants and Configurations
# ---------------------------------------------------------
CENSUS_DIVISIONS = {
    'Pacific': ['CA', 'OR', 'WA', 'HI', 'AK'],
    'West South Central': ['TX', 'OK', 'AR', 'LA'],
    'New England': ['ME', 'NH', 'VT', 'MA', 'RI', 'CT']
}

GITHUB_FONT = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, '
    'Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji"'
)

CSS_STYLES = f"""
    body {{ font-family: {GITHUB_FONT}; margin: 0; padding: 0; background-color: #f9f9f9; color: #24292f; }}
    
    .container {{ padding: 20px; max-width: 1400px; margin: auto; }}
    .container-wide {{ padding: 20px 40px; max-width: 98%; margin: auto; box-sizing: border-box; }}
    
    .map-grid {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-bottom: 20px; }}
    .map-box {{ flex: 1 1 30%; min-width: 300px; background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); box-sizing: border-box; }}
    
    /* THE FIX: Replaced flexible growth with strict 32% widths and space-between alignment */
    .chart-row {{ display: flex; flex-wrap: wrap; justify-content: space-between; margin-bottom: 40px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); box-sizing: border-box; }}
    .chart-container {{ flex: 0 0 32%; box-sizing: border-box; }}
    
    /* Media query to seamlessly stack charts on smaller screens */
    @media (max-width: 900px) {{
        .chart-container {{ flex: 0 0 100%; margin-bottom: 20px; }}
    }}
    
    .nav-menu, .nav-menu ul {{ list-style: none; margin: 0; padding: 0; }}
    .nav-menu {{ background-color: #24292f; display: flex; }}
    .nav-menu > li {{ position: relative; }}
    .nav-menu a {{ display: block; color: white; padding: 14px 16px; text-decoration: none; font-weight: 500; }}
    .nav-menu a:hover {{ background-color: #57606a; }}
    .nav-menu ul {{ display: none; position: absolute; top: 100%; left: 0; background-color: #24292f; min-width: 200px; z-index: 1000; box-shadow: 0px 8px 16px rgba(0,0,0,0.4); }}
    .nav-menu li:hover > ul {{ display: block; }}
    .nav-menu ul ul {{ top: 0; left: 100%; background-color: #32383f; }}

    .tab-container {{ display: flex; justify-content: center; gap: 10px; margin-bottom: 30px; }}
    .tab-btn {{ padding: 10px 20px; cursor: pointer; background-color: #ebecf0; border: none; border-radius: 6px; font-size: 15px; font-weight: 600; font-family: inherit; color: #57606a; transition: 0.2s; }}
    .tab-btn:hover {{ background-color: #d0d7de; }}
    .tab-btn.active {{ background-color: #0969da; color: white; }}
    
    .tabs-wrapper {{ position: relative; width: 100%; }}
    .tab-content {{ position: absolute; top: 0; left: 0; width: 100%; visibility: hidden; opacity: 0; transition: opacity 0.3s; z-index: 0; }}
    .tab-content.active {{ position: relative; visibility: visible; opacity: 1; z-index: 1; }}
    
    @keyframes smoothLoad {{
        0% {{ opacity: 0; }}
        100% {{ opacity: 1; }}
    }}
    .fade-in-section {{
        opacity: 0; 
        animation: smoothLoad 0.4s ease-out forwards;
        animation-delay: 0.2s; 
    }}
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
            <button class="tab-btn" onclick="openTab(event, 'Energy')">Energy Use</button>
            <button class="tab-btn" onclick="openTab(event, 'PeakDemand')">Peak Demand</button>
            <button class="tab-btn" onclick="openTab(event, 'Emissions')">Emissions</button>
            <button class="tab-btn" onclick="openTab(event, 'CapCost')">Capital Cost</button>
            <button class="tab-btn" onclick="openTab(event, 'EnergyCost')">Energy Cost</button>
        </div>

        <div class="tabs-wrapper fade-in-section">
            <div id="Energy" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">Energy Use (TBtu)</h2>
                <div class="chart-row">{energy_charts_html}</div>
            </div>
            
            <div id="PeakDemand" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">Peak Demand (GW)</h2>
                <div class="chart-row">{peak_charts_html}</div>
            </div>
            
            <div id="Emissions" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">Emissions (MTCO2e)</h2>
                <div class="chart-row">{emissions_charts_html}</div>
            </div>
            
            <div id="CapCost" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">Capital Cost (M$)</h2>
                <div class="chart-row">{cap_cost_charts_html}</div>
            </div>
            
            <div id="EnergyCost" class="tab-content">
                <h2 style="text-align: center; font-weight: 400;">Energy Cost (M$)</h2>
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
        
        window.addEventListener('load', function() {{
            setTimeout(function() {{
                window.dispatchEvent(new Event('resize'));
            }}, 150);
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
        <h1 style="text-align: center; margin-bottom: 40px;">US Buildings Current Snapshot</h1>
        
        <div class="fade-in-section">
            <div class="map-grid">
                <div class="map-box" data-tab="Energy">{map_energy}</div>
                <div class="map-box" data-tab="PeakDemand">{map_peak}</div>
                <div class="map-box" data-tab="Emissions">{map_emissions}</div>
            </div>
            
            <div class="map-grid">
                <div class="map-box" data-tab="CapCost">{map_capcost}</div>
                <div class="map-box" data-tab="EnergyCost">{map_energycost}</div>
            </div>
        </div>
    </div>
    
    <script>
        var checkExist = setInterval(function() {{
           var plots = document.getElementsByClassName('plotly-graph-div');
           if (plots.length >= 5) {{
              clearInterval(checkExist);
              for (let i = 0; i < plots.length; i++) {{
                  let targetTab = plots[i].closest('.map-box').getAttribute('data-tab');
                  plots[i].on('plotly_click', function(data){{
                      let state = data.points[0].location;
                      window.location.href = state + '.html#' + targetTab;
                  }});
              }}
           }}
        }}, 100);

        window.addEventListener('load', function() {{
            setTimeout(function() {{
                window.dispatchEvent(new Event('resize'));
            }}, 150);
        }});
    </script>
</body>
</html>
"""


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------
def create_dummy_data():
    """Creates dummy dataset with all metrics and additional fuels."""
    random.seed(42)
    regions = ['CA', 'TX', 'ME']
    years = [2026, 2035, 2050]
    sectors = {
        'Residential': [
            'SF Home', 'MF Home', 'Mobile Home'
        ],
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

                        if fuel == 'Natural Gas':
                            e_fact = 0.5
                        elif fuel == 'Propane':
                            e_fact = 0.6
                        elif fuel == 'Fuel Oil':
                            e_fact = 0.7
                        else:
                            e_fact = 0.1

                        p_fact = 0.2 if fuel == 'Electricity' else 0.0

                        for c_type, v in [('Existing', val_ex), ('New', val_nw)]:
                            data.append([
                                r, y, sector, b_type, fuel, end_use, tech,
                                c_type,
                                round(v, 1),
                                round(v * e_fact, 1),
                                round(v * p_fact, 1),
                                round(v * 1.5, 1),
                                round(v * 0.8, 1)
                            ])

    cols = [
        'Region', 'Year', 'Sector', 'Building_Type', 'Fuel_Type',
        'End_Use', 'Technology', 'Construction_Type', 'Energy_Use_TBtu',
        'Emissions_MTCO2e', 'Peak_Demand_GW', 'Capital_Cost_M$',
        'Energy_Cost_M$'
    ]
    return pd.DataFrame(data, columns=cols)


def generate_navbar_html(divisions_dict):
    """Dynamically builds a bulletproof nested list dropdown HTML."""
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
    nav_html += (
        '        </ul>\n'
        '    </li>\n'
        '</ul>\n'
    )
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
                f"<p style='text-align:center;'>No {metric_col} data for "
                f"{year}</p></div>"
            )
            continue

        fig = px.sunburst(
            df_year,
            path=path_cols,
            values=metric_col,
            color=path_cols[0],
            color_discrete_map=color_dict,
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
            autosize=True,
            uniformtext=dict(minsize=11, mode='hide')
        )

        chart_div = fig.to_html(
            full_html=False, 
            include_plotlyjs=False, 
            default_width='100%',
            config={'responsive': True}
        )
        row_html += f"<div class='chart-container'>{chart_div}</div>"

    return row_html


# ---------------------------------------------------------
# Main Execution
# ---------------------------------------------------------
def main():
    output_dir = "docs"
    os.makedirs(output_dir, exist_ok=True)

    df = create_dummy_data()
    dynamic_navbar = generate_navbar_html(CENSUS_DIVISIONS)

    std_path = [
        'Fuel_Type', 'End_Use', 'Technology', 
        'Building_Type', 'Construction_Type'
    ]
    
    std_colors = {
        'Electricity': '#19D3F3',
        'Natural<br>Gas': '#FFA15A',
        'Propane': '#B6E880',
        'Fuel<br>Oil': '#FF97FF'
    }

    peak_path = [
        'End_Use', 'Technology', 'Building_Type', 'Construction_Type'
    ]
    peak_colors = {
        'Space<br>Heating': '#EF553B',
        'Water<br>Heating': '#00CC96',
        'Lighting': '#AB63FA',
        'HVAC': '#1F77B4'
    }

    def build_page_html(data_slice, page_title):
        html_eng = generate_sunburst_row(
            data_slice, 'Energy_Use_TBtu', std_path, std_colors
        )
        html_emi = generate_sunburst_row(
            data_slice, 'Emissions_MTCO2e', std_path, std_colors
        )
        html_cap = generate_sunburst_row(
            data_slice, 'Capital_Cost_M$', std_path, std_colors
        )
        html_enc = generate_sunburst_row(
            data_slice, 'Energy_Cost_M$', std_path, std_colors
        )
        
        peak_df = data_slice[data_slice['Fuel_Type'] == 'Electricity']
        html_peak = generate_sunburst_row(
            peak_df, 'Peak_Demand_GW', peak_path, peak_colors
        )

        return HTML_TEMPLATE.format(
            css_styles=CSS_STYLES,
            nav_bar_html=dynamic_navbar,
            page_title=page_title,
            energy_charts_html=html_eng,
            emissions_charts_html=html_emi,
            peak_charts_html=html_peak,
            cap_cost_charts_html=html_cap,
            energy_cost_charts_html=html_enc
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
    df_2050 = df[df['Year'] == 2050]
    if not df_2050.empty:
        
        agg_dict = {
            'Energy_Use_TBtu': 'sum',
            'Emissions_MTCO2e': 'sum',
            'Capital_Cost_M$': 'sum',
            'Energy_Cost_M$': 'sum'
        }
        map_df_all = df_2050.groupby('Region').agg(agg_dict).reset_index()
        
        peak_df = df_2050[df_2050['Fuel_Type'] == 'Electricity']
        map_df_peak = peak_df.groupby('Region')['Peak_Demand_GW'].sum().reset_index()
        map_df_all = map_df_all.merge(map_df_peak, on='Region', how='left')

        def generate_map_panel(data, metric, title):
            fig = px.choropleth(
                data, locations='Region', locationmode="USA-states",
                color=metric, scope="usa", title=title, 
                color_continuous_scale="Teal"
            )
            fig.update_layout(
                font=dict(family=GITHUB_FONT, size=12),
                margin=dict(t=40, l=0, r=0, b=0),
                coloraxis_colorbar=dict(title=None, thickness=10, len=0.7),
                autosize=True
            )
            
            return fig.to_html(
                full_html=False, 
                include_plotlyjs=False, 
                default_width='100%',
                default_height='400px',
                config={'responsive': True}
            )

        map_eng = generate_map_panel(map_df_all, 'Energy_Use_TBtu', "Energy Use (TBtu)")
        map_peak = generate_map_panel(map_df_all, 'Peak_Demand_GW', "Peak Demand (GW)")
        map_emi = generate_map_panel(map_df_all, 'Emissions_MTCO2e', "Emissions (MTCO2e)")
        map_cap = generate_map_panel(map_df_all, 'Capital_Cost_M$', "Capital Cost (M$)")
        map_enc = generate_map_panel(map_df_all, 'Energy_Cost_M$', "Energy Cost (M$)")
        
        final_idx_html = INDEX_TEMPLATE.format(
            css_styles=CSS_STYLES,
            nav_bar_html=dynamic_navbar,
            map_energy=map_eng,
            map_peak=map_peak,
            map_emissions=map_emi,
            map_capcost=map_cap,
            map_energycost=map_enc
        )
    else:
        final_idx_html = "<p>No map data available for 2050.</p>"

    with open(os.path.join(output_dir, "index.html"), "w") as f:
        f.write(final_idx_html)

    print("All pages generated successfully!")


if __name__ == "__main__":
    main()
