"""
SCMS MULTI-PAGE APPLICATION - MAIN FILE
========================================

Application principale avec navigation entre tous les dashboards

Installation:
    pip install dash pandas plotly openpyxl dash-bootstrap-components

Usage:
    python3 app.py
    
Open: http://127.0.0.1:8050/
"""

import dash
from dash import dcc, html, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime
import importlib

# ============================================================================
# 1. INITIALISER L'APPLICATION
# ============================================================================

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
    title="SCMS Dashboard System"
)

server = app.server

# ============================================================================
# 2. LAYOUT PRINCIPAL AVEC NAVIGATION
# ============================================================================

def create_header():
    """Header avec navigation"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H1("SCMS DASHBOARD SYSTEM", 
                           style={'color': '#2c3e50', 'fontWeight': 'bold', 'fontSize': '28px', 'marginBottom': '5px'}),
                    html.H6("School Construction and Maintenance Strategy 2024-2050",
                           style={'color': '#7f8c8d', 'fontSize': '14px', 'marginBottom': '0'})
                ], style={'textAlign': 'center'})
            ])
        ], style={'marginBottom': '20px'}),
        
        # NAVIGATION BUTTONS
        dbc.Row([
            dbc.Col([
                dbc.ButtonGroup([
                    dbc.Button("1️⃣ Overview", id="btn-page-1", color="primary", size="md",
                              style={'fontSize': '13px', 'padding': '8px 18px'}),
                    dbc.Button("2️⃣ Maintenance", id="btn-page-2", color="light", size="md", outline=True,
                              style={'fontSize': '13px', 'padding': '8px 18px'}),
                    dbc.Button("3️⃣ Infrastructure", id="btn-page-3", color="light", size="md", outline=True,
                              style={'fontSize': '13px', 'padding': '8px 18px'}),
                    dbc.Button("4️⃣ District", id="btn-page-4", color="light", size="md", outline=True,
                              style={'fontSize': '13px', 'padding': '8px 18px'}),
                    dbc.DropdownMenu(
                        label="More ▼",
                        children=[
                            dbc.DropdownMenuItem("5️⃣ Teachers", id="btn-page-5", disabled=True),
                            dbc.DropdownMenuItem("6️⃣ WASH", id="btn-page-6", disabled=True),
                            dbc.DropdownMenuItem("7️⃣ Energy", id="btn-page-7", disabled=True),
                            dbc.DropdownMenuItem("8️⃣ Climate", id="btn-page-8", disabled=True),
                            dbc.DropdownMenuItem("9️⃣ Safety", id="btn-page-9", disabled=True),
                            dbc.DropdownMenuItem("🔟 Budget", id="btn-page-10", disabled=True),
                            dbc.DropdownMenuItem("1️⃣1️⃣ Geographic", id="btn-page-11", disabled=True),
                            dbc.DropdownMenuItem("1️⃣2️⃣ Strategic", id="btn-page-12", disabled=True),
                        ],
                        color="light",
                        size="md",
                        style={'fontSize': '13px'}
                    )
                ], className="d-flex justify-content-center")
            ])
        ], style={'marginBottom': '20px'}),
        
        html.Hr(style={'margin': '0 0 20px 0'})
    ], fluid=True, style={'backgroundColor': '#f5f7fa', 'padding': '20px 20px 0 20px'})

def create_footer():
    """Footer commun"""
    return dbc.Container([
        html.Hr(style={'margin': '30px 0 15px 0'}),
        dbc.Row([
            dbc.Col([
                html.P([
                    html.Strong("SCMS 2024-2050 | Multi-Dashboard System | "),
                    f"Generated: {datetime.now().strftime('%B %d, %Y')} | ",
                    html.A("📧 Support", href="mailto:support@mineduc.gov.rw", 
                          style={'color': '#007bff', 'textDecoration': 'none'})
                ], className="text-center", 
                   style={'fontSize': '11px', 'color': '#6c757d', 'marginBottom': '0'})
            ])
        ])
    ], fluid=True, style={'backgroundColor': '#f5f7fa', 'padding': '0 20px 20px 20px'})

# ============================================================================
# 3. LAYOUT PRINCIPAL
# ============================================================================

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='current-page', data='page-1'),  # Store pour la page actuelle
    
    # Header avec navigation
    html.Div(id='header-container'),
    
    # Contenu dynamique
    html.Div(id='page-content', style={'backgroundColor': '#f5f7fa', 'minHeight': '80vh'}),
    
    # Footer
    html.Div(id='footer-container')
])

# ============================================================================
# 4. CALLBACKS DE NAVIGATION
# ============================================================================

@app.callback(
    Output('current-page', 'data'),
    [Input('btn-page-1', 'n_clicks'),
     Input('btn-page-2', 'n_clicks'),
     Input('btn-page-3', 'n_clicks'),
     Input('btn-page-4', 'n_clicks')],
    prevent_initial_call=True
)
def update_current_page(btn1, btn2, btn3, btn4):
    """Détecter quel bouton a été cliqué"""
    ctx = dash.callback_context
    
    if not ctx.triggered:
        return 'page-1'
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    page_map = {
        'btn-page-1': 'page-1',
        'btn-page-2': 'page-2',
        'btn-page-3': 'page-3',
        'btn-page-4': 'page-4'
    }
    
    return page_map.get(button_id, 'page-1')

@app.callback(
    Output('header-container', 'children'),
    Input('current-page', 'data')
)
def update_header(current_page):
    """Afficher le header avec boutons actifs"""
    return create_header()

@app.callback(
    Output('footer-container', 'children'),
    Input('current-page', 'data')
)
def update_footer(current_page):
    """Afficher le footer"""
    return create_footer()


@app.callback(
    Output('page-content', 'children'),
    Input('current-page', 'data')
)
def display_page(current_page):
    
    page_files = {
        'page-1': '1_overview',
        'page-2': '2_maintenance_operation',
        'page-3': '3_safety_utilities_enironment',
        'page-4': '4_district'
    }
    
    if current_page in page_files:
        module_name = f'pages.{page_files[current_page]}'
        page_module = importlib.import_module(module_name)
        return page_module.layout
    
    else:
        return dbc.Container([
            dbc.Alert([
                html.H4("Page en construction"),
                html.P("Cette page sera disponible prochainement.")
            ], color="info")
        ], style={'marginTop': '50px'})
# ============================================================================
# 5. STYLES ACTIFS DES BOUTONS
# ============================================================================

@app.callback(
    [Output('btn-page-1', 'color'),
     Output('btn-page-1', 'outline'),
     Output('btn-page-2', 'color'),
     Output('btn-page-2', 'outline'),
     Output('btn-page-3', 'color'),
     Output('btn-page-3', 'outline'),
     Output('btn-page-4', 'color'),
     Output('btn-page-4', 'outline')],
    Input('current-page', 'data')
)
def update_button_styles(current_page):
    """Mettre à jour les styles des boutons de navigation"""
    
    # Tous les boutons en outline par défaut
    styles = [
        ('light', True),  # page-1
        ('light', True),  # page-2
        ('light', True),  # page-3
        ('light', True),  # page-4
    ]
    
    # Activer le bouton de la page courante
    page_index = {
        'page-1': 0,
        'page-2': 1,
        'page-3': 2,
        'page-4': 3
    }
    
    if current_page in page_index:
        idx = page_index[current_page]
        styles[idx] = ('primary', False)
    
    # Flatten la liste pour le retour
    result = []
    for color, outline in styles:
        result.extend([color, outline])
    
    return result

# ============================================================================
# 6. LANCER L'APPLICATION
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("🚀 SCMS MULTI-PAGE DASHBOARD SYSTEM")
    print("="*80)
    print("\n✅ Pages disponibles:")
    print("   1️⃣  Overview Dashboard")
    print("   2️⃣  Maintenance Operations Dashboard")
    print("   3️⃣  Safety & Infrastructure Dashboard")
    print("   4️⃣  District Analysis Dashboard")
    print("   5️⃣-1️⃣2️⃣ Coming Soon...")
    print("\n📋 Navigation:")
    print("   • Cliquez sur les boutons en haut pour changer de page")
    print("   • La page active est en bleu (primary)")
    print("   • Les autres pages sont en gris clair (outline)")
    print("\n🌐 Starting server...")
    print("   → Open: http://127.0.0.1:8050/")
    print("   → Press Ctrl+C to stop\n")
    print("="*80 + "\n")
    
    app.run(debug=True, host='127.0.0.1', port=8050)