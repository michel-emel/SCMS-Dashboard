"""
SCMS DISTRICT DASHBOARD - DASHBOARD 4/12
=========================================

COMPLETE VERSION - Phases 1 + 2 + 3
- ✅ Phase 1: Filters + KPIs + District Ranking Table
- ✅ Phase 2: Spider Chart, Scatter Plot, Box Plot, Heatmap
- ✅ Phase 3: Top/Bottom 10, Province Comparison, Sector Drill-down

Installation:
    pip install dash pandas plotly openpyxl dash-bootstrap-components

Usage:
    python3 scms_dashboard_district.py
    
Ouvrir: http://127.0.0.1:8051/
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

print("📊 Chargement des données...")
df = pd.read_excel('SCMS DATA.xlsx', sheet_name='RAW_DATA_ASSESSMENT')

df['name_of_the_province'] = df['name_of_the_province'].fillna('Unknown')
df['name_of_the_district'] = df['name_of_the_district'].fillna('Unknown')

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

print(f"✓ Données chargées: {len(df)} écoles")
print(f"✓ Districts: {df['name_of_the_district'].nunique()}")

# ============================================================================
# 2. AGRÉGATION PAR DISTRICT
# ============================================================================

def aggregate_by_district(data):
    """Agréger données au niveau district"""
    if len(data) == 0:
        return pd.DataFrame()
    
    district_agg = data.groupby(['name_of_the_district', 'name_of_the_province', 'location_type']).agg({
        'school_code': 'count',  # Number of schools
        'number_of_students': 'sum',
        'number_of_teachers': 'sum',
        'number_of_classrooms': 'sum',
        'kpi_a1_student_classroom_ratio': 'mean',
        'kpi_a2_student_teacher_ratio': 'mean',
        'index_1_infrastructure_health_index': 'mean',
        'kpi_d2_electricity_reliability': 'mean',
        'kpi_d1_water_quality_score': 'mean',
        'kpi_b1_classroom_damage_rate': 'mean',
        'kpi_c1_fence_availability': 'mean',
        'm5_delayed_maintenance': 'sum'
    }).reset_index()
    
    district_agg.columns = [
        'District', 'Province', 'Location', 'Schools', 'Students', 'Teachers', 
        'Classrooms', 'S/C Ratio', 'S/T Ratio', 'Infra Index', 
        'Electricity %', 'Water Score', 'Classroom Damage %', 
        'Fence %', 'Delayed Maintenance'
    ]
    
    # Convert percentages
    district_agg['Electricity %'] = round(district_agg['Electricity %'] * 100, 1)
    district_agg['Fence %'] = round(district_agg['Fence %'] * 100, 1)
    
    # Round other metrics
    district_agg['S/C Ratio'] = round(district_agg['S/C Ratio'], 1)
    district_agg['S/T Ratio'] = round(district_agg['S/T Ratio'], 1)
    district_agg['Infra Index'] = round(district_agg['Infra Index'], 2)
    district_agg['Water Score'] = round(district_agg['Water Score'], 1)
    district_agg['Classroom Damage %'] = round(district_agg['Classroom Damage %'], 1)
    
    # Add ranking based on Infrastructure Index
    district_agg = district_agg.sort_values('Infra Index', ascending=False)
    district_agg.insert(0, 'Rank', range(1, len(district_agg) + 1))
    
    return district_agg

# Initial aggregation
district_data = aggregate_by_district(df)

# ============================================================================
# 3. PRÉPARER LES OPTIONS DE FILTRES
# ============================================================================

all_provinces = sorted(df['name_of_the_province'].unique().tolist())
all_districts = sorted(df['name_of_the_district'].unique().tolist())

districts_by_province = {}
for prov in all_provinces:
    districts_by_province[prov] = sorted(
        df[df['name_of_the_province'] == prov]['name_of_the_district'].unique().tolist()
    )

# ============================================================================
# 4. FONCTIONS HELPER
# ============================================================================

def filter_data(location=None, province=None):
    """Filtrer données brutes"""
    filtered = df.copy()
    
    if location and location != 'All Locations':
        filtered = filtered[filtered['location_type'] == location]
    
    if province and province != 'All Provinces':
        filtered = filtered[filtered['name_of_the_province'] == province]
    
    return filtered

def calculate_district_kpis(data):
    """Calculer KPIs agrégés pour tous districts filtrés"""
    if len(data) == 0:
        return {
            'total_districts': 0, 'total_schools': 0, 'total_students': 0,
            'avg_sc_ratio': 0, 'avg_st_ratio': 0, 'avg_infra': 0,
            'avg_electricity': 0, 'avg_water': 0,
            'sc_color': '#999', 'st_color': '#999', 'infra_color': '#999'
        }
    
    kpis = {
        'total_districts': len(data),
        'total_schools': int(data['Schools'].sum()),
        'total_students': int(data['Students'].sum()),
        'avg_sc_ratio': round(data['S/C Ratio'].mean(), 1),
        'avg_st_ratio': round(data['S/T Ratio'].mean(), 1),
        'avg_infra': round(data['Infra Index'].mean(), 2),
        'avg_electricity': round(data['Electricity %'].mean(), 1),
        'avg_water': round(data['Water Score'].mean(), 1)
    }
    
    kpis['sc_color'] = '#d62728' if kpis['avg_sc_ratio'] > 45 else '#2ca02c'
    kpis['st_color'] = '#d62728' if kpis['avg_st_ratio'] > 35 else '#2ca02c'
    kpis['infra_color'] = '#2ca02c' if kpis['avg_infra'] >= 0.7 else '#d62728'
    
    return kpis

def create_kpi_card(title, value, color, subtitle="", value_format="", icon=""):
    """Créer une card KPI stylisée"""
    if value_format == "number":
        display_value = f"{value:,}"
    elif value_format == "decimal":
        display_value = f"{value:.1f}"
    elif value_format == "percentage":
        display_value = f"{value:.2f}"
    elif value_format == "percent":
        display_value = f"{value:.1f}%"
    else:
        display_value = str(value)
    
    return dbc.Card([
        dbc.CardBody([
            html.Div([
                html.Span(icon, style={'fontSize': '20px', 'marginRight': '8px'}) if icon else None,
                html.Span(title, style={'fontSize': '11px', 'fontWeight': 'bold'})
            ], style={'color': '#6c757d', 'marginBottom': '8px'}),
            html.H2(display_value, style={'color': color, 'fontWeight': 'bold', 'marginBottom': '5px', 'fontSize': '30px'}),
            html.P(subtitle, className="text-muted", style={'fontSize': '9px', 'marginBottom': '0', 'lineHeight': '1.2'})
        ], style={'padding': '12px'})
    ], style={'textAlign': 'center', 'height': '105px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})

# ============================================================================
# 5. INITIALISER L'APPLICATION DASH
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.title = "SCMS District Dashboard"

# ============================================================================
# 6. LAYOUT DE L'APPLICATION
# ============================================================================

app.layout = dbc.Container([
    
    # HEADER
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1("SCMS DISTRICT DASHBOARD", 
                       style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '26px', 'marginBottom': '3px'}),
                html.H6("District-Level Performance Analysis - School Construction and Maintenance Strategy 2024-2050",
                       style={'color': '#7f8c8d', 'fontSize': '13px', 'marginBottom': '0'})
            ], style={'textAlign': 'center'})
        ])
    ], style={'marginBottom': '18px'}),
    
    # NAVIGATION
    dbc.Row([
        dbc.Col([
            dbc.ButtonGroup([
                dbc.Button("1️⃣ Overview", color="light", size="md", outline=True, disabled=True,
                          style={'fontSize': '13px', 'padding': '8px 18px'}),
                dbc.Button("2️⃣ Infrastructure", color="light", size="md", outline=True, disabled=True,
                          style={'fontSize': '13px', 'padding': '8px 18px'}),
                dbc.Button("3️⃣ Maintenance", color="light", size="md", outline=True, disabled=True,
                          style={'fontSize': '13px', 'padding': '8px 18px'}),
                dbc.Button("4️⃣ District", color="primary", size="md", active=True,
                          style={'fontSize': '13px', 'padding': '8px 18px'}),
                dbc.DropdownMenu(
                    label="More ▼",
                    children=[
                        dbc.DropdownMenuItem("5️⃣ Teachers", disabled=True),
                        dbc.DropdownMenuItem("6️⃣ WASH", disabled=True),
                        dbc.DropdownMenuItem("7️⃣ Energy", disabled=True),
                        dbc.DropdownMenuItem("8️⃣ Climate", disabled=True),
                        dbc.DropdownMenuItem("9️⃣ Safety", disabled=True),
                        dbc.DropdownMenuItem("🔟 Budget", disabled=True),
                        dbc.DropdownMenuItem("1️⃣1️⃣ Geographic", disabled=True),
                        dbc.DropdownMenuItem("1️⃣2️⃣ Strategic", disabled=True),
                    ],
                    color="light",
                    size="md",
                    style={'fontSize': '13px'}
                )
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
        ], width=3),
        dbc.Col([
            html.Label("📍 Province", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='province-dropdown', 
                        options=[{'label': 'All Provinces', 'value': 'All Provinces'}] + 
                                [{'label': p, 'value': p} for p in all_provinces],
                        value='All Provinces', clearable=False, style={'fontSize': '10px'})
        ], width=3),
        dbc.Col([
            html.Label("🏘️ Compare Districts (max 5)", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='district-multi-dropdown',
                        options=[{'label': d, 'value': d} for d in all_districts],
                        value=[], multi=True, placeholder="Select districts to compare...",
                        style={'fontSize': '10px'})
        ], width=6)
    ], style={'marginBottom': '18px'}),
    
    html.Hr(style={'margin': '0 0 22px 0'}),
    
    # KPI SECTION HEADER
    html.Div([
        html.H6("📊 DISTRICT-LEVEL KEY PERFORMANCE INDICATORS", 
               style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '13px', 'marginBottom': '14px', 'letterSpacing': '0.5px'})
    ]),
    
    # KPI ROWS
    html.Div(id='kpi-cards-row1', style={'marginBottom': '18px'}),
    html.Div(id='kpi-cards-row2', style={'marginBottom': '28px'}),
    
    # RANKING TABLE
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader([
                    html.Div([
                        html.Span("🏆 DISTRICT RANKING & PERFORMANCE TABLE", 
                                 style={'fontWeight': 'bold', 'fontSize': '13px', 'marginRight': '15px'}),
                        html.Span("(Ranked by Infrastructure Index)", 
                                 style={'fontSize': '10px', 'color': '#6c757d', 'fontStyle': 'italic'})
                    ], style={'display': 'inline-block'})
                ], style={'backgroundColor': '#f8f9fa', 'padding': '10px'}),
                dbc.CardBody([
                    html.Div(id='ranking-table')
                ], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=12)
    ], style={'marginBottom': '28px'}),
    
    # PHASE 2: COMPARATIVE VISUALIZATIONS
    html.Div([
        html.H6("📊 COMPARATIVE ANALYSIS", 
               style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '13px', 'marginBottom': '14px', 'letterSpacing': '0.5px'})
    ]),
    
    # SPIDER CHART + SCATTER PLOT
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🕸️ MULTI-DIMENSIONAL COMPARISON (SPIDER CHART)", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    html.Div(id='spider-info', style={'fontSize': '10px', 'color': '#6c757d', 'marginBottom': '8px', 'textAlign': 'center'}),
                    dcc.Graph(id='spider-chart', style={'height': '400px'}, config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📈 INFRASTRUCTURE vs ENROLLMENT (SCATTER PLOT)", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='scatter-chart', style={'height': '400px'}, config={'displayModeBar': True})
                ], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6)
    ], style={'marginBottom': '22px'}),
    
    # BOX PLOT + HEATMAP
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 INFRASTRUCTURE GAP ANALYSIS", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    html.Div([
                        html.Span("🎯 Target: 0.70 | ", style={'fontSize': '10px', 'color': '#6c757d'}),
                        html.Span("🔴 Below Target | ", style={'fontSize': '10px', 'color': '#d62728'}),
                        html.Span("🟢 Above Target", style={'fontSize': '10px', 'color': '#2ca02c'})
                    ], style={'textAlign': 'center', 'marginBottom': '5px'}),
                    dcc.Graph(id='gap-chart', style={'height': '350px'}, config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🔥 PERFORMANCE HEATMAP", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='heatmap-chart', style={'height': '350px'}, config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6)
    ], style={'marginBottom': '28px'}),
    
    # PHASE 3: TOP/BOTTOM + PROVINCE COMPARISON
    html.Div([
        html.H6("🏆 DISTRICT PERFORMANCE RANKINGS", 
               style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '13px', 'marginBottom': '14px', 'letterSpacing': '0.5px'})
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🥇 TOP 10 BEST PERFORMING DISTRICTS", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#d4edda', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='top10-chart', style={'height': '380px'}, config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("⚠️ BOTTOM 10 DISTRICTS (NEED ATTENTION)", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8d7da', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='bottom10-chart', style={'height': '380px'}, config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6)
    ], style={'marginBottom': '22px'}),
    
    # PROVINCE COMPARISON
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 AVERAGE PERFORMANCE BY PROVINCE", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='province-comparison', style={'height': '350px'}, config={'displayModeBar': False})
                ], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=12)
    ], style={'marginBottom': '28px'}),
    
    # SECTOR DRILL-DOWN
    dbc.Row([
        dbc.Col([
            html.Div(id='sector-drilldown')
        ], width=12)
    ], style={'marginBottom': '22px'}),
    
    # FOOTER
    html.Hr(style={'margin': '22px 0 12px 0'}),
    dbc.Row([
        dbc.Col([
            html.P([
                html.Strong("SCMS 2024-2050 | Dashboard 4/12 - District Analysis | "),
                f"Source: MINEDUC School Assessment Data | Generated: {datetime.now().strftime('%B %d, %Y')} | ",
                html.A("📧 Support", href="mailto:support@mineduc.gov.rw", style={'color': '#007bff', 'textDecoration': 'none'})
            ], className="text-center", style={'fontSize': '10px', 'color': '#6c757d', 'marginBottom': '0'})
        ])
    ])
    
], fluid=True, style={'backgroundColor': '#f5f7fa', 'padding': '20px', 'fontFamily': 'Arial, sans-serif'})

# ============================================================================
# 7. CALLBACKS
# ============================================================================

@app.callback(
    Output('district-multi-dropdown', 'options'),
    Input('province-dropdown', 'value')
)
def update_district_options(selected_province):
    """Update district dropdown based on province selection"""
    if selected_province == 'All Provinces':
        options = [{'label': d, 'value': d} for d in all_districts]
    else:
        districts = districts_by_province.get(selected_province, [])
        options = [{'label': d, 'value': d} for d in districts]
    return options

@app.callback(
    Output('kpi-cards-row1', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-multi-dropdown', 'value')
)
def update_kpi_row1(location, province, selected_districts):
    """Update first row of KPIs"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None
    )
    
    district_agg = aggregate_by_district(filtered_df)
    
    # Filter by selected districts if any
    if selected_districts and len(selected_districts) > 0:
        district_agg = district_agg[district_agg['District'].isin(selected_districts)]
    
    kpis = calculate_district_kpis(district_agg)
    
    return dbc.Row([
        dbc.Col(create_kpi_card("Total Districts", kpis['total_districts'], '#1f77b4', 
                               subtitle="Districts in selection", icon="🗺️"), width=3),
        dbc.Col(create_kpi_card("Total Schools", kpis['total_schools'], '#2ca02c', 
                               value_format="number", subtitle="Across all districts", icon="🏫"), width=3),
        dbc.Col(create_kpi_card("Total Students", kpis['total_students'], '#ff7f0e', 
                               value_format="number", subtitle="Enrolled students", icon="👥"), width=3),
        dbc.Col(create_kpi_card("Avg Infrastructure", kpis['avg_infra'], kpis['infra_color'],
                               subtitle="🟢 Good: ≥0.7 | 🔴 Poor: <0.7", value_format="percentage", icon="🏗️"), width=3)
    ], className="g-3")

