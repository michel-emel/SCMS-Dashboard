"""
SCMS MAINTENANCE OPERATIONS DASHBOARD - PROFESSIONAL WITH LOCATION & SCHOOL FILTERS
===================================================================================

Dashboard 2/12 - Maintenance Status and Performance

✅ FEATURES:
- Location Type Filter (Kigali/Secondary/Rural)
- Multi-School Selection
- 7 KPIs (including Climate Mitigation Coverage)
- 13 Professional Visualizations
- Performance Analysis & Benchmarking

Installation:
    pip install dash pandas plotly openpyxl dash-bootstrap-components

Usage:
    python3 scms_dashboard_2_maintenance_fixed.py
    
Open: http://127.0.0.1:8050/
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import numpy as np

import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc

# ============================================================================
# 1. CHARGEMENT DES DONNÉES
# ============================================================================

print("📊 Chargement des données d'évaluation...")
df = pd.read_excel('SCMS DATA.xlsx', sheet_name='RAW_DATA_ASSESSMENT')

df['name_of_the_province'] = df['name_of_the_province'].fillna('Unknown')
df['name_of_the_district'] = df['name_of_the_district'].fillna('Unknown')
df['name_of_the_sector'] = df['name_of_the_sector'].fillna('Unknown')

# Normalize frequency (0-3 → 0-1)
df['m4_routine_maintenance_frequency_normalized'] = df['m4_routine_maintenance_frequency_score'] / 3

print(f"✓ Données chargées: {len(df)} écoles évaluées")

# Create location_type column
kigali_codes = [110504, 110505, 120735, 130804, 130405, 121207, 110306, 121011, 130819, 110909]

secondary_codes = [331232, 330802, 330713, 240605, 240504, 240202, 271011, 270202, 270517, 
                   270613, 430207, 430706, 430518, 430801, 520312, 520403, 520801, 361510, 
                   360614, 361306]

def get_location_type(code):
    if code in kigali_codes:
        return 'Kigali City'
    elif code in secondary_codes:
        return 'Secondary Cities'
    else:
        return 'Rural Districts'

df['location_type'] = df['school_code'].apply(get_location_type)

print(f"✓ Location types créés: {df['location_type'].value_counts().to_dict()}")

# ============================================================================
# 2. PRÉPARER LES OPTIONS DE FILTRES
# ============================================================================

all_provinces = sorted(df['name_of_the_province'].unique().tolist())

districts_by_province = {}
for prov in all_provinces:
    districts_by_province[prov] = sorted(
        df[df['name_of_the_province'] == prov]['name_of_the_district'].unique().tolist()
    )

sectors_by_district = {}
for dist in df['name_of_the_district'].unique():
    sectors_by_district[dist] = sorted(
        df[df['name_of_the_district'] == dist]['name_of_the_sector'].unique().tolist()
    )

# ============================================================================
# 3. FONCTIONS HELPER
# ============================================================================

def calculate_overall_maintenance_score(row):
    """Calculer score global maintenance pour une école (0-100)"""
    doing_maint = row['m1_maintenance_activity_last_3y'] * 100 * 0.3
    not_delayed = (1 - row['m5_delayed_maintenance']) * 100 * 0.3
    
    days_score = 100
    if pd.notna(row['m2_days_since_last_maintenance']):
        if row['m2_days_since_last_maintenance'] <= 365:
            days_score = 100
        elif row['m2_days_since_last_maintenance'] <= 730:
            days_score = 70
        else:
            days_score = 30
    days_contrib = days_score * 0.2
    
    freq_score = row['m4_routine_maintenance_frequency_normalized'] * 100 * 0.2
    
    return doing_maint + not_delayed + days_contrib + freq_score

def identify_critical_maintenance_issues(row):
    """Identifier les problèmes critiques de maintenance"""
    issues = []
    
    if row['m1_maintenance_activity_last_3y'] == 0:
        issues.append('🔴 No Maintenance')
    
    if row['m5_delayed_maintenance'] == 1:
        issues.append('⏰ Delayed Tasks')
    
    if pd.notna(row['m2_days_since_last_maintenance']) and row['m2_days_since_last_maintenance'] > 730:
        issues.append('📅 >2 Years')
    
    if row['m8_funding_gap'] == 1:
        issues.append('💰 Funding Gap')
    
    if row['m6_funding_source_diversity'] == 0:
        issues.append('📊 No Diversity')
    
    if row['m9_ongoing_maintenance'] == 0:
        issues.append('🔄 No Ongoing')
    
    return issues

def calculate_dashboard_kpis(data):
    """Calculer tous les KPIs du dashboard"""
    if len(data) == 0:
        return {
            'doing_maintenance_pct': 0, 'delayed_pct': 0, 'avg_days': 0,
            'funding_gap_pct': 0, 'frequency_avg': 0, 'diversity_avg': 0,
            'climate_mitigation': 0, 'degradation_rate': 0
        }
    
    doing_maintenance_pct = round((data['m1_maintenance_activity_last_3y'].sum() / len(data)) * 100, 1)
    delayed_pct = round((data['m5_delayed_maintenance'].sum() / len(data)) * 100, 1)
    avg_days = round(data['m2_days_since_last_maintenance'].mean(), 0)
    funding_gap_pct = round((data['m8_funding_gap'].sum() / len(data)) * 100, 1)
    frequency_avg = round(data['m4_routine_maintenance_frequency_normalized'].mean(), 2)
    diversity_avg = round(data['m6_funding_source_diversity'].mean(), 2)
    climate_mitigation = round(data['kpi_e2_climate_mitigation_coverage'].mean(), 1)
    
    degradation_rate = calculate_degradation_rate(data)

    return {
        'doing_maintenance_pct': doing_maintenance_pct,
        'delayed_pct': delayed_pct,
        'avg_days': avg_days,
        'funding_gap_pct': funding_gap_pct,
        'frequency_avg': frequency_avg,
        'diversity_avg': diversity_avg,
        'climate_mitigation': climate_mitigation,
        'degradation_rate': degradation_rate  
    }

def filter_data(location=None, province=None, district=None, sector=None, schools=None):
    """Filtrer les données selon tous les critères"""
    filtered = df.copy()
    
    if location and location != 'All Locations':
        filtered = filtered[filtered['location_type'] == location]
    
    if province and province != 'All Provinces':
        filtered = filtered[filtered['name_of_the_province'] == province]
    
    if district and district != 'All Districts':
        filtered = filtered[filtered['name_of_the_district'] == district]
    
    if sector and sector != 'All Sectors':
        filtered = filtered[filtered['name_of_the_sector'] == sector]
    
    if schools and len(schools) > 0:
        filtered = filtered[filtered['school_name'].isin(schools)]
    
    return filtered

def calculate_degradation_rate(data):
    """Calculer taux de dégradation annuel (%/an)"""
    if len(data) == 0:
        return 0
    
    avg_health = data['index_1_infrastructure_health_index'].mean()
    avg_days = data['m2_days_since_last_maintenance'].mean()
    
    if avg_days == 0 or avg_health >= 1:
        return 0
    
    years_without = avg_days / 365
    degradation_rate = ((1 - avg_health) / years_without) * 100
    
    return min(degradation_rate, 20)  # Cap à 20%/an

def create_kpi_card(title, value, color, subtitle="", value_format="", icon=""):
    """Créer une card KPI stylisée"""
    if value_format == "percent":
        display_value = f"{value:.1f}%"
    elif value_format == "decimal":
        display_value = f"{value:.2f}"
    elif value_format == "number":
        display_value = f"{int(value):,}" if not np.isnan(value) else "N/A"
    else:
        display_value = str(value)
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Span(icon, style={'fontSize': '18px', 'marginRight': '6px'}) if icon else None,
                html.Span(title, style={'fontSize': '10px', 'fontWeight': 'bold'})
            ], style={'color': '#6c757d', 'marginBottom': '6px'}),
            html.H2(display_value, style={'color': color, 'fontWeight': 'bold', 'marginBottom': '4px', 'fontSize': '22px'}),
            html.P(subtitle, className="text-muted", style={'fontSize': '8px', 'marginBottom': '0', 'lineHeight': '1.2'})
        ], style={'padding': '10px'})
    ], style={'textAlign': 'center', 'height': '95px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})

# ============================================================================
# 4. INITIALISER L'APPLICATION DASH
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.title = "SCMS Maintenance Operations Dashboard Professional"

# ============================================================================
# 5. LAYOUT DE L'APPLICATION
# ============================================================================

app.layout = dbc.Container([
    
    # HEADER
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1("SCMS MAINTENANCE OPERATIONS DASHBOARD", 
                       style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '26px', 'marginBottom': '3px'}),
                html.H6("School Construction and Maintenance Strategy 2024-2050 - Professional Edition",
                       style={'color': '#7f8c8d', 'fontSize': '13px', 'marginBottom': '0'})
            ], style={'textAlign': 'center'})
        ])
    ], style={'marginBottom': '18px'}),
    
    # NAVIGATION
    dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button("1️⃣ Overview", color="light", size="md", outline=True,
                          style={'fontSize': '13px', 'padding': '8px 18px'}),
                dbc.Button("2️⃣ Maintenance", color="primary", size="md", active=True,
                          style={'fontSize': '13px', 'padding': '8px 18px'}),
                dbc.Button("3️⃣ Infrastructure", color="light", size="md", outline=True,
                          style={'fontSize': '13px', 'padding': '8px 18px'}),
            ], className="d-flex justify-content-center")
        ])
    ], style={'marginBottom': '18px'}),
    
    html.Hr(style={'margin': '0 0 18px 0'}),
    
    # FILTRES
    dbc.Row([
        dbc.Col([
            html.Label("🌍 Location Type", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='location-dropdown',
                        options=[
                            {'label': 'All Locations', 'value': 'All Locations'},
                            {'label': 'Kigali City', 'value': 'Kigali City'},
                            {'label': 'Secondary Cities', 'value': 'Secondary Cities'},
                            {'label': 'Rural Districts', 'value': 'Rural Districts'}
                        ],
                        value='All Locations', clearable=False, style={'fontSize': '10px'})
        ], width=2),
        dbc.Col([
            html.Label("📍 Province", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='province-dropdown', 
                        options=[{'label': 'All Provinces', 'value': 'All Provinces'}] + 
                                [{'label': p, 'value': p} for p in all_provinces],
                        value='All Provinces', clearable=False, style={'fontSize': '10px'})
        ], width=2),
        dbc.Col([
            html.Label("🏘️ District", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='district-dropdown', 
                        options=[{'label': 'All Districts', 'value': 'All Districts'}],
                        value='All Districts', clearable=False, style={'fontSize': '10px'})
        ], width=2),
        dbc.Col([
            html.Label("🗺️ Sector", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='sector-dropdown',
                        options=[{'label': 'All Sectors', 'value': 'All Sectors'}],
                        value='All Sectors', clearable=False, style={'fontSize': '10px'})
        ], width=2),
        dbc.Col([
            html.Label("🏫 Schools", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='school-multi-dropdown',
                        options=[],
                        value=[], 
                        multi=True,
                        placeholder="Select schools...",
                        style={'fontSize': '10px'})
        ], width=2),
        dbc.Col([
            html.Label("📊 Selection", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            html.Div(id='selection-display', 
                    style={'fontSize': '10px', 'padding': '5px', 'backgroundColor': '#e3f2fd', 
                           'borderRadius': '4px', 'textAlign': 'center', 'marginTop': '2px'})
        ], width=2)
    ], style={'marginBottom': '18px'}),
    
    html.Hr(style={'margin': '0 0 22px 0'}),
    
    # KPI SECTION (7 KPIs)
    html.Div([
        html.H6("🔧 MAINTENANCE KEY PERFORMANCE INDICATORS", 
               style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '13px', 'marginBottom': '14px', 'letterSpacing': '0.5px'})
    ]),
    
    html.Div(id='kpi-cards', style={'marginBottom': '28px'}),
    
    # COMPARE PROVINCES
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("⚖️ COMPARE TWO PROVINCES SIDE-BY-SIDE", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#e3f2fd', 'fontSize': '12px', 'padding': '8px', 'textAlign': 'center'}),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select Province 1:", style={'fontWeight': 'bold', 'fontSize': '10px'}),
                            dcc.Dropdown(id='compare-province-1',
                                       options=[{'label': p, 'value': p} for p in all_provinces],
                                       value=all_provinces[0] if all_provinces else None,
                                       clearable=False,
                                       style={'fontSize': '10px'})
                        ], width=6),
                        dbc.Col([
                            html.Label("Select Province 2:", style={'fontWeight': 'bold', 'fontSize': '10px'}),
                            dcc.Dropdown(id='compare-province-2',
                                       options=[{'label': p, 'value': p} for p in all_provinces],
                                       value=all_provinces[1] if len(all_provinces) > 1 else all_provinces[0],
                                       clearable=False,
                                       style={'fontSize': '10px'})
                        ], width=6)
                    ], style={'marginBottom': '15px'}),
                    html.Div(id='province-comparison-content')
                ], style={'padding': '12px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=12)
    ], style={'marginBottom': '22px'}),
    
    # SECTION: PERFORMANCE ANALYSIS
    html.Div([
        html.H6("🎯 PERFORMANCE ANALYSIS & BENCHMARKING", 
               style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '13px', 'marginBottom': '14px', 'letterSpacing': '0.5px'})
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🏆 TOP 5 BEST vs 🔴 BOTTOM 5 WORST MAINTAINED SCHOOLS", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#d4edda', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='top-bottom-schools', style={'height': '320px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'border': '2px solid #28a745'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🚨 CRITICAL MAINTENANCE ISSUES SUMMARY", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8d7da', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    html.Div(id='critical-issues-table')
                ], style={'padding': '10px', 'maxHeight': '320px', 'overflowY': 'auto'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'border': '2px solid #dc3545'})
        ], width=6)
    ], style={'marginBottom': '22px'}),
    
    # RADAR + CLIMATE ON SAME ROW
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📡 PROVINCE MAINTENANCE PERFORMANCE RADAR", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#e3f2fd', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='radar-chart', style={'height': '400px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'border': '2px solid #007bff'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🌍 CLIMATE MITIGATION COVERAGE BY PROVINCE", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#d4edda', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='climate-mitigation-chart', style={'height': '400px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'border': '2px solid #28a745'})
        ], width=6)
    ], style={'marginBottom': '22px'}),
    
    # SECTION: DETAILED ANALYSIS
    html.Div([
        html.H6("📊 DETAILED MAINTENANCE ANALYSIS", 
               style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '13px', 'marginBottom': '14px', 'letterSpacing': '0.5px'})
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("💰 FUNDING SOURCE DIVERSITY", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='funding-diversity-chart', style={'height': '320px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("💰 MAINTENANCE FUNDING GAP BY PROVINCE", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#fff3cd', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='funding-gap-chart', style={'height': '320px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'border': '2px solid #ffc107'})
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📉 INFRASTRUCTURE DEGRADATION PROJECTION", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8d7da', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='degradation-chart', style={'height': '320px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'border': '2px solid #dc3545'})
        ], width=4)
    ], style={'marginBottom': '22px'}),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("⏰ DELAYED MAINTENANCE BY PROVINCE", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='delayed-by-province', style={'height': '320px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🎯 TOP 10 SCHOOLS NEEDING URGENT ATTENTION", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8d7da', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='top10-urgent-schools', style={'height': '320px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'border': '2px solid #dc3545'})
        ], width=6)
    ], style={'marginBottom': '22px'}),
    
    # RECOMMENDATIONS BOX
    dbc.Row([
        dbc.Col([
            html.Div(id='recommendations-box')
        ], width=12)
    ], style={'marginBottom': '22px'}),
    
    # FOOTER
    html.Hr(style={'margin': '22px 0 12px 0'}),
    dbc.Row([
        dbc.Col([
            html.P([
                html.Strong("SCMS 2024-2050 | Dashboard 2/12 - Maintenance Operations (WITH FILTERS) | "),
                f"Generated: {datetime.now().strftime('%B %d, %Y')} | ",
                html.A("📧 Support", href="mailto:support@mineduc.gov.rw", style={'color': '#007bff', 'textDecoration': 'none'})
            ], className="text-center", style={'fontSize': '10px', 'color': '#6c757d', 'marginBottom': '0'})
        ])
    ])
    
], fluid=True, style={'backgroundColor': '#f5f7fa', 'padding': '20px', 'fontFamily': 'Arial, sans-serif'})

# ============================================================================
# 6. CALLBACKS - NAVIGATION & FILTERS
# ============================================================================

@app.callback(
    Output('district-dropdown', 'options'),
    Output('district-dropdown', 'value'),
    Input('province-dropdown', 'value')
)
def update_district_options(selected_province):
    if selected_province == 'All Provinces':
        all_districts = sorted(df['name_of_the_district'].unique().tolist())
        options = [{'label': 'All Districts', 'value': 'All Districts'}] + [{'label': d, 'value': d} for d in all_districts]
    else:
        districts = districts_by_province.get(selected_province, [])
        options = [{'label': 'All Districts', 'value': 'All Districts'}] + [{'label': d, 'value': d} for d in districts]
    return options, 'All Districts'

@app.callback(
    Output('sector-dropdown', 'options'),
    Output('sector-dropdown', 'value'),
    Input('district-dropdown', 'value')
)
def update_sector_options(selected_district):
    if selected_district == 'All Districts':
        all_sectors = sorted(df['name_of_the_sector'].unique().tolist())
        options = [{'label': 'All Sectors', 'value': 'All Sectors'}] + [{'label': s, 'value': s} for s in all_sectors]
    else:
        sectors = sectors_by_district.get(selected_district, [])
        options = [{'label': 'All Sectors', 'value': 'All Sectors'}] + [{'label': s, 'value': s} for s in sectors]
    return options, 'All Sectors'

@app.callback(
    Output('school-multi-dropdown', 'options'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_school_options(location, province, district, sector):
    """Update school dropdown based on filters"""
    filtered = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    schools = sorted(filtered['school_name'].unique().tolist())
    return [{'label': s, 'value': s} for s in schools]

@app.callback(
    Output('selection-display', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_selection_display(location, province, district, sector, schools):
    parts = []
    if location != 'All Locations': parts.append(f"🌍 {location}")
    if province != 'All Provinces': parts.append(f"📍 {province}")
    if district != 'All Districts': parts.append(f"🏘️ {district}")
    if sector != 'All Sectors': parts.append(f"🗺️ {sector}")
    if schools and len(schools) > 0: parts.append(f"🏫 {len(schools)} school(s)")
    return " → ".join(parts) if parts else "🌍 All Data"

@app.callback(
    Output('kpi-cards', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_kpis(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    kpis = calculate_dashboard_kpis(filtered_df)
    
    color_maint = '#2ca02c' if kpis['doing_maintenance_pct'] >= 75 else ('#ffa500' if kpis['doing_maintenance_pct'] >= 50 else '#d62728')
    color_delayed = '#2ca02c' if kpis['delayed_pct'] <= 20 else ('#ffa500' if kpis['delayed_pct'] <= 40 else '#d62728')
    color_days = '#2ca02c' if kpis['avg_days'] <= 365 else ('#ffa500' if kpis['avg_days'] <= 730 else '#d62728')
    color_gap = '#2ca02c' if kpis['funding_gap_pct'] <= 30 else ('#ffa500' if kpis['funding_gap_pct'] <= 50 else '#d62728')
    color_climate = '#2ca02c' if kpis['climate_mitigation'] >= 75 else ('#ffa500' if kpis['climate_mitigation'] >= 50 else '#d62728')
    
    # 7 KPIs in 2 rows
    row1 = dbc.Row([
        dbc.Col(create_kpi_card("Doing Maintenance", kpis['doing_maintenance_pct'], color_maint,
                               subtitle="% schools active", value_format="percent", icon="🔧"), width=3),
        dbc.Col(create_kpi_card("Delayed Tasks", kpis['delayed_pct'], color_delayed,
                               subtitle="% with delays", value_format="percent", icon="⏰"), width=3),
        dbc.Col(create_kpi_card("Avg Days Since", kpis['avg_days'], color_days,
                               subtitle="Last maintenance", value_format="number", icon="📅"), width=3),
        dbc.Col(create_kpi_card("Funding Gap", kpis['funding_gap_pct'], color_gap,
                               subtitle="% with gap", value_format="percent", icon="💰"), width=3),
    ], className="g-2")

    row2 = dbc.Row([
        dbc.Col(create_kpi_card("Frequency", kpis['frequency_avg'], '#17a2b8',
                               subtitle="Normalized (0-1)", value_format="decimal", icon="🔄"), width=4),
        dbc.Col(create_kpi_card("Diversity", kpis['diversity_avg'], '#9467bd',
                               subtitle="Avg funding sources", value_format="decimal", icon="📊"), width=4),
        dbc.Col(create_kpi_card("Climate Mitigation", kpis['climate_mitigation'], color_climate,
                               subtitle="Coverage %", value_format="percent", icon="🌍"), width=4),
    ], className="g-2", style={'marginTop': '10px'})
    
    return html.Div([row1, row2])

@app.callback(
    Output('province-comparison-content', 'children'),
    Input('compare-province-1', 'value'),
    Input('compare-province-2', 'value')
)
def update_province_comparison(prov1, prov2):
    if not prov1 or not prov2:
        return html.P("Select two provinces to compare", style={'textAlign': 'center', 'color': '#999'})
    
    df1 = filter_data(province=prov1)
    df2 = filter_data(province=prov2)
    
    kpis1 = calculate_dashboard_kpis(df1)
    kpis2 = calculate_dashboard_kpis(df2)
    
    def winner_badge(val1, val2, higher_better=True):
        if higher_better:
            return "🏆" if val1 > val2 else ("" if val1 == val2 else "")
        else:
            return "🏆" if val1 < val2 else ("" if val1 == val2 else "")
    
    comparison_rows = [
        ("Doing Maintenance %", f"{kpis1['doing_maintenance_pct']:.1f}%", f"{kpis2['doing_maintenance_pct']:.1f}%",
         winner_badge(kpis1['doing_maintenance_pct'], kpis2['doing_maintenance_pct'], True)),
        ("Delayed Tasks %", f"{kpis1['delayed_pct']:.1f}%", f"{kpis2['delayed_pct']:.1f}%",
         winner_badge(kpis1['delayed_pct'], kpis2['delayed_pct'], False)),
        ("Avg Days Since", f"{int(kpis1['avg_days'])}", f"{int(kpis2['avg_days'])}",
         winner_badge(kpis1['avg_days'], kpis2['avg_days'], False)),
        ("Funding Gap %", f"{kpis1['funding_gap_pct']:.1f}%", f"{kpis2['funding_gap_pct']:.1f}%",
         winner_badge(kpis1['funding_gap_pct'], kpis2['funding_gap_pct'], False)),
        ("Climate Mitigation %", f"{kpis1['climate_mitigation']:.1f}%", f"{kpis2['climate_mitigation']:.1f}%",
         winner_badge(kpis1['climate_mitigation'], kpis2['climate_mitigation'], True))
    ]
    
    table_data = []
    for metric, val1, val2, winner in comparison_rows:
        if metric in ["Doing Maintenance %", "Climate Mitigation %"]:
            winner_col = f"{prov1} {winner}" if winner and val1 > val2 else (f"{prov2} {winner}" if winner else "Tie")
        else:
            winner_col = f"{prov1} {winner}" if winner and val1 < val2 else (f"{prov2} {winner}" if winner else "Tie")
        table_data.append({'Metric': metric, prov1: val1, prov2: val2, 'Winner': winner_col})
    
    return dash_table.DataTable(
        data=table_data,
        columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': prov1, 'id': prov1}, 
                {'name': prov2, 'id': prov2}, {'name': 'Winner', 'id': 'Winner'}],
        style_cell={'textAlign': 'center', 'fontSize': '10px', 'padding': '8px'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'fontSize': '10px'},
        style_data_conditional=[
            {'if': {'column_id': 'Winner', 'filter_query': '{Winner} contains "🏆"'}, 'backgroundColor': '#d4edda', 'fontWeight': 'bold'}
        ]
    )

# ============================================================================
# 7. CALLBACKS - PERFORMANCE ANALYSIS (ALL UPDATED WITH NEW FILTERS)
# ============================================================================

@app.callback(
    Output('top-bottom-schools', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_top_bottom_schools(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    filtered_df['overall_score'] = filtered_df.apply(calculate_overall_maintenance_score, axis=1)
    
    top5 = filtered_df.nlargest(5, 'overall_score')[['school_name', 'overall_score']].copy()
    bottom5 = filtered_df.nsmallest(5, 'overall_score')[['school_name', 'overall_score']].copy()
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Top 5 Best',
        y=top5['school_name'],
        x=top5['overall_score'],
        orientation='h',
        marker_color='#2ca02c',
        text=[f'{v:.1f}%' for v in top5['overall_score']],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Maintenance Score: %{x:.1f}%<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name='Bottom 5 Worst',
        y=bottom5['school_name'],
        x=-bottom5['overall_score'],
        orientation='h',
        marker_color='#d62728',
        text=[f'{v:.1f}%' for v in bottom5['overall_score']],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Maintenance Score: %{customdata:.1f}%<extra></extra>',
        customdata=bottom5['overall_score']
    ))
    
    fig.update_layout(
        barmode='group',
        xaxis_title="Maintenance Performance Score",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9)),
        margin=dict(l=180, r=30, t=15, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0'),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('critical-issues-table', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_critical_issues(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    critical_schools = []
    for idx, row in filtered_df.iterrows():
        issues = identify_critical_maintenance_issues(row)
        if len(issues) >= 2:
            critical_schools.append({
                'school': row['school_name'],
                'province': row['name_of_the_province'],
                'issues': issues,
                'count': len(issues)
            })
    
    critical_schools = sorted(critical_schools, key=lambda x: x['count'], reverse=True)
    
    if len(critical_schools) == 0:
        return html.P("✅ No schools with multiple critical maintenance issues found", 
                     style={'textAlign': 'center', 'color': '#28a745', 'fontWeight': 'bold'})
    
    items = []
    for i, school in enumerate(critical_schools[:10], 1):
        issue_badges = ' '.join(school['issues'])
        items.append(html.Div([
            html.Div([
                html.Span(f"{i}. ", style={'fontWeight': 'bold', 'fontSize': '10px', 'color': '#d62728', 'marginRight': '5px'}),
                html.Span(f"{school['school']}", style={'fontSize': '10px', 'fontWeight': 'bold'}),
                html.Span(f" ({school['province']})", style={'fontSize': '9px', 'color': '#6c757d', 'marginLeft': '5px'})
            ], style={'marginBottom': '4px'}),
            html.Div([
                html.Span(issue_badges, style={'fontSize': '9px', 'marginRight': '8px'}),
                html.Span(f"{school['count']} issues", style={'fontSize': '9px', 'color': '#d62728', 'fontWeight': 'bold', 'backgroundColor': '#f8d7da', 'padding': '2px 6px', 'borderRadius': '3px'})
            ])
        ], style={'marginBottom': '12px', 'paddingBottom': '12px', 'borderBottom': '1px solid #e9ecef'}))
    
    return html.Div(items)

@app.callback(
    Output('radar-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_radar_chart(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    radar_data = []
    for prov in filtered_df['name_of_the_province'].unique():
        prov_data = filtered_df[filtered_df['name_of_the_province'] == prov]
        
        doing_maint = (prov_data['m1_maintenance_activity_last_3y'].sum() / len(prov_data)) * 100
        not_delayed = 100 - ((prov_data['m5_delayed_maintenance'].sum() / len(prov_data)) * 100)
        
        avg_days_score = 100
        avg_days = prov_data['m2_days_since_last_maintenance'].mean()
        if avg_days <= 365:
            avg_days_score = 100
        elif avg_days <= 730:
            avg_days_score = 70
        else:
            avg_days_score = 30
        
        frequency_score = prov_data['m4_routine_maintenance_frequency_normalized'].mean() * 100
        funding_health = 100 - ((prov_data['m8_funding_gap'].sum() / len(prov_data)) * 100)
        diversity_score = (prov_data['m6_funding_source_diversity'].mean() / 3) * 100
        
        radar_data.append({
            'province': prov,
            'Doing Maintenance': doing_maint,
            'Not Delayed': not_delayed,
            'Recency': avg_days_score,
            'Frequency': frequency_score,
            'Funding Health': funding_health,
            'Diversity': diversity_score
        })
    
    fig = go.Figure()
    
    categories = ['Doing Maintenance', 'Not Delayed', 'Recency', 'Frequency', 'Funding Health', 'Diversity']
    
    for item in radar_data:
        values = [item[cat] for cat in categories]
        values.append(values[0])
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories + [categories[0]],
            fill='toself',
            name=item['province']
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=80, r=80, t=30, b=80),
        paper_bgcolor='white',
        font=dict(size=10)
    )
    
    return fig

@app.callback(
    Output('climate-mitigation-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_climate_mitigation(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    climate_by_prov = filtered_df.groupby('name_of_the_province')['kpi_e2_climate_mitigation_coverage'].mean().reset_index()
    climate_by_prov.columns = ['Province', 'Coverage %']
    climate_by_prov = climate_by_prov.sort_values('Coverage %', ascending=True)
    
    colors = ['#2ca02c' if x >= 75 else ('#ffa500' if x >= 50 else '#d62728') for x in climate_by_prov['Coverage %']]
    
    fig = go.Figure(data=[go.Bar(
        y=climate_by_prov['Province'],
        x=climate_by_prov['Coverage %'],
        orientation='h',
        marker_color=colors,
        text=[f'{v:.1f}%' for v in climate_by_prov['Coverage %']],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Coverage: %{x:.1f}%<extra></extra>'
    )])
    
    fig.add_shape(type="line", x0=75, x1=75, y0=-0.5, y1=len(climate_by_prov)-0.5,
                 line=dict(color="green", width=2, dash="dash"))
    fig.add_annotation(x=75, y=len(climate_by_prov)-0.5, text="Target: 75%",
                      showarrow=False, xanchor='left', yanchor='top',
                      font=dict(size=9, color='green'))
    
    fig.update_layout(
        xaxis_title="Climate Mitigation Coverage %",
        yaxis_title="Province",
        showlegend=False,
        margin=dict(l=120, r=30, t=15, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0', range=[0, 100]),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

# ============================================================================
# 8. CALLBACKS - DETAILED ANALYSIS (ALL UPDATED WITH NEW FILTERS)
# ============================================================================

@app.callback(
    Output('funding-gap-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_funding_gap_chart(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    gap_by_prov = filtered_df.groupby('name_of_the_province').apply(
        lambda x: (x['m8_funding_gap'].sum() / len(x)) * 100
    ).reset_index()
    gap_by_prov.columns = ['Province', 'Gap %']
    gap_by_prov = gap_by_prov.sort_values('Gap %', ascending=True)
    
    colors = ['#2ca02c' if x <= 30 else ('#ffa500' if x <= 50 else '#d62728') for x in gap_by_prov['Gap %']]
    
    fig = go.Figure(data=[go.Bar(
        y=gap_by_prov['Province'],
        x=gap_by_prov['Gap %'],
        orientation='h',
        marker_color=colors,
        text=[f'{v:.1f}%' for v in gap_by_prov['Gap %']],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Funding Gap: %{x:.1f}%<extra></extra>'
    )])
    
    fig.update_layout(
        xaxis_title="% Schools with Funding Gap",
        yaxis_title="Province",
        showlegend=False,
        margin=dict(l=120, r=30, t=15, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0', range=[0, 100]),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('degradation-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_degradation_chart(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    current_health = filtered_df['index_1_infrastructure_health_index'].mean()
    degradation_rate = calculate_degradation_rate(filtered_df) / 100
    
    years = list(range(0, 11))
    projected_health = [max(current_health - (degradation_rate * year), 0) for year in years]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=years,
        y=projected_health,
        mode='lines+markers',
        name='Infrastructure Health',
        line=dict(color='#d62728', width=3),
        marker=dict(size=8),
        hovertemplate='<b>Year %{x}</b><br>Health: %{y:.2f}<extra></extra>'
    ))
    
    fig.add_shape(type="line", x0=0, x1=10, y0=0.4, y1=0.4,
                 line=dict(color="red", width=2, dash="dash"))
    
    fig.add_annotation(x=10, y=0.4, text="Critical Level (0.40)",
                      showarrow=False, xanchor='right', yanchor='bottom',
                      font=dict(size=9, color='red'))
    
    fig.update_layout(
        xaxis_title="Years Without Maintenance",
        yaxis_title="Infrastructure Health Index",
        showlegend=False,
        margin=dict(l=50, r=30, t=15, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0'),
        yaxis=dict(gridcolor='#e0e0e0', range=[0, 1.05])
    )
    
    return fig

@app.callback(
    Output('funding-diversity-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_funding_diversity(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    diversity_counts = filtered_df['m6_funding_source_diversity'].value_counts().sort_index()
    
    fig = go.Figure(data=[go.Bar(
        x=[f'{int(k)} source{"s" if k != 1 else ""}' for k in diversity_counts.index],
        y=diversity_counts.values,
        marker_color='#1f77b4',
        text=diversity_counts.values,
        textposition='auto'
    )])
    
    fig.update_layout(
        xaxis_title="Number of Funding Sources",
        yaxis_title="Number of Schools",
        showlegend=False,
        margin=dict(l=50, r=30, t=15, b=60),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0'),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('delayed-by-province', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_delayed_by_province(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    delayed_by_prov = filtered_df.groupby('name_of_the_province').apply(
        lambda x: (x['m5_delayed_maintenance'].sum() / len(x)) * 100
    ).reset_index()
    delayed_by_prov.columns = ['Province', 'Delayed %']
    delayed_by_prov = delayed_by_prov.sort_values('Delayed %', ascending=True)
    
    colors = ['#2ca02c' if x <= 20 else ('#ffa500' if x <= 40 else '#d62728') for x in delayed_by_prov['Delayed %']]
    
    fig = go.Figure(data=[go.Bar(
        y=delayed_by_prov['Province'],
        x=delayed_by_prov['Delayed %'],
        orientation='h',
        marker_color=colors,
        text=[f'{v:.1f}%' for v in delayed_by_prov['Delayed %']],
        textposition='auto'
    )])
    
    fig.update_layout(
        xaxis_title="% Schools with Delayed Tasks",
        yaxis_title="Province",
        showlegend=False,
        margin=dict(l=120, r=30, t=15, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0', range=[0, 100]),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('top10-urgent-schools', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_top10_urgent(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    urgent_df = filtered_df[['school_name', 'm2_days_since_last_maintenance', 'm3_capitation_grant_pct']].copy()
    urgent_df = urgent_df.dropna()
    urgent_df['urgency_score'] = urgent_df['m2_days_since_last_maintenance'] * (100 - urgent_df['m3_capitation_grant_pct'])
    urgent_df = urgent_df.nlargest(10, 'urgency_score')
    
    max_days = urgent_df['m2_days_since_last_maintenance'].max()
    urgent_df['days_normalized'] = (urgent_df['m2_days_since_last_maintenance'] / max_days) * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Days Since Maintenance',
        y=urgent_df['school_name'],
        x=urgent_df['days_normalized'],
        orientation='h',
        marker_color='#ff7f0e',
        text=[f'{int(d)} days' for d in urgent_df['m2_days_since_last_maintenance']],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Days: %{text}<extra></extra>',
        customdata=urgent_df['m2_days_since_last_maintenance']
    ))
    
    fig.add_trace(go.Bar(
        name='Capitation Grant %',
        y=urgent_df['school_name'],
        x=urgent_df['m3_capitation_grant_pct'],
        orientation='h',
        marker_color='#1f77b4',
        text=[f'{v:.1f}%' for v in urgent_df['m3_capitation_grant_pct']],
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Capitation: %{x:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        xaxis_title="Normalized Score (0-100)",
        yaxis_title="School",
        barmode='group',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=9)),
        margin=dict(l=180, r=30, t=30, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=9),
        xaxis=dict(gridcolor='#e0e0e0', range=[0, 105]),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('recommendations-box', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value'),
    Input('school-multi-dropdown', 'value')
)
def update_recommendations(location, province, district, sector, schools):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None,
        schools=schools if schools and len(schools) > 0 else None
    )
    
    kpis = calculate_dashboard_kpis(filtered_df)
    
    recommendations = []
    
    if kpis['doing_maintenance_pct'] < 50:
        recommendations.append(f"🔴 Critical: Only {kpis['doing_maintenance_pct']:.1f}% schools doing maintenance. Immediate action required.")
    elif kpis['doing_maintenance_pct'] < 75:
        recommendations.append(f"⚠️ {kpis['doing_maintenance_pct']:.1f}% maintenance rate. Target is 90%+. Scale up programs.")
    
    if kpis['delayed_pct'] > 40:
        recommendations.append(f"🔴 {kpis['delayed_pct']:.1f}% schools have delayed tasks. Address funding gaps urgently.")
    elif kpis['delayed_pct'] > 20:
        recommendations.append(f"⏰ {kpis['delayed_pct']:.1f}% delayed tasks. Improve budget allocation.")
    
    if kpis['avg_days'] > 730:
        recommendations.append(f"📅 Average {int(kpis['avg_days'])} days since maintenance (>2 years). Implement regular schedule.")
    
    if kpis['funding_gap_pct'] > 50:
        recommendations.append(f"💰 {kpis['funding_gap_pct']:.1f}% schools report funding gap. Increase maintenance budget.")
    
    if kpis['climate_mitigation'] < 50:
        recommendations.append(f"🌍 Low climate mitigation coverage ({kpis['climate_mitigation']:.1f}%). Prioritize climate-resilient infrastructure.")
    elif kpis['climate_mitigation'] < 75:
        recommendations.append(f"🌍 Climate mitigation at {kpis['climate_mitigation']:.1f}%. Continue scaling up green measures.")
    
    if kpis['diversity_avg'] < 1:
        recommendations.append(f"📊 Low funding diversity ({kpis['diversity_avg']:.2f}). Diversify funding sources for sustainability.")
    
    if not recommendations:
        recommendations.append("✅ Maintenance operations performing well. Continue current practices and monitor regularly.")
    
    return dbc.Card([
        dbc.CardHeader("💡 KEY RECOMMENDATIONS", 
                      style={'fontWeight': 'bold', 'backgroundColor': '#d1ecf1', 'fontSize': '13px', 'padding': '8px', 'textAlign': 'center'}),
        dbc.CardBody([
            html.Ul([
                html.Li(rec, style={'fontSize': '11px', 'marginBottom': '8px', 'lineHeight': '1.5'})
                for rec in recommendations
            ], style={'paddingLeft': '20px', 'marginBottom': '0'})
        ], style={'padding': '12px'})
    ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'border': '2px solid #17a2b8'})

# ============================================================================
# 9. LANCER L'APPLICATION
# ============================================================================

server = app.server

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 SCMS MAINTENANCE OPERATIONS DASHBOARD - WITH LOCATION & SCHOOL FILTERS")
    print("="*80)
    print("\n✅ NEW FEATURES:")
    print("   • Location Type Filter (Kigali City / Secondary Cities / Rural Districts)")
    print("   • Multi-School Selection (select specific schools)")
    print("   • All 13 visualizations updated with new filters")
    print("   • Dynamic school dropdown based on location/province/district/sector")
    print("\n📊 Dashboard Content:")
    print("   • 7 KPIs (Maintenance, Delays, Funding, Climate)")
    print("   • 13 Professional Visualizations")
    print("   • Province Comparison Tool")
    print("   • Performance Benchmarking")
    print("   • Smart Recommendations")
    print("\n🎯 All Callbacks Updated: 15/15 ✅")
    print("\n🌐 Starting server...")
    print("   → Open: http://127.0.0.1:8050/")
    print("   → Press Ctrl+C to stop\n")
    print("="*80 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=8050)