"""
SCMS ALERTS DASHBOARD - ENRICHED & CORRECTED
==========================================

Garde uniquement:
- Filtres (Location Type, Province, District, Sector)
- Alertes (Urgent, Attention, Good Status)

Installation:
    pip install dash pandas plotly openpyxl dash-bootstrap-components

Usage:
    python3 scms_alerts_simple.py
"""

import pandas as pd
from datetime import datetime
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc

# ============================================================================
# 1. CHARGEMENT DES DONNÉES
# ============================================================================

print("📊 Chargement des données...")
df_assess = pd.read_excel('SCMS DATA.xlsx', sheet_name='RAW_DATA_ASSESSMENT')
df_inspec = pd.read_excel('SCMS DATA.xlsx', sheet_name='RAW_DATA_INSPECTION')

# Fusionner sur school_code
df = df_assess.merge(
    df_inspec,
    on='school_code',
    suffixes=('_assess', '_inspec'),
    how='left'
)

# Nettoyage basique
for col in ['name_of_the_province', 'name_of_the_district', 'name_of_the_sector']:
    df[col] = df[col].fillna('Unknown')

# Créer location_type
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
# 3. FONCTIONS HELPER - LOGIQUE EXACTE DE VOS DASHBOARDS
# ============================================================================

def calculate_alerts(data):
    """Calculer alertes avec toutes écoles - logique issue de Dashboard 1"""
    if len(data) == 0:
        return {'urgent': [], 'attention': [], 'good': []}
    
    urgent = []
    attention = []
    good = []
    
    for _, row in data.iterrows():
        # Colonnes clés - utiliser _assess pour ratios, _inspec pour observations
        sc = row.get('kpi_a1_student_classroom_ratio', 0)
        st = row.get('kpi_a2_student_teacher_ratio', 0)
        infra = row.get('index_1_infrastructure_health_index', 0)
        
        # Pour les indicateurs binaires, utiliser assessment
        delayed_maint = row.get('m5_delayed_maintenance', 0)
        safety_concerns = row.get('s2_immediate_safety_concerns', 0)
        fence_avail = row.get('kpi_c1_fence_availability', 0)
        
        school_info = {
            'School': row['school_name'],
            'Location': row['location_type'],
            'Province': row['name_of_the_province'],
            'District': row['name_of_the_district'],
            'Students': int(row.get('number_of_students', 0)),
            'Teachers': int(row.get('number_of_teachers', 0)),
            'Classrooms': int(row.get('number_of_classrooms', 0)),
            'S/C': round(sc, 1),
            'S/T': round(st, 1),
            'Infra': round(infra, 2),
            # WASH
            'Toilets': round(row.get('students_per_toilet', 0), 1),
            'Damaged Toilets (%)': round(row.get('kpi_b2_toilet_damage_rate', 0) * 100, 1),
            'Water Quality': round(row.get('kpi_d1_water_quality_score', 0), 1),
            # Utilities
            'Electricity Reliability': round(row.get('kpi_d2_electricity_reliability', 0), 1),
            # Safety
            'Safety Compliance (%)': round(row.get('saf_10_safety_compliance_index', 0) * 100, 1),
            # Governance
            'PTA Presence': int(row.get('com_2_pta_presence_observed', 0)),
            'Delayed Maintenance': int(delayed_maint)
        }
        
        # URGENT
        if (sc > 50 or st > 40 or infra < 0.5):
            urgent.append(school_info)
        
        # ATTENTION
        elif (45 < sc <= 50 or
              35 < st <= 40 or
              0.5 <= infra < 0.7 or
              delayed_maint == 1 or
              safety_concerns == 1 or
              fence_avail == 0):
            issues = []
            if 45 < sc <= 50: issues.append('High S/C')
            if 35 < st <= 40: issues.append('High S/T')
            if 0.5 <= infra < 0.7: issues.append('Med Infra')
            if delayed_maint == 1: issues.append('Delayed')
            if safety_concerns == 1: issues.append('Safety')
            if fence_avail == 0: issues.append('No Fence')
            school_info['Issues'] = ', '.join(issues)
            attention.append(school_info)
        
        # GOOD
        else:
            good_reasons = []
            if sc <= 45: good_reasons.append('S/C≤45')
            if st <= 35: good_reasons.append('S/T≤35')
            if infra >= 0.7: good_reasons.append('Infra≥0.7')
            school_info['Why Good'] = ', '.join(good_reasons)
            good.append(school_info)
    
    return {'urgent': urgent, 'attention': attention, 'good': good}