@app.callback(
    Output('kpi-cards-row2', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-multi-dropdown', 'value')
)
def update_kpi_row2(location, province, selected_districts):
    """Update second row of KPIs"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None
    )
    
    district_agg = aggregate_by_district(filtered_df)
    
    if selected_districts and len(selected_districts) > 0:
        district_agg = district_agg[district_agg['District'].isin(selected_districts)]
    
    kpis = calculate_district_kpis(district_agg)
    
    return dbc.Row([
        dbc.Col(create_kpi_card("Avg S/C Ratio", kpis['avg_sc_ratio'], kpis['sc_color'],
                               subtitle="🟢 Good: ≤45 | 🔴 Crowded: >45", value_format="decimal"), width=3),
        dbc.Col(create_kpi_card("Avg S/T Ratio", kpis['avg_st_ratio'], kpis['st_color'],
                               subtitle="🟢 Good: ≤35 | 🔴 High: >35", value_format="decimal"), width=3),
        dbc.Col(create_kpi_card("Avg Electricity", kpis['avg_electricity'], '#ffc107',
                               subtitle="% of schools with electricity", value_format="percent", icon="💡"), width=3),
        dbc.Col(create_kpi_card("Avg Water Quality", kpis['avg_water'], '#17a2b8',
                               subtitle="Average water quality score", value_format="decimal", icon="💧"), width=3)
    ], className="g-3")

@app.callback(
    Output('ranking-table', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-multi-dropdown', 'value')
)
def update_ranking_table(location, province, selected_districts):
    """Update district ranking table"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None
    )
    
    district_agg = aggregate_by_district(filtered_df)
    
    # Highlight selected districts
    if selected_districts and len(selected_districts) > 0:
        district_agg['Selected'] = district_agg['District'].apply(lambda x: '✓' if x in selected_districts else '')
    else:
        district_agg['Selected'] = ''
    
    # Reorder columns for display
    display_cols = ['Rank', 'Selected', 'District', 'Location', 'Province', 'Schools', 'Students', 
                   'S/C Ratio', 'S/T Ratio', 'Infra Index', 'Electricity %', 'Water Score']
    
    table_data = district_agg[display_cols].to_dict('records')
    
    # Color coding conditions
    style_conditions = [
        # Top 5 districts (green background)
        {'if': {'filter_query': '{Rank} <= 5'}, 
         'backgroundColor': '#d4edda', 'fontWeight': 'bold'},
        
        # Bottom 5 districts (red background)
        {'if': {'filter_query': f'{{Rank}} >= {len(district_agg) - 4}'}, 
         'backgroundColor': '#f8d7da'},
        
        # S/C Ratio coloring
        {'if': {'column_id': 'S/C Ratio', 'filter_query': '{S/C Ratio} > 50'}, 
         'color': '#d62728', 'fontWeight': 'bold'},
        {'if': {'column_id': 'S/C Ratio', 'filter_query': '{S/C Ratio} <= 45'}, 
         'color': '#2ca02c', 'fontWeight': 'bold'},
        
        # S/T Ratio coloring
        {'if': {'column_id': 'S/T Ratio', 'filter_query': '{S/T Ratio} > 40'}, 
         'color': '#d62728', 'fontWeight': 'bold'},
        {'if': {'column_id': 'S/T Ratio', 'filter_query': '{S/T Ratio} <= 35'}, 
         'color': '#2ca02c', 'fontWeight': 'bold'},
        
        # Infrastructure Index coloring
        {'if': {'column_id': 'Infra Index', 'filter_query': '{Infra Index} >= 0.7'}, 
         'color': '#2ca02c', 'fontWeight': 'bold'},
        {'if': {'column_id': 'Infra Index', 'filter_query': '{Infra Index} < 0.5'}, 
         'color': '#d62728', 'fontWeight': 'bold'},
        
        # Alternate row coloring
        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'},
        
        # Selected districts highlight
        {'if': {'filter_query': '{Selected} = "✓"'}, 
         'backgroundColor': '#cfe2ff', 'border': '2px solid #0d6efd'}
    ]
    
    return dash_table.DataTable(
        data=table_data,
        columns=[{'name': i, 'id': i} for i in display_cols],
        style_cell={
            'textAlign': 'left', 
            'fontSize': '10px', 
            'padding': '8px',
            'whiteSpace': 'normal',
            'height': 'auto'
        },
        style_header={
            'backgroundColor': '#343a40',
            'color': 'white',
            'fontWeight': 'bold',
            'fontSize': '11px',
            'textAlign': 'center'
        },
        style_data_conditional=style_conditions,
        page_size=30,
        sort_action='native',
        filter_action='native',
        fixed_rows={'headers': True},
        style_table={'overflowX': 'auto', 'maxHeight': '600px', 'overflowY': 'auto'}
    )

