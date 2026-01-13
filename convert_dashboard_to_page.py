"""
SCMS DASHBOARD TO PAGE CONVERTER
=================================

Script automatique pour convertir vos dashboards existants en pages

Usage:
    python3 convert_dashboard_to_page.py <input_file> <page_number>
    
Exemple:
    python3 convert_dashboard_to_page.py scms_dashboard_1_overview_fixed.py 1
"""

import sys
import re

def convert_dashboard_to_page(input_file, page_number):
    """
    Convertir un dashboard en page pour l'application multi-pages
    """
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Erreur: Fichier '{input_file}' non trouvé")
        return False
    
    print(f"📖 Lecture de {input_file}...")
    
    # =========================================================================
    # 1. SUPPRIMER L'INITIALISATION DE L'APP
    # =========================================================================
    
    # Supprimer app = dash.Dash(...)
    content = re.sub(
        r'app = dash\.Dash\([^)]*\)',
        '# Application initialisée dans app.py',
        content,
        flags=re.DOTALL
    )
    
    # Supprimer app.title
    content = re.sub(
        r'app\.title = [^\n]+\n',
        '',
        content
    )
    
    # Supprimer server = app.server
    content = re.sub(
        r'server = app\.server\n',
        '',
        content
    )
    
    print("✓ Initialisation de l'app supprimée")
    
    # =========================================================================
    # 2. AJOUTER LES IMPORTS NÉCESSAIRES
    # =========================================================================
    
    # Ajouter l'import de callback si pas déjà présent
    if 'from dash import' in content and 'callback' not in content:
        content = content.replace(
            'from dash import',
            'from dash import callback,'
        )
    elif 'import dash' in content and 'from dash import callback' not in content:
        # Ajouter après les imports dash
        import_section = content.split('\n\n')[0]
        content = content.replace(
            import_section,
            import_section + '\nfrom dash import callback'
        )
    
    print("✓ Imports mis à jour")
    
    # =========================================================================
    # 3. REMPLACER app.layout PAR layout
    # =========================================================================
    
    content = content.replace('app.layout =', 'layout =')
    
    print("✓ app.layout → layout")
    
    # =========================================================================
    # 4. REMPLACER @app.callback PAR @callback
    # =========================================================================
    
    content = content.replace('@app.callback', '@callback')
    
    print("✓ @app.callback → @callback")
    
    # =========================================================================
    # 5. SUPPRIMER LA SECTION NAVIGATION
    # =========================================================================
    
    # Pattern pour détecter la navigation
    nav_pattern = r'# NAVIGATION.*?(?=html\.Hr|# FILTRES|\n\n    #)'
    content = re.sub(nav_pattern, '', content, flags=re.DOTALL)
    
    # Supprimer aussi le ButtonGroup si présent
    buttongroup_pattern = r'dbc\.Row\(\[\s*dbc\.Col\(\[\s*dbc\.ButtonGroup\(\[.*?\]\).*?\]\).*?\], style=\{[^}]*\}\),'
    content = re.sub(buttongroup_pattern, '', content, flags=re.DOTALL)
    
    print("✓ Navigation supprimée")
    
    # =========================================================================
    # 6. SUPPRIMER LE FOOTER
    # =========================================================================
    
    # Pattern pour le footer
    footer_pattern = r'# FOOTER.*?(?=\], fluid=True)'
    content = re.sub(footer_pattern, '', content, flags=re.DOTALL)
    
    # Supprimer aussi les dernières lignes de footer
    footer_lines_pattern = r'html\.Hr\(style=\{\'margin\': \'22px.*?\]\)'
    content = re.sub(footer_lines_pattern, '', content, flags=re.DOTALL)
    
    print("✓ Footer supprimé")
    
    # =========================================================================
    # 7. SUPPRIMER LA SECTION if __name__ == '__main__'
    # =========================================================================
    
    main_pattern = r'if __name__ == \'__main__\':.*'
    content = re.sub(main_pattern, '', content, flags=re.DOTALL)
    
    print("✓ Section __main__ supprimée")
    
    # =========================================================================
    # 8. NETTOYER LES ESPACES ET COMMENTAIRES
    # =========================================================================
    
    # Supprimer les lignes vides excessives
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    # Supprimer les commentaires de séparation inutiles
    content = re.sub(r'# ={50,}\n', '', content)
    
    print("✓ Nettoyage effectué")
    
    # =========================================================================
    # 9. ÉCRIRE LE FICHIER DE SORTIE
    # =========================================================================
    
    output_file = f'pages/page_{page_number}_{get_page_name(page_number)}.py'
    
    # Ajouter un header au début
    header = f'''"""
PAGE {page_number} - {get_page_title(page_number)}
{"=" * 50}

Converti automatiquement depuis {input_file}
"""

'''
    
    final_content = header + content
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print(f"\n✅ Conversion réussie!")
        print(f"📄 Fichier créé: {output_file}")
        return True
    except Exception as e:
        print(f"\n❌ Erreur lors de l'écriture: {e}")
        return False

