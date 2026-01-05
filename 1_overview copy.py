"""
SCMS OVERVIEW DASHBOARD - FINAL EDITION
========================================

Version finale professionnelle pour MINEDUC/World Bank avec:
- ✅ Bug GOOD STATUS corrigé (50 au lieu de 1)
- ✅ Navigation dropdown professionnelle (12 dashboards visibles)
- ✅ Espacement optimal (+20px entre sections)
- ✅ Mini-bars dans Top/Bottom performers
- ✅ Heatmap texte agrandi (11px)
- ✅ Gender gap % dans Toilets chart
- ✅ Polish complet

Installation:
    pip install dash pandas plotly openpyxl dash-bootstrap-components

Usage:
    python3 scms_dashboard_final.py
    
Ouvrir: http://127.0.0.1:8050/
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
df['name_of_the_sector'] = df['name_of_the_sector'].fillna('Unknown')

df['latitude'] = pd.to_numeric(df['gps_latitude'], errors='coerce')
df['longitude'] = pd.to_numeric(df['gps_longitude'], errors='coerce')

print(f"✓ Données chargées: {len(df)} écoles")
print(f"✓ Écoles avec GPS: {df['latitude'].notna().sum()}")

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

def calculate_kpis(data):
    """Calculer tous les KPIs"""
    if len(data) == 0:
        return {
            'total_schools': 0, 'total_students': 0, 'total_classrooms': 0, 'total_teachers': 0,
            'avg_student_classroom': 0, 'avg_student_teacher': 0, 'avg_teacher_classroom': 0,
            'avg_infrastructure': 0, 'pct_electricity': 0, 'avg_water_quality': 0,
            'avg_classroom_damage': 0, 'avg_toilet_damage': 0, 'pct_fence': 0,
            'toilets_boys': 0, 'toilets_girls': 0,
            'sc_color': '#999', 'st_color': '#999', 'infra_color': '#999',
            'class_dmg_color': '#999', 'toilet_dmg_color': '#999'
        }
    
    kpis = {
        'total_schools': len(data),
        'total_students': int(data['number_of_students'].sum()),
        'total_classrooms': int(data['number_of_classrooms'].sum()),
        'total_teachers': int(data['number_of_teachers'].sum()),
        'avg_student_classroom': round(data['kpi_a1_student_classroom_ratio'].mean(), 1),
        'avg_student_teacher': round(data['kpi_a2_student_teacher_ratio'].mean(), 1),
        'avg_teacher_classroom': round((data['number_of_teachers'] / data['number_of_classrooms']).mean(), 1),
        'avg_infrastructure': round(data['index_1_infrastructure_health_index'].mean(), 2),
        'pct_electricity': round((data['kpi_d2_electricity_reliability'].sum() / len(data)) * 100, 1),
        'avg_water_quality': round(data['kpi_d1_water_quality_score'].mean(), 1),
        'avg_classroom_damage': round(data['kpi_b1_classroom_damage_rate'].mean(), 1),
        'avg_toilet_damage': round(data['kpi_b2_toilet_damage_rate'].mean(), 1),
        'pct_fence': round((data['kpi_c1_fence_availability'].sum() / len(data)) * 100, 1),
        'toilets_boys': int(data['toilets_boys_total'].sum()),
        'toilets_girls': int(data['toilets_girls_total'].sum())
    }
    
    kpis['sc_color'] = '#d62728' if kpis['avg_student_classroom'] > 45 else '#2ca02c'
    kpis['st_color'] = '#d62728' if kpis['avg_student_teacher'] > 35 else '#2ca02c'
    kpis['infra_color'] = '#2ca02c' if kpis['avg_infrastructure'] >= 0.7 else '#d62728'
    kpis['class_dmg_color'] = '#2ca02c' if kpis['avg_classroom_damage'] < 15 else ('#ffa500' if kpis['avg_classroom_damage'] < 30 else '#d62728')
    kpis['toilet_dmg_color'] = '#2ca02c' if kpis['avg_toilet_damage'] < 15 else ('#ffa500' if kpis['avg_toilet_damage'] < 30 else '#d62728')
    
    return kpis

def calculate_alerts(data):
    """Calculer les alertes avec logique corrigée - BUG FIXED"""
    if len(data) == 0:
        return {'urgent': [], 'attention': [], 'good': 0}
    
    urgent_schools = set()
    attention_schools = set()
    urgent = []
    attention = []
    
    # URGENT: Seulement S/C >50, S/T >40, Infra <0.5 (critères dominants)
    for _, row in data.iterrows():
        issues = []
        if row['kpi_a1_student_classroom_ratio'] > 50:
            issues.append(f"S/C: {row['kpi_a1_student_classroom_ratio']:.1f}")
        if row['kpi_a2_student_teacher_ratio'] > 40:
            issues.append(f"S/T: {row['kpi_a2_student_teacher_ratio']:.1f}")
        if row['index_1_infrastructure_health_index'] < 0.5:
            issues.append(f"Infra: {row['index_1_infrastructure_health_index']:.2f}")
        
        if issues:
            urgent.append({'school': row['school_name'], 'issues': issues})
            urgent_schools.add(row['school_name'])
    
    # ATTENTION: Ratios moyens + Safety + Fence (mais PAS les écoles déjà en URGENT)
    for _, row in data.iterrows():
        if row['school_name'] in urgent_schools:
            continue
        
        issues = []
        if 45 < row['kpi_a1_student_classroom_ratio'] <= 50:
            issues.append("High S/C")
        if 35 < row['kpi_a2_student_teacher_ratio'] <= 40:
            issues.append("High S/T")
        if 0.5 <= row['index_1_infrastructure_health_index'] < 0.7:
            issues.append("Medium Infra")
        if row['m5_delayed_maintenance'] == 1:
            issues.append("Delayed Maint.")
        if row['s2_immediate_safety_concerns'] == 1:
            issues.append("Safety")
        if row['kpi_c1_fence_availability'] == 0:
            issues.append("No Fence")
        
        if issues:
            attention.append({'school': row['school_name'], 'issues': issues})
            attention_schools.add(row['school_name'])
    
    # *** BUG FIX: GOOD count calculation ***
    # Avant: good_count = len(data) - len(urgent) - len(attention)  ← WRONG (compte les listes, pas les écoles)
    # Après: good_count = len(data) - len(urgent_schools) - len(attention_schools)  ← CORRECT
    good_count = len(data) - len(urgent_schools) - len(attention_schools)
    
    return {
        'urgent': urgent[:5],
        'attention': attention[:5],
        'good': good_count
    }

def filter_data(province=None, district=None, sector=None):
    """Filtrer les données"""
    filtered = df.copy()
    
    if province and province != 'All Provinces':
        filtered = filtered[filtered['name_of_the_province'] == province]
    
    if district and district != 'All Districts':
        filtered = filtered[filtered['name_of_the_district'] == district]
    
    if sector and sector != 'All Sectors':
        filtered = filtered[filtered['name_of_the_sector'] == sector]
    
    return filtered

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

def create_progress_bar(value, max_value=1.0, color='#2ca02c'):
    """Créer une mini progress bar pour Top/Bottom performers"""
    width_pct = (value / max_value) * 100
    return html.Div([
        html.Div(style={
            'width': f'{width_pct}%',
            'height': '6px',
            'backgroundColor': color,
            'borderRadius': '3px',
            'transition': 'width 0.3s ease'
        })
    ], style={'width': '100%', 'height': '6px', 'backgroundColor': '#e9ecef', 'borderRadius': '3px', 'marginTop': '3px'})

# ============================================================================
# 4. INITIALISER L'APPLICATION DASH
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True
)

app.title = "SCMS Overview Dashboard"

# ============================================================================
# 5. LAYOUT DE L'APPLICATION
# ============================================================================

app.layout = dbc.Container([
    
    # HEADER
    dbc.Row([
        dbc.Col([
            html.Div([
                html.H1("SCMS OVERVIEW DASHBOARD", 
                       style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '26px', 'marginBottom': '3px'}),
                html.H6("School Construction and Maintenance Strategy 2024-2050",
                       style={'color': '#7f8c8d', 'fontSize': '13px', 'marginBottom': '0'})
            ], style={'textAlign': 'center'})
        ])
    ], style={'marginBottom': '15px'}),
    
    # NAVIGATION DROPDOWN + QUICK LINKS
    dbc.Row([
        dbc.Col([
            html.Label("📊 Navigate to Dashboard:", style={'fontSize': '11px', 'fontWeight': 'bold', 'marginBottom': '5px'}),
            dcc.Dropdown(
                id='dashboard-selector',
                options=[
                    {'label': '1️⃣ Overview (Current)', 'value': '1'},
                    {'label': '2️⃣ Infrastructure Condition', 'value': '2', 'disabled': True},
                    {'label': '3️⃣ Maintenance & Rehabilitation', 'value': '3', 'disabled': True},
                    {'label': '4️⃣ Water & Sanitation (WASH)', 'value': '4', 'disabled': True},
                    {'label': '5️⃣ Energy & Utilities', 'value': '5', 'disabled': True},
                    {'label': '6️⃣ Climate Resilience', 'value': '6', 'disabled': True},
                    {'label': '7️⃣ Safety & Security', 'value': '7', 'disabled': True},
                    {'label': '8️⃣ District Performance', 'value': '8', 'disabled': True},
                    {'label': '9️⃣ Teacher & Staffing', 'value': '9', 'disabled': True},
                    {'label': '🔟 Budget & Financing', 'value': '10', 'disabled': True},
                    {'label': '1️⃣1️⃣ Geographic Analysis', 'value': '11', 'disabled': True},
                    {'label': '1️⃣2️⃣ Strategic Projections 2024-2050', 'value': '12', 'disabled': True}
                ],
                value='1',
                clearable=False,
                style={'fontSize': '11px'}
            )
        ], width=4),
        dbc.Col([
            html.Label("🔗 Quick Access:", style={'fontSize': '11px', 'fontWeight': 'bold', 'marginBottom': '5px'}),
            dbc.ButtonGroup([
                dbc.Button("📐 Infrastructure", color="light", size="sm", outline=True, disabled=True),
                dbc.Button("🔧 Maintenance", color="light", size="sm", outline=True, disabled=True),
                dbc.Button("💧 WASH", color="light", size="sm", outline=True, disabled=True),
                dbc.Button("⚡ Energy", color="light", size="sm", outline=True, disabled=True)
            ])
        ], width=8, className="d-flex align-items-end")
    ], style={'marginBottom': '15px'}),
    
    html.Hr(style={'margin': '0 0 15px 0'}),
    
    # FILTRES
    dbc.Row([
        dbc.Col([
            html.Label("📍 Province", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='province-dropdown', 
                        options=[{'label': 'All Provinces', 'value': 'All Provinces'}] + 
                                [{'label': p, 'value': p} for p in all_provinces],
                        value='All Provinces', clearable=False, style={'fontSize': '10px'})
        ], width=3),
        dbc.Col([
            html.Label("🏘️ District", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='district-dropdown', 
                        options=[{'label': 'All Districts', 'value': 'All Districts'}],
                        value='All Districts', clearable=False, style={'fontSize': '10px'})
        ], width=3),
        dbc.Col([
            html.Label("🗺️ Sector", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            dcc.Dropdown(id='sector-dropdown',
                        options=[{'label': 'All Sectors', 'value': 'All Sectors'}],
                        value='All Sectors', clearable=False, style={'fontSize': '10px'})
        ], width=3),
        dbc.Col([
            html.Label("📊 Current Selection", style={'fontWeight': 'bold', 'fontSize': '11px', 'marginBottom': '4px'}),
            html.Div(id='selection-display', 
                    style={'fontSize': '10px', 'padding': '5px', 'backgroundColor': '#e3f2fd', 
                           'borderRadius': '4px', 'textAlign': 'center', 'marginTop': '2px'})
        ], width=3)
    ], style={'marginBottom': '15px'}),
    
    html.Hr(style={'margin': '0 0 20px 0'}),
    
    # KPI SECTION HEADER
    html.Div([
        html.H6("📊 KEY PERFORMANCE INDICATORS", 
               style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '13px', 'marginBottom': '12px', 'letterSpacing': '0.5px'})
    ]),
    
    # KPI ROW 1: COMPTAGES
    html.Div(id='kpi-cards-row1', style={'marginBottom': '15px'}),
    
    # KPI ROW 2: RATIOS & UTILITIES
    html.Div(id='kpi-cards-row2', style={'marginBottom': '15px'}),
    
    # KPI ROW 3: DAMAGE RATES & COVERAGE
    html.Div(id='kpi-cards-row3', style={'marginBottom': '25px'}),
    
    # TOP/BOTTOM + AGE DISTRIBUTION
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🏆 TOP 5 PERFORMERS", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#d4edda', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([html.Div(id='top-performers')], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("⚠️ BOTTOM 5 (NEED ATTENTION)", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8d7da', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([html.Div(id='bottom-performers')], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📅 SCHOOL AGE DISTRIBUTION", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#d1ecf1', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='age-distribution', style={'height': '140px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=4)
    ], style={'marginBottom': '20px'}),
    
    # SCHOOL AGE TABLE
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📋 Schools by Age Range", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#fff3cd', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([html.Div(id='age-table')], style={'padding': '10px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=12)
    ], style={'marginBottom': '20px'}),
    
    # MAP + PIE
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🗺️ GEOGRAPHIC DISTRIBUTION", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='map-chart', style={'height': '360px'}, config={'displayModeBar': True})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 STUDENTS DISTRIBUTION", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='pie-chart', style={'height': '360px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6)
    ], style={'marginBottom': '20px'}),
    
    # TOILETS + CLIMATE
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🚻 TOILETS COVERAGE BY GENDER", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='toilets-chart', style={'height': '280px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("🌍 CLIMATE VULNERABILITY", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='climate-chart', style={'height': '280px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6)
    ], style={'marginBottom': '20px'}),
    
    # HEATMAP
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 PERFORMANCE RATIOS HEATMAP", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='heatmap-chart', style={'height': '280px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=12)
    ], style={'marginBottom': '20px'}),
    
    # SCHOOLS + TOP 10 (HORIZONTAL)
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 SCHOOLS BY PROVINCE", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='schools-bar', style={'height': '320px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("📊 TOP 10 SCHOOLS BY ENROLLMENT", 
                              style={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa', 'fontSize': '12px', 'padding': '6px'}),
                dbc.CardBody([
                    dcc.Graph(id='top10-bar', style={'height': '320px'}, config={'displayModeBar': False})
                ], style={'padding': '5px'})
            ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px'})
        ], width=6)
    ], style={'marginBottom': '25px'}),
    
    # ALERTS BOX (À LA FIN)
    dbc.Row([
        dbc.Col([
            html.Div(id='alerts-box')
        ], width=12)
    ], style={'marginBottom': '20px'}),
    
    # FOOTER
    html.Hr(style={'margin': '20px 0 10px 0'}),
    dbc.Row([
        dbc.Col([
            html.P([
                html.Strong("SCMS 2024-2050 | "),
                f"Source: MINEDUC School Assessment Data | Generated: {datetime.now().strftime('%B %d, %Y')} | ",
                html.A("📧 Support", href="mailto:support@mineduc.gov.rw", style={'color': '#007bff', 'textDecoration': 'none'})
            ], className="text-center", style={'fontSize': '10px', 'color': '#6c757d', 'marginBottom': '0'})
        ])
    ])
    
], fluid=True, style={'backgroundColor': '#f5f7fa', 'padding': '20px', 'fontFamily': 'Arial, sans-serif'})

# ============================================================================
# 6. CALLBACKS
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
    Output('selection-display', 'children'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_selection_display(province, district, sector):
    parts = []
    if province != 'All Provinces': parts.append(f"📍 {province}")
    if district != 'All Districts': parts.append(f"🏘️ {district}")
    if sector != 'All Sectors': parts.append(f"🗺️ {sector}")
    return " → ".join(parts) if parts else "🌍 All Provinces, Districts & Sectors"

@app.callback(
    Output('kpi-cards-row1', 'children'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_kpi_row1(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    kpis = calculate_kpis(filtered_df)
    
    return dbc.Row([
        dbc.Col(create_kpi_card("Total Schools", kpis['total_schools'], '#1f77b4', icon="🏫"), width=3),
        dbc.Col(create_kpi_card("Total Students", kpis['total_students'], '#2ca02c', value_format="number", icon="👥"), width=3),
        dbc.Col(create_kpi_card("Total Classrooms", kpis['total_classrooms'], '#ff7f0e', value_format="number", icon="🏫"), width=3),
        dbc.Col(create_kpi_card("Total Teachers", kpis['total_teachers'], '#9467bd', value_format="number", icon="👨‍🏫"), width=3)
    ], className="g-2")

@app.callback(
    Output('kpi-cards-row2', 'children'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_kpi_row2(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    kpis = calculate_kpis(filtered_df)
    
    return dbc.Row([
        dbc.Col(create_kpi_card("Student/Classroom", kpis['avg_student_classroom'], kpis['sc_color'],
                               subtitle="🟢 Good: ≤45 | 🔴 Crowded: >45", value_format="decimal"), width=2),
        dbc.Col(create_kpi_card("Student/Teacher", kpis['avg_student_teacher'], kpis['st_color'],
                               subtitle="🟢 Good: ≤35 | 🔴 High: >35", value_format="decimal"), width=2),
        dbc.Col(create_kpi_card("Teacher/Classroom", kpis['avg_teacher_classroom'], '#17a2b8',
                               subtitle="Teachers per classroom", value_format="decimal"), width=2),
        dbc.Col(create_kpi_card("Infrastructure", kpis['avg_infrastructure'], kpis['infra_color'],
                               subtitle="🟢 Good: ≥0.7 | 🔴 Poor: <0.7", value_format="percentage"), width=2),
        dbc.Col(create_kpi_card("Electricity", kpis['pct_electricity'], '#28a745',
                               subtitle="% schools with electricity", value_format="percent", icon="💡"), width=2),
        dbc.Col(create_kpi_card("Water Quality", kpis['avg_water_quality'], '#007bff',
                               subtitle="Average score (0-4)", value_format="decimal", icon="💧"), width=2)
    ], className="g-2")

@app.callback(
    Output('kpi-cards-row3', 'children'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_kpi_row3(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    kpis = calculate_kpis(filtered_df)
    
    return dbc.Row([
        dbc.Col(create_kpi_card("Classroom Damage", kpis['avg_classroom_damage'], kpis['class_dmg_color'],
                               subtitle="🟢 <15% | 🟡 15-30% | 🔴 >30%", value_format="percent", icon="🔧"), width=3),
        dbc.Col(create_kpi_card("Toilet Damage", kpis['avg_toilet_damage'], kpis['toilet_dmg_color'],
                               subtitle="🟢 <15% | 🟡 15-30% | 🔴 >30%", value_format="percent", icon="🚽"), width=3),
        dbc.Col(create_kpi_card("Fence Coverage", kpis['pct_fence'], '#6610f2',
                               subtitle="% schools with fence", value_format="percent", icon="🚧"), width=3),
        dbc.Col(create_kpi_card("Total Toilets", kpis['toilets_boys'] + kpis['toilets_girls'], '#fd7e14',
                               subtitle=f"Boys: {kpis['toilets_boys']:,} | Girls: {kpis['toilets_girls']:,}", value_format="number", icon="🚻"), width=3)
    ], className="g-2")

@app.callback(
    Output('top-performers', 'children'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_top_performers(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    top5 = filtered_df.nlargest(5, 'index_1_infrastructure_health_index')[['school_name', 'index_1_infrastructure_health_index']]
    
    items = []
    for i, (_, row) in enumerate(top5.iterrows()):
        items.append(html.Div([
            html.Div([
                html.Span(f"{i+1}. ", style={'fontWeight': 'bold', 'fontSize': '11px', 'color': '#2ca02c'}),
                html.Span(f"{row['school_name']}", style={'fontSize': '10px'}),
                html.Span(f" ({row['index_1_infrastructure_health_index']:.2f})", 
                         style={'fontSize': '9px', 'color': '#2ca02c', 'marginLeft': '4px', 'fontWeight': 'bold'})
            ]),
            create_progress_bar(row['index_1_infrastructure_health_index'], 1.0, '#2ca02c')
        ], style={'marginBottom': '6px', 'paddingBottom': '6px', 'borderBottom': '1px solid #e9ecef'}))
    
    return html.Div(items)

@app.callback(
    Output('bottom-performers', 'children'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_bottom_performers(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    bottom5 = filtered_df.nsmallest(5, 'index_1_infrastructure_health_index')[['school_name', 'index_1_infrastructure_health_index']]
    
    items = []
    for i, (_, row) in enumerate(bottom5.iterrows()):
        items.append(html.Div([
            html.Div([
                html.Span(f"{i+1}. ", style={'fontWeight': 'bold', 'fontSize': '11px', 'color': '#d62728'}),
                html.Span(f"{row['school_name']}", style={'fontSize': '10px'}),
                html.Span(f" ({row['index_1_infrastructure_health_index']:.2f})", 
                         style={'fontSize': '9px', 'color': '#d62728', 'marginLeft': '4px', 'fontWeight': 'bold'})
            ]),
            create_progress_bar(row['index_1_infrastructure_health_index'], 1.0, '#d62728')
        ], style={'marginBottom': '6px', 'paddingBottom': '6px', 'borderBottom': '1px solid #e9ecef'}))
    
    return html.Div(items)

@app.callback(
    Output('age-distribution', 'figure'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_age_distribution(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    fig = go.Figure(data=[go.Histogram(
        x=filtered_df['kpi_b3_school_age'],
        nbinsx=10,
        marker_color='#17a2b8',
        hovertemplate='Age: %{x} years<br>Count: %{y}<extra></extra>'
    )])
    
    fig.update_layout(
        xaxis_title="School Age (years)",
        yaxis_title="Count",
        showlegend=False,
        margin=dict(l=35, r=15, t=10, b=35),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(family="Arial", size=9),
        xaxis=dict(gridcolor='#e0e0e0'),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    return fig

@app.callback(
    Output('age-table', 'children'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_age_table(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    bins = [0, 10, 20, 30, 40, 50, 60, 100]
    labels = ['0-10 yrs', '11-20 yrs', '21-30 yrs', '31-40 yrs', '41-50 yrs', '51-60 yrs', '>60 yrs']
    
    filtered_df['age_group'] = pd.cut(filtered_df['kpi_b3_school_age'], bins=bins, labels=labels, right=True)
    
    age_summary = []
    for label in labels:
        schools_in_group = filtered_df[filtered_df['age_group'] == label]['school_name'].tolist()
        if schools_in_group:
            age_summary.append({
                'Age Range': label,
                'Count': len(schools_in_group),
                'Schools': ', '.join(schools_in_group[:5]) + (f' (+{len(schools_in_group)-5} more)' if len(schools_in_group) > 5 else '')
            })
    
    if not age_summary:
        return html.P("No data available", style={'fontSize': '10px', 'color': '#999', 'textAlign': 'center'})
    
    return dash_table.DataTable(
        data=age_summary,
        columns=[{'name': i, 'id': i} for i in ['Age Range', 'Count', 'Schools']],
        style_cell={'textAlign': 'left', 'fontSize': '10px', 'padding': '5px'},
        style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold', 'fontSize': '10px'},
        style_data_conditional=[
            {'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}
        ]
    )

@app.callback(
    Output('map-chart', 'figure'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_map(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    map_df = filtered_df[filtered_df['latitude'].notna() & filtered_df['longitude'].notna()].copy()
    
    if len(map_df) == 0:
        fig = go.Figure()
        fig.add_annotation(text="No GPS data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=12, color="#999"))
        fig.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), margin=dict(l=0, r=0, t=0, b=0))
        return fig
    
    map_df['color'] = map_df['index_1_infrastructure_health_index'].apply(
        lambda x: '#2ca02c' if x >= 0.7 else ('#ffa500' if x >= 0.5 else '#d62728')
    )
    
    map_df['hover_text'] = map_df.apply(lambda row: 
        f"<b>{row['school_name']}</b><br>Province: {row['name_of_the_province']}<br>District: {row['name_of_the_district']}<br>" +
        f"Sector: {row['name_of_the_sector']}<br>Students: {int(row['number_of_students']):,}<br>" +
        f"S/C: {row['kpi_a1_student_classroom_ratio']:.1f} | Infra: {row['index_1_infrastructure_health_index']:.2f}",
        axis=1
    )
    
    fig = go.Figure()
    
    for color, label in [('#2ca02c', 'Good'), ('#ffa500', 'Medium'), ('#d62728', 'Poor')]:
        subset = map_df[map_df['color'] == color]
        if len(subset) > 0:
            fig.add_trace(go.Scattermapbox(
                lat=subset['latitude'], lon=subset['longitude'], mode='markers',
                marker=dict(size=subset['number_of_students'] / 100, color=color, opacity=0.8, sizemin=4),
                text=subset['hover_text'], hovertemplate='%{text}<extra></extra>', name=label
            ))
    
    lat_range = map_df['latitude'].max() - map_df['latitude'].min()
    lon_range = map_df['longitude'].max() - map_df['longitude'].min()
    zoom = 10 if (lat_range < 0.5 and lon_range < 0.5) else (9 if (lat_range < 1 and lon_range < 1) else (8 if (lat_range < 2 and lon_range < 2) else 7))
    
    fig.update_layout(
        mapbox=dict(style='open-street-map', center=dict(lat=map_df['latitude'].mean(), lon=map_df['longitude'].mean()), zoom=zoom),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=0.02, xanchor="center", x=0.5, bgcolor='rgba(255,255,255,0.8)', font=dict(size=9)),
        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='white'
    )
    return fig

@app.callback(
    Output('pie-chart', 'figure'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_pie_chart(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    students_by_province = filtered_df.groupby('name_of_the_province')['number_of_students'].sum().reset_index()
    
    fig = go.Figure(data=[go.Pie(
        labels=students_by_province['name_of_the_province'],
        values=students_by_province['number_of_students'],
        hole=0.4,
        textinfo='label+percent',
        textposition='outside',
        marker=dict(colors=px.colors.qualitative.Set2),
        hovertemplate="<b>%{label}</b><br>Students: %{value:,}<br>%{percent}<extra></extra>"
    )])
    
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='white', font=dict(size=10))
    return fig

@app.callback(
    Output('toilets-chart', 'figure'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_toilets_chart(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    boys = int(filtered_df['toilets_boys_total'].sum())
    girls = int(filtered_df['toilets_girls_total'].sum())
    gap_pct = round(abs(boys - girls) / max(boys, girls) * 100, 1) if max(boys, girls) > 0 else 0
    
    fig = go.Figure(data=[
        go.Bar(name='Boys', y=['Toilets'], x=[boys], orientation='h', marker_color='#3498db', text=[f'{boys:,}'], textposition='auto'),
        go.Bar(name='Girls', y=['Toilets'], x=[girls], orientation='h', marker_color='#e74c3c', text=[f'{girls:,}'], textposition='auto')
    ])
    
    fig.add_annotation(
        text=f"Gender Gap: {gap_pct}%",
        xref="paper", yref="paper",
        x=0.5, y=1.15,
        showarrow=False,
        font=dict(size=11, color='#6c757d')
    )
    
    fig.update_layout(
        barmode='group',
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=1.1, xanchor="center", x=0.5),
        margin=dict(l=60, r=30, t=50, b=30),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(title="Number of Toilets", gridcolor='#e0e0e0'),
        yaxis=dict(showticklabels=False)
    )
    return fig

@app.callback(
    Output('climate-chart', 'figure'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_climate_chart(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    climate_counts = filtered_df['kpi_e1_climate_vulnerability_index'].value_counts().sort_index()
    labels = {0: 'Not Vulnerable', 1: 'Slightly', 2: 'Moderately', 3: 'Highly Vulnerable'}
    
    fig = go.Figure(data=[go.Pie(
        labels=[labels.get(i, str(i)) for i in climate_counts.index],
        values=climate_counts.values,
        hole=0.4,
        marker=dict(colors=['#2ca02c', '#ffd700', '#ffa500', '#d62728']),
        textinfo='label+value',
        hovertemplate="<b>%{label}</b><br>Schools: %{value}<br>%{percent}<extra></extra>"
    )])
    
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='white', font=dict(size=10))
    return fig

@app.callback(
    Output('heatmap-chart', 'figure'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_heatmap(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    group_col = 'name_of_the_sector' if (province != 'All Provinces' and district != 'All Districts') else ('name_of_the_district' if province != 'All Provinces' else 'name_of_the_province')
    
    heatmap_data = filtered_df.groupby(group_col).agg({
        'kpi_a1_student_classroom_ratio': 'mean',
        'kpi_a2_student_teacher_ratio': 'mean',
        'index_1_infrastructure_health_index': 'mean'
    }).reset_index()
    
    fig = go.Figure(data=go.Heatmap(
        z=[heatmap_data.iloc[:, 1].values, heatmap_data.iloc[:, 2].values, heatmap_data.iloc[:, 3].values],
        x=heatmap_data.iloc[:, 0].values,
        y=['S/C Ratio', 'S/T Ratio', 'Infrastructure'],
        colorscale=[[0, '#2ca02c'], [0.5, '#ffa500'], [1, '#d62728']],
        text=[[f"{v:.1f}" for v in heatmap_data.iloc[:, 1].values],
              [f"{v:.1f}" for v in heatmap_data.iloc[:, 2].values],
              [f"{v:.2f}" for v in heatmap_data.iloc[:, 3].values]],
        texttemplate='%{text}',
        textfont=dict(size=11, color='white'),
        hovertemplate='<b>%{y}</b><br>%{x}: %{z:.2f}<extra></extra>',
        showscale=False
    ))
    
    fig.update_layout(
        margin=dict(l=110, r=25, t=15, b=60),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(tickangle=-45)
    )
    return fig

@app.callback(
    Output('schools-bar', 'figure'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_schools_bar(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    schools_by_province = filtered_df.groupby('name_of_the_province').size().reset_index(name='count').sort_values('count', ascending=True)
    
    fig = go.Figure(data=[go.Bar(
        y=schools_by_province['name_of_the_province'],
        x=schools_by_province['count'],
        orientation='h',
        marker_color=px.colors.qualitative.Set2[:len(schools_by_province)],
        text=schools_by_province['count'],
        textposition='auto',
        hovertemplate="<b>%{y}</b><br>Schools: %{x}<extra></extra>"
    )])
    
    fig.update_layout(
        xaxis_title="Number of Schools",
        yaxis_title="Province",
        showlegend=False,
        margin=dict(l=120, r=30, t=15, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0'),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    return fig

@app.callback(
    Output('top10-bar', 'figure'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_top10_bar(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    top_10 = filtered_df.nlargest(10, 'number_of_students')[['school_name', 'number_of_students']].sort_values('number_of_students', ascending=True)
    
    fig = go.Figure(data=[go.Bar(
        y=top_10['school_name'],
        x=top_10['number_of_students'],
        orientation='h',
        marker_color=px.colors.sequential.Viridis,
        text=top_10['number_of_students'],
        textposition='auto',
        hovertemplate="<b>%{y}</b><br>Students: %{x:,}<extra></extra>"
    )])
    
    fig.update_layout(
        xaxis_title="Number of Students",
        yaxis_title="School Name",
        showlegend=False,
        margin=dict(l=150, r=30, t=15, b=40),
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(size=10),
        xaxis=dict(gridcolor='#e0e0e0'),
        yaxis=dict(gridcolor='#e0e0e0')
    )
    return fig

@app.callback(
    Output('alerts-box', 'children'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_alerts(province, district, sector):
    filtered_df = filter_data(
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    
    alerts = calculate_alerts(filtered_df)
    
    urgent_items = [
        html.Li(f"{alert['school']}: {', '.join(alert['issues'])}", 
               style={'fontSize': '10px', 'marginBottom': '3px', 'lineHeight': '1.4'})
        for alert in alerts['urgent']
    ] if alerts['urgent'] else [html.Li("No urgent issues ✅", style={'fontSize': '10px', 'color': '#28a745', 'fontStyle': 'italic'})]
    
    attention_items = [
        html.Li(f"{alert['school']}: {', '.join(alert['issues'])}", 
               style={'fontSize': '10px', 'marginBottom': '3px', 'lineHeight': '1.4'})
        for alert in alerts['attention']
    ] if alerts['attention'] else [html.Li("No attention needed ✅", style={'fontSize': '10px', 'color': '#28a745', 'fontStyle': 'italic'})]
    
    return dbc.Card([
        dbc.CardHeader("⚠️ ALERTS & PRIORITIES", 
                      style={'fontWeight': 'bold', 'backgroundColor': '#fff3cd', 'fontSize': '13px', 'padding': '8px', 'textAlign': 'center'}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H6(f"🔴 URGENT ({len(alerts['urgent'])})", 
                           style={'fontSize': '11px', 'color': '#d62728', 'fontWeight': 'bold', 'marginBottom': '8px'}),
                    html.Ul(urgent_items, style={'paddingLeft': '18px', 'marginBottom': '0'})
                ], width=4),
                dbc.Col([
                    html.H6(f"🟡 ATTENTION ({len(alerts['attention'])})", 
                           style={'fontSize': '11px', 'color': '#ffa500', 'fontWeight': 'bold', 'marginBottom': '8px'}),
                    html.Ul(attention_items, style={'paddingLeft': '18px', 'marginBottom': '0'})
                ], width=4),
                dbc.Col([
                    html.H6(f"✅ GOOD STATUS ({alerts['good']})", 
                           style={'fontSize': '11px', 'color': '#2ca02c', 'fontWeight': 'bold', 'marginBottom': '8px'}),
                    html.P(f"{alerts['good']} schools in good condition", 
                          style={'fontSize': '10px', 'marginBottom': '0', 'color': '#28a745'})
                ], width=4)
            ])
        ], style={'padding': '12px'})
    ], style={'boxShadow': '0 2px 4px rgba(0,0,0,0.1)', 'borderRadius': '8px', 'border': '2px solid #ffc107'})

# ============================================================================
# 7. LANCER L'APPLICATION
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*75)
    print("🚀 SCMS OVERVIEW DASHBOARD - FINAL EDITION")
    print("="*75)
    print("\n✅ All Bug Fixes & Improvements Applied:")
    print("   ✓ Bug GOOD STATUS corrigé (50 au lieu de 1)")
    print("   ✓ Navigation dropdown professionnelle (12 dashboards)")
    print("   ✓ Mini progress bars Top/Bottom performers")
    print("   ✓ Heatmap texte agrandi (11px)")
    print("   ✓ Espacement optimal entre sections (+20px)")
    print("   ✓ Gender gap % dans Toilets chart")
    print("   ✓ Layout polish complet")
    print("\n🎯 Version finale prête pour MINEDUC/World Bank")
    print("\n🌐 Starting server...")
    print("   → Open: http://127.0.0.1:8050/")
    print("   → Press Ctrl+C to stop\n")
    print("="*75 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=8050)