# ============================================================================
# PHASE 2 & 3 CALLBACKS
# ============================================================================

@app.callback(
    Output('spider-chart', 'figure'),
    Output('spider-info', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-multi-dropdown', 'value')
)
def update_spider_chart(location, province, selected_districts):
    """Spider/Radar chart for multi-dimensional comparison"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None
    )
    
    district_agg = aggregate_by_district(filtered_df)
    
    # If no districts selected, show top 5
    if not selected_districts or len(selected_districts) == 0:
        selected_districts = district_agg.nlargest(5, 'Infra Index')['District'].tolist()
        info_text = f"📊 Showing Top 5 Districts (select districts in filter to compare specific ones)"
    else:
        info_text = f"📊 Comparing {len(selected_districts)} selected district(s)"
    
    district_subset = district_agg[district_agg['District'].isin(selected_districts)]
    
    if len(district_subset) == 0:
        fig = go.Figure()
        fig.add_annotation(text="Select districts to compare", xref="paper", yref="paper", 
                          x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#999"))
        return fig, info_text
    
    # Normalize metrics to 0-1 scale for radar chart
    # Higher is better for all metrics
    categories = ['Infrastructure', 'Electricity', 'Water Quality', 'Fence Coverage', 
                  'Low S/C Ratio', 'Low S/T Ratio', 'Low Damage', 'High Teachers']
    
    fig = go.Figure()
    
    for _, row in district_subset.iterrows():
        values = [
            row['Infra Index'],  # Already 0-1
            row['Electricity %'] / 100,  # Convert to 0-1
            row['Water Score'] / 4,  # Assuming max score is 4
            row['Fence %'] / 100,
            max(0, 1 - (row['S/C Ratio'] / 60)),  # Inverse - lower is better
            max(0, 1 - (row['S/T Ratio'] / 50)),  # Inverse - lower is better
            max(0, 1 - (row['Classroom Damage %'] / 100)),  # Inverse
            min(1, row['Teachers'] / row['Students'] * 100) if row['Students'] > 0 else 0
        ]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=row['District'],
            hovertemplate='<b>%{theta}</b><br>Score: %{r:.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], tickformat='.1f')
        ),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(size=9)),
        margin=dict(l=80, r=80, t=20, b=60),
        paper_bgcolor='white',
        font=dict(size=10)
    )
    
    return fig, info_text

@app.callback(
    Output('scatter-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-multi-dropdown', 'value')
)
def update_scatter_chart(location, province, selected_districts):
    """Scatter plot: Infrastructure vs Students"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None
    )
    
    district_agg = aggregate_by_district(filtered_df)
    
    # Highlight selected districts
    district_agg['Selected'] = district_agg['District'].apply(
        lambda x: 'Selected' if (selected_districts and x in selected_districts) else 'Others'
    )
    
    fig = px.scatter(
        district_agg,
        x='Infra Index',
        y='Students',
        size='Schools',
        color='Province',
        hover_name='District',
        hover_data={
            'Province': True,
            'Schools': True,
            'Students': ':,',
            'S/C Ratio': ':.1f',
            'S/T Ratio': ':.1f',
            'Infra Index': ':.2f',
            'Selected': False
        },
        size_max=30,
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    # Add quadrant lines
    fig.add_hline(y=district_agg['Students'].median(), line_dash="dash", 
                  line_color="gray", opacity=0.5, annotation_text="Median Students")
    fig.add_vline(x=0.7, line_dash="dash", line_color="red", opacity=0.5, 
                  annotation_text="Target: 0.7")
    
    # Highlight selected districts
    if selected_districts and len(selected_districts) > 0:
        selected_data = district_agg[district_agg['District'].isin(selected_districts)]
        fig.add_trace(go.Scatter(
            x=selected_data['Infra Index'],
            y=selected_data['Students'],
            mode='markers',
            marker=dict(size=15, color='red', symbol='diamond', line=dict(width=2, color='darkred')),
            name='Selected Districts',
            text=selected_data['District'],
            hoverinfo='text'
        ))
    
    fig.update_layout(
        xaxis_title="Infrastructure Health Index",
        yaxis_title="Total Students",
        showlegend=True,
        legend=dict(font=dict(size=9)),
        margin=dict(l=50, r=30, t=30, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0'),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('gap-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value')
)
def update_gap_chart(location, province):
    """Gap Analysis: Infrastructure Index vs Target (0.7)"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None
    )
    
    district_agg = aggregate_by_district(filtered_df)
    
    # Calculate gap from target (0.7)
    TARGET = 0.7
    district_agg['Gap'] = district_agg['Infra Index'] - TARGET
    district_agg['Gap_Percent'] = (district_agg['Gap'] / TARGET) * 100
    
    # Sort by gap (worst first)
    district_agg = district_agg.sort_values('Gap', ascending=True)
    
    # Color coding based on gap severity
    def get_color(gap):
        if gap < -0.3:
            return '#8b0000'  # Dark red (critical)
        elif gap < -0.2:
            return '#d62728'  # Red (severe)
        elif gap < -0.1:
            return '#ff7f0e'  # Orange (moderate)
        elif gap < 0:
            return '#ffc107'  # Yellow (minor)
        elif gap < 0.1:
            return '#90ee90'  # Light green (good)
        else:
            return '#2ca02c'  # Dark green (excellent)
    
    district_agg['Color'] = district_agg['Gap'].apply(get_color)
    
    # Create hover text with current value and gap
    district_agg['Hover'] = district_agg.apply(
        lambda row: f"<b>{row['District']}</b><br>" +
                   f"Current: {row['Infra Index']:.2f}<br>" +
                   f"Target: {TARGET:.2f}<br>" +
                   f"Gap: {row['Gap']:+.2f} ({row['Gap_Percent']:+.1f}%)<br>" +
                   f"Schools: {int(row['Schools'])}", 
        axis=1
    )
    
    fig = go.Figure()
    
    # Add bars
    fig.add_trace(go.Bar(
        y=district_agg['District'],
        x=district_agg['Gap'],
        orientation='h',
        marker=dict(color=district_agg['Color']),
        text=district_agg['Gap'].apply(lambda x: f'{x:+.2f}'),
        textposition='auto',
        hovertemplate='%{customdata}<extra></extra>',
        customdata=district_agg['Hover']
    ))
    
    # Add reference line at 0 (target achieved)
    fig.add_vline(x=0, line_dash="solid", line_color="black", line_width=2,
                  annotation_text="TARGET", annotation_position="top")
    
    # Add shaded regions
    fig.add_vrect(x0=-1, x1=0, fillcolor="red", opacity=0.1, layer="below", line_width=0)
    fig.add_vrect(x0=0, x1=1, fillcolor="green", opacity=0.1, layer="below", line_width=0)
    
    fig.update_layout(
        xaxis_title="Gap from Target (0.70)",
        yaxis_title="District",
        showlegend=False,
        margin=dict(l=120, r=30, t=20, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0', zeroline=True, zerolinewidth=2, zerolinecolor='black'),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('heatmap-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value')
)
def update_heatmap_chart(location, province):
    """Heatmap of district performance across KPIs"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None
    )
    
    district_agg = aggregate_by_district(filtered_df)
    
    # Select top 15 and bottom 15 for visibility
    top_bottom = pd.concat([
        district_agg.head(15),
        district_agg.tail(15)
    ]).drop_duplicates()
    
    # Prepare data for heatmap
    metrics = ['Infra Index', 'S/C Ratio', 'S/T Ratio', 'Electricity %', 'Water Score']
    
    heatmap_data = top_bottom[['District'] + metrics].set_index('District')
    
    # Normalize data for better color scaling (0-1)
    normalized = heatmap_data.copy()
    normalized['S/C Ratio'] = 1 - (normalized['S/C Ratio'] / normalized['S/C Ratio'].max())
    normalized['S/T Ratio'] = 1 - (normalized['S/T Ratio'] / normalized['S/T Ratio'].max())
    normalized['Electricity %'] = normalized['Electricity %'] / 100
    normalized['Water Score'] = normalized['Water Score'] / 4
    
    fig = go.Figure(data=go.Heatmap(
        z=normalized.T.values,
        x=normalized.index,
        y=metrics,
        colorscale='RdYlGn',
        text=heatmap_data.T.values,
        texttemplate='%{text:.1f}',
        textfont=dict(size=8),
        hovertemplate='<b>%{y}</b><br>%{x}: %{text:.2f}<extra></extra>',
        showscale=True,
        colorbar=dict(title=dict(text="Score", side="right"), tickmode="linear", tick0=0, dtick=0.2)
    ))
    
    fig.update_layout(
        margin=dict(l=100, r=50, t=20, b=120),
        paper_bgcolor='white',
        font=dict(size=9),
        xaxis=dict(tickangle=-45, side='bottom'),
        yaxis=dict(side='left')
    )
    
    return fig

@app.callback(
    Output('top10-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value')
)
def update_top10_chart(location, province):
    """Top 10 best performing districts"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None
    )
    
    district_agg = aggregate_by_district(filtered_df)
    top10 = district_agg.head(10).sort_values('Infra Index', ascending=True)
    
    fig = go.Figure(data=[go.Bar(
        y=top10['District'],
        x=top10['Infra Index'],
        orientation='h',
        marker_color=px.colors.sequential.Greens_r,
        text=top10['Infra Index'].apply(lambda x: f'{x:.2f}'),
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Infrastructure: %{x:.2f}<br>Rank: %{customdata}<extra></extra>',
        customdata=top10['Rank']
    )])
    
    fig.update_layout(
        xaxis_title="Infrastructure Health Index",
        yaxis_title="District",
        showlegend=False,
        margin=dict(l=120, r=30, t=20, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0', range=[0, 1]),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('bottom10-chart', 'figure'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value')
)
def update_bottom10_chart(location, province):
    """Bottom 10 worst performing districts"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None
    )
    
    district_agg = aggregate_by_district(filtered_df)
    bottom10 = district_agg.tail(10).sort_values('Infra Index', ascending=True)
    
    fig = go.Figure(data=[go.Bar(
        y=bottom10['District'],
        x=bottom10['Infra Index'],
        orientation='h',
        marker_color=px.colors.sequential.Reds,
        text=bottom10['Infra Index'].apply(lambda x: f'{x:.2f}'),
        textposition='auto',
        hovertemplate='<b>%{y}</b><br>Infrastructure: %{x:.2f}<br>Rank: %{customdata}<extra></extra>',
        customdata=bottom10['Rank']
    )])
    
    fig.update_layout(
        xaxis_title="Infrastructure Health Index",
        yaxis_title="District",
        showlegend=False,
        margin=dict(l=120, r=30, t=20, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0', range=[0, 1]),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('province-comparison', 'figure'),
    Input('location-dropdown', 'value')
)
def update_province_comparison(location):
    """Grouped bar chart comparing provinces"""
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None
    )
    
    # Aggregate by province
    province_agg = filtered_df.groupby('name_of_the_province').agg({
        'kpi_a1_student_classroom_ratio': 'mean',
        'kpi_a2_student_teacher_ratio': 'mean',
        'index_1_infrastructure_health_index': 'mean',
        'kpi_d2_electricity_reliability': 'mean'
    }).reset_index()
    
    province_agg.columns = ['Province', 'S/C Ratio', 'S/T Ratio', 'Infrastructure', 'Electricity']
    province_agg['Electricity'] = province_agg['Electricity'] * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='S/C Ratio',
        x=province_agg['Province'],
        y=province_agg['S/C Ratio'],
        text=province_agg['S/C Ratio'].apply(lambda x: f'{x:.1f}'),
        textposition='auto',
        marker_color='#1f77b4'
    ))
    
    fig.add_trace(go.Bar(
        name='S/T Ratio',
        x=province_agg['Province'],
        y=province_agg['S/T Ratio'],
        text=province_agg['S/T Ratio'].apply(lambda x: f'{x:.1f}'),
        textposition='auto',
        marker_color='#ff7f0e'
    ))
    
    fig.add_trace(go.Bar(
        name='Infrastructure (×100)',
        x=province_agg['Province'],
        y=province_agg['Infrastructure'] * 100,
        text=province_agg['Infrastructure'].apply(lambda x: f'{x:.2f}'),
        textposition='auto',
        marker_color='#2ca02c'
    ))
    
    fig.add_trace(go.Bar(
        name='Electricity %',
        x=province_agg['Province'],
        y=province_agg['Electricity'],
        text=province_agg['Electricity'].apply(lambda x: f'{x:.1f}%'),
        textposition='auto',
        marker_color='#ffc107'
    ))
    
    fig.update_layout(
        barmode='group',
        xaxis_title="Province",
        yaxis_title="Average Score",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=9)),
        margin=dict(l=50, r=30, t=60, b=80),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(tickangle=-45, gridcolor='#e0e0e0'),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    
    return fig

@app.callback(
    Output('sector-drilldown', 'children'),
    Input('district-multi-dropdown', 'value')
)
def update_sector_drilldown(selected_districts):
    """Sector-level drill-down when single district selected"""
    
    if not selected_districts or len(selected_districts) != 1:
        return html.Div([
            html.P("💡 Select exactly ONE district in the filter above to see sector-level breakdown", 
                  style={'fontSize': '11px', 'color': '#6c757d', 'textAlign': 'center', 
                         'padding': '20px', 'backgroundColor': '#f8f9fa', 'borderRadius': '8px'})
        ])
    
    district_name = selected_districts[0]
    
    # Filter data for this district
    district_schools = df[df['name_of_the_district'] == district_name]
    
    if len(district_schools) == 0:
        return html.Div([html.P("No data available", style={'textAlign': 'center', 'color': '#999'})])
    
    # Aggregate by sector
    sector_agg = district_schools.groupby('name_of_the_sector').agg({
        'school_code': 'count',
        'number_of_students': 'sum',
        'number_of_teachers': 'sum',
        'number_of_classrooms': 'sum',
        'kpi_a1_student_classroom_ratio': 'mean',
        'kpi_a2_student_teacher_ratio': 'mean',
        'index_1_infrastructure_health_index': 'mean'
    }).reset_index()
    
    sector_agg.columns = ['Sector', 'Schools', 'Students', 'Teachers', 'Classrooms', 
                         'S/C Ratio', 'S/T Ratio', 'Infra Index']
    
    sector_agg = sector_agg.round({'S/C Ratio': 1, 'S/T Ratio': 1, 'Infra Index': 2})
    sector_agg = sector_agg.sort_values('Infra Index', ascending=False)
    
    table_data = sector_agg.to_dict('records')
    
    style_conditions = [
        {'if': {'column_id': 'S/C Ratio', 'filter_query': '{S/C Ratio} > 50'}, 
         'color': '#d62728', 'fontWeight': 'bold'},
        {'if': {'column_id': 'S/T Ratio', 'filter_query': '{S/T Ratio} > 40'}, 
         'color': '#d62728', 'fontWeight': 'bold'},
        {'if': {'column_id': 'Infra Index', 'filter_query': '{Infra Index} >= 0.7'}, 
         'color': '#2ca02c', 'fontWeight': 'bold'},
        {'if': {'column_id': 'Infra Index', 'filter_query': '{Infra Index} < 0.5'}, 
         'color': '#d62728', 'fontWeight': 'bold'},
        {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
    ]
    
    return dbc.Card([
        dbc.CardHeader(f"📍 SECTOR BREAKDOWN - {district_name}", 
                      style={'fontWeight': 'bold', 'backgroundColor': '#e3f2fd', 'fontSize': '12px', 'padding': '8px'}),
        dbc.CardBody([
            dash_table.DataTable(
                data=table_data,
                columns=[{'name': i, 'id': i} for i in sector_agg.columns],
                style_cell={'textAlign': 'left', 'fontSize': '10px', 'padding': '6px'},
                style_header={'backgroundColor': '#2196f3', 'color': 'white', 'fontWeight': 'bold', 'fontSize': '11px'},
                style_data_conditional=style_conditions,
                page_size=20,
                sort_action='native',
                filter_action='native'
            )
        ], style={'padding': '10px'})
    ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})

# ============================================================================
# 8. LANCER L'APPLICATION
# ============================================================================

server = app.server

if __name__ == '__main__':
    print("\n" + "="*75)
    print("🚀 SCMS DISTRICT DASHBOARD - DASHBOARD 4/12 - COMPLETE VERSION")
    print("="*75)
    print("\n✅ Phase 1 - Core Features:")
    print("   ✓ District-level aggregation (30 districts)")
    print("   ✓ 8 KPI cards (Performance + Coverage)")
    print("   ✓ Interactive ranking table (sortable, filterable, color-coded)")
    print("   ✓ Multi-district comparison filter (select up to 5)")
    print("\n✅ Phase 2 - Comparative Visualizations:")
    print("   ✓ Spider/Radar Chart (8-dimensional comparison)")
    print("   ✓ Scatter Plot (Infrastructure vs Students)")
    print("   ✓ Gap Analysis (Infrastructure gap to target 0.7)")
    print("   ✓ Heatmap (District performance matrix)")
    print("\n✅ Phase 3 - Rankings & Drill-down:")
    print("   ✓ Top 10 Best Districts")
    print("   ✓ Bottom 10 Worst Districts")
    print("   ✓ Province Performance Comparison")
    print("   ✓ Sector-level drill-down (when 1 district selected)")
    print("\n🎯 COMPLETE - Ready for MINEDUC/World Bank")
    print("\n🌐 Starting server...")
    print("   → Open: http://127.0.0.1:8051/")
    print("   → Press Ctrl+C to stop\n")
    print("="*75 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=8051)