def get_page_name(page_number):
    """Obtenir le nom de la page"""
    names = {
        1: 'overview',
        2: 'maintenance',
        3: 'infrastructure',
        4: 'district',
        5: 'teachers',
        6: 'wash',
        7: 'energy',
        8: 'climate',
        9: 'safety',
        10: 'budget',
        11: 'geographic',
        12: 'strategic'
    }
    return names.get(int(page_number), f'page{page_number}')

def get_page_title(page_number):
    """Obtenir le titre de la page"""
    titles = {
        1: 'OVERVIEW DASHBOARD',
        2: 'MAINTENANCE OPERATIONS',
        3: 'SAFETY & INFRASTRUCTURE',
        4: 'DISTRICT ANALYSIS',
        5: 'TEACHERS ANALYTICS',
        6: 'WASH FACILITIES',
        7: 'ENERGY & UTILITIES',
        8: 'CLIMATE RESILIENCE',
        9: 'SAFETY COMPLIANCE',
        10: 'BUDGET & FINANCING',
        11: 'GEOGRAPHIC ANALYSIS',
        12: 'STRATEGIC PLANNING'
    }
    return titles.get(int(page_number), f'PAGE {page_number}')

def main():
    """Fonction principale"""
    
    print("\n" + "="*70)
    print("🔄 SCMS DASHBOARD TO PAGE CONVERTER")
    print("="*70 + "\n")
    
    if len(sys.argv) < 3:
        print("❌ Usage incorrect!")
        print("\nUsage:")
        print("    python3 convert_dashboard_to_page.py <input_file> <page_number>")
        print("\nExemple:")
        print("    python3 convert_dashboard_to_page.py scms_dashboard_1_overview_fixed.py 1")
        print("    python3 convert_dashboard_to_page.py scms_dashboard_2_maintenance_fixed.py 2")
        print()
        return
    
    input_file = sys.argv[1]
    page_number = sys.argv[2]
    
    print(f"📥 Input:  {input_file}")
    print(f"📤 Output: pages/page_{page_number}_{get_page_name(page_number)}.py")
    print()
    
    success = convert_dashboard_to_page(input_file, page_number)
    
    if success:
        print("\n" + "="*70)
        print("✅ CONVERSION TERMINÉE!")
        print("="*70)
        print("\nProchaines étapes:")
        print("1. Vérifiez le fichier créé dans pages/")
        print("2. Testez avec: python3 app.py")
        print("3. Répétez pour les autres dashboards")
        print()
    else:
        print("\n" + "="*70)
        print("❌ ÉCHEC DE LA CONVERSION")
        print("="*70)
        print("\nVérifiez les erreurs ci-dessus et réessayez.")
        print()

if __name__ == '__main__':
    main()