def filter_data(location=None, province=None, district=None, sector=None):
    filtered = df.copy()
    if location and location != 'All Locations':
        filtered = filtered[filtered['location_type'] == location]
    if province and province != 'All Provinces':
        filtered = filtered[filtered['name_of_the_province'] == province]
    if district and district != 'All Districts':
        filtered = filtered[filtered['name_of_the_district'] == district]
    if sector and sector != 'All Sectors':
        filtered = filtered[filtered['name_of_the_sector'] == sector]
    return filtered

# ============================================================================
# 4. INITIALISER L'APPLICATION DASH
# ============================================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "SCMS Alerts Dashboard - Enriched"

# ============================================================================
# 5. LAYOUT DE L'APPLICATION
# ============================================================================

app.layout = dbc.Container([
    # HEADER
    dbc.Row([dbc.Col(html.Div([
        html.H1("SCMS ALERTS DASHBOARD", style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '28px', 'marginBottom': '5px'}),
        html.H6("School Construction and Maintenance Strategy - Alerts & Priorities",
                style={'color': '#7f8c8d', 'fontSize': '14px'})
    ], style={'textAlign': 'center'}))], style={'marginBottom': '25px'}),
    
    html.Hr(style={'margin': '0 0 20px 0'}),
    
    # FILTRES
    dbc.Row([
        dbc.Col([html.Label("🌍 Location Type", style={'fontWeight': 'bold', 'fontSize': '12px', 'marginBottom': '5px'}),
                 dcc.Dropdown(id='location-dropdown', options=[
                    {'label': 'All Locations', 'value': 'All Locations'},
                    {'label': 'Kigali City', 'value': 'Kigali City'},
                    {'label': 'Secondary Cities', 'value': 'Secondary Cities'},
                    {'label': 'Rural Districts', 'value': 'Rural Districts'}
                 ], value='All Locations', clearable=False, style={'fontSize': '11px'})], width=3),
        dbc.Col([html.Label("📍 Province", style={'fontWeight': 'bold', 'fontSize': '12px', 'marginBottom': '5px'}),
                 dcc.Dropdown(id='province-dropdown', options=[{'label': 'All Provinces', 'value': 'All Provinces'}] + 
                              [{'label': p, 'value': p} for p in all_provinces],
                              value='All Provinces', clearable=False, style={'fontSize': '11px'})], width=3),
        dbc.Col([html.Label("🏘️ District", style={'fontWeight': 'bold', 'fontSize': '12px', 'marginBottom': '5px'}),
                 dcc.Dropdown(id='district-dropdown', options=[{'label': 'All Districts', 'value': 'All Districts'}],
                              value='All Districts', clearable=False, style={'fontSize': '11px'})], width=3),
        dbc.Col([html.Label("🗺️ Sector", style={'fontWeight': 'bold', 'fontSize': '12px', 'marginBottom': '5px'}),
                 dcc.Dropdown(id='sector-dropdown', options=[{'label': 'All Sectors', 'value': 'All Sectors'}],
                              value='All Sectors', clearable=False, style={'fontSize': '11px'})], width=3)
    ], style={'marginBottom': '25px'}),
    
    dbc.Row([dbc.Col(html.Div(id='selection-display', style={
        'fontSize': '12px', 'padding': '10px', 'backgroundColor': '#e3f2fd',
        'borderRadius': '5px', 'textAlign': 'center', 'fontWeight': 'bold', 'border': '1px solid #2196f3'
    }))], style={'marginBottom': '30px'}),
    
    html.Hr(style={'margin': '0 0 25px 0'}),
    
    # ALERTS BOX
    dbc.Row([dbc.Col(html.Div(id='alerts-box'))]),
    
    # FOOTER
    html.Hr(style={'margin': '30px 0 15px 0'}),
    dbc.Row([dbc.Col(html.P([
        html.Strong("SCMS 2024-2050 | Alerts Dashboard | "),
        f"Source: MINEDUC School Assessment Data | Generated: {datetime.now().strftime('%B %d, %Y')} | ",
        html.A("📧 Support", href="mailto:support@mineduc.gov.rw", 
              style={'color': '#007bff', 'textDecoration': 'none'})
    ], className="text-center", style={'fontSize': '11px', 'color': '#6c757d', 'marginBottom': '0'}))])
    
], fluid=True, style={'backgroundColor': '#f5f7fa', 'padding': '30px', 'fontFamily': 'Arial, sans-serif'})

# ============================================================================
# 6. CALLBACKS
# ============================================================================

@app.callback(
    Output('district-dropdown', 'options'), Output('district-dropdown', 'value'),
    Input('province-dropdown', 'value')
)
def update_district_options(selected_province):
    if selected_province == 'All Provinces':
        opts = [{'label': 'All Districts', 'value': 'All Districts'}] + \
               [{'label': d, 'value': d} for d in sorted(df['name_of_the_district'].unique())]
    else:
        opts = [{'label': 'All Districts', 'value': 'All Districts'}] + \
               [{'label': d, 'value': d} for d in districts_by_province.get(selected_province, [])]
    return opts, 'All Districts'

@app.callback(
    Output('sector-dropdown', 'options'), Output('sector-dropdown', 'value'),
    Input('district-dropdown', 'value')
)
def update_sector_options(selected_district):
    if selected_district == 'All Districts':
        opts = [{'label': 'All Sectors', 'value': 'All Sectors'}] + \
               [{'label': s, 'value': s} for s in sorted(df['name_of_the_sector'].unique())]
    else:
        opts = [{'label': 'All Sectors', 'value': 'All Sectors'}] + \
               [{'label': s, 'value': s} for s in sectors_by_district.get(selected_district, [])]
    return opts, 'All Sectors'

@app.callback(
    Output('selection-display', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_selection_display(location, province, district, sector):
    parts = []
    if location != 'All Locations': parts.append(f"🌍 {location}")
    if province != 'All Provinces': parts.append(f"📍 {province}")
    if district != 'All Districts': parts.append(f"🏘️ {district}")
    if sector != 'All Sectors': parts.append(f"🗺️ {sector}")
    return " → ".join(parts) if parts else "🌍 All Locations | All Provinces, Districts & Sectors"

@app.callback(
    Output('alerts-box', 'children'),
    Input('location-dropdown', 'value'),
    Input('province-dropdown', 'value'),
    Input('district-dropdown', 'value'),
    Input('sector-dropdown', 'value')
)
def update_alerts(location, province, district, sector):
    filtered_df = filter_data(
        location=location if location != 'All Locations' else None,
        province=province if province != 'All Provinces' else None,
        district=district if district != 'All Districts' else None,
        sector=sector if sector != 'All Sectors' else None
    )
    alerts = calculate_alerts(filtered_df)
    
    # Colonnes communes
    base_cols = [
        'School', 'Location', 'Province', 'District', 'Students', 'Teachers', 'Classrooms',
        'S/C', 'S/T', 'Infra', 'Toilets', 'Damaged Toilets (%)', 'Water Quality',
        'Electricity Reliability', 'Safety Compliance (%)', 'PTA Presence', 'Delayed Maintenance'
    ]
    
    # URGENT TABLE
    urgent_table = dash_table.DataTable(
        data=alerts['urgent'],
        columns=[{'name': i, 'id': i} for i in base_cols],
        style_cell={'textAlign': 'left', 'fontSize': '9px', 'padding': '4px'},
        style_header={'backgroundColor': '#f8d7da', 'fontWeight': 'bold', 'fontSize': '10px'},
        style_data_conditional=[
            {'if': {'column_id': 'S/C', 'filter_query': '{S/C} > 50'}, 'backgroundColor': '#f8d7da', 'color': '#d62728', 'fontWeight': 'bold'},
            {'if': {'column_id': 'S/T', 'filter_query': '{S/T} > 40'}, 'backgroundColor': '#f8d7da', 'color': '#d62728', 'fontWeight': 'bold'},
            {'if': {'column_id': 'Infra', 'filter_query': '{Infra} < 0.5'}, 'backgroundColor': '#f8d7da', 'color': '#d62728', 'fontWeight': 'bold'}
        ],
        page_size=10, sort_action='native', filter_action='native'
    ) if alerts['urgent'] else html.P("✅ No urgent issues", style={'fontSize': '12px', 'color': '#28a745', 'textAlign': 'center', 'padding': '20px'})
    
    # ATTENTION TABLE
    attention_cols = base_cols + ['Issues']
    attention_table = dash_table.DataTable(
        data=alerts['attention'],
        columns=[{'name': i, 'id': i} for i in attention_cols],
        style_cell={'textAlign': 'left', 'fontSize': '9px', 'padding': '4px'},
        style_header={'backgroundColor': '#fff3cd', 'fontWeight': 'bold', 'fontSize': '10px'},
        page_size=10, sort_action='native', filter_action='native'
    ) if alerts['attention'] else html.P("✅ No schools need attention", style={'fontSize': '12px', 'color': '#28a745', 'textAlign': 'center', 'padding': '20px'})
    
    # GOOD TABLE
    good_cols = base_cols + ['Why Good']
    good_table = dash_table.DataTable(
        data=alerts['good'],
        columns=[{'name': i, 'id': i} for i in good_cols],
        style_cell={'textAlign': 'left', 'fontSize': '9px', 'padding': '4px'},
        style_header={'backgroundColor': '#d4edda', 'fontWeight': 'bold', 'fontSize': '10px'},
        style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#f8f9fa'}],
        page_size=10, sort_action='native', filter_action='native'
    ) if alerts['good'] else html.P("No schools in good status", style={'fontSize': '12px', 'color': '#999', 'textAlign': 'center', 'padding': '20px'})
    
    return dbc.Card([
        dbc.CardHeader(f"⚠️ ALERTS & PRIORITIES - {len(filtered_df)} SCHOOLS", style={
            'fontWeight': 'bold', 'backgroundColor': '#fff3cd', 'fontSize': '16px', 'padding': '12px', 'textAlign': 'center'
        }),
        dbc.CardBody([
            dbc.Row([dbc.Col([html.H5(f"🔴 URGENT ({len(alerts['urgent'])} schools)", style={'fontSize': '14px', 'color': '#d62728', 'fontWeight': 'bold', 'marginBottom': '12px', 'borderBottom': '2px solid #d62728', 'paddingBottom': '5px'}), urgent_table], width=12)], style={'marginBottom': '25px'}),
            dbc.Row([dbc.Col([html.H5(f"🟡 ATTENTION ({len(alerts['attention'])} schools)", style={'fontSize': '14px', 'color': '#ffa500', 'fontWeight': 'bold', 'marginBottom': '12px', 'borderBottom': '2px solid #ffa500', 'paddingBottom': '5px'}), attention_table], width=12)], style={'marginBottom': '25px'}),
            dbc.Row([dbc.Col([html.H5(f"✅ GOOD STATUS ({len(alerts['good'])} schools)", style={'fontSize': '14px', 'color': '#2ca02c', 'fontWeight': 'bold', 'marginBottom': '12px', 'borderBottom': '2px solid #2ca02c', 'paddingBottom': '5px'}), good_table], width=12)])
        ], style={'padding': '20px'})
    ], style={'boxShadow': '0 4px 6px rgba(0,0,0,0.1)', 'borderRadius': '10px', 'border': '3px solid #ffc107'})

# ============================================================================
# 7. LANCER L'APPLICATION
# ============================================================================

server = app.server

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 SCMS ALERTS DASHBOARD - ENRICHED & CORRECTED")
    print("="*60)
    print("\n✅ Features:")
    print("   ✓ Full school profile: Students, Teachers, Classrooms")
    print("   ✓ WASH: Toilets, Damaged Toilets, Water Quality")
    print("   ✓ Utilities: Electricity Reliability")
    print("   ✓ Safety & Governance: Safety Compliance, PTA, Maintenance")
    print("   ✓ Issues / Why Good explanations")
    print("\n🌐 Starting server...")
    print("   → Open: http://127.0.0.1:8050/")
    print("   → Press Ctrl+C to stop\n")
    print("="*60 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=8050)