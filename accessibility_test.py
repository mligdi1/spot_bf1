#!/usr/bin/env python3
"""
Tests d'accessibilité pour BF1 TV
"""

import requests
from bs4 import BeautifulSoup
import json


class AccessibilityTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
    
    def get_page_content(self, endpoint):
        """Récupère le contenu d'une page"""
        try:
            response = requests.get(f"{self.base_url}{endpoint}")
            if response.status_code == 200:
                return BeautifulSoup(response.text, 'html.parser')
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération de {endpoint}: {e}")
            return None
    
    def test_alt_text(self, soup):
        """Test des textes alternatifs des images"""
        print("🖼️  Test des textes alternatifs...")
        
        images = soup.find_all('img')
        results = []
        
        for img in images:
            alt_text = img.get('alt', '')
            if not alt_text:
                results.append({
                    'element': str(img)[:100],
                    'status': 'FAIL',
                    'message': 'Image sans texte alternatif'
                })
            elif alt_text.strip() == '':
                results.append({
                    'element': str(img)[:100],
                    'status': 'FAIL',
                    'message': 'Texte alternatif vide'
                })
            else:
                results.append({
                    'element': str(img)[:100],
                    'status': 'PASS',
                    'message': f'Texte alternatif: "{alt_text}"'
                })
        
        return results
    
    def test_heading_structure(self, soup):
        """Test de la structure des titres"""
        print("📝 Test de la structure des titres...")
        
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        results = []
        
        if not headings:
            results.append({
                'status': 'WARN',
                'message': 'Aucun titre trouvé sur la page'
            })
            return results
        
        # Vérifier qu'il y a un h1
        h1_count = len(soup.find_all('h1'))
        if h1_count == 0:
            results.append({
                'status': 'FAIL',
                'message': 'Aucun titre H1 trouvé'
            })
        elif h1_count > 1:
            results.append({
                'status': 'WARN',
                'message': f'Plusieurs titres H1 trouvés ({h1_count})'
            })
        else:
            results.append({
                'status': 'PASS',
                'message': 'Un seul titre H1 trouvé'
            })
        
        # Vérifier la hiérarchie des titres
        current_level = 0
        for heading in headings:
            level = int(heading.name[1])
            if level > current_level + 1:
                results.append({
                    'status': 'WARN',
                    'message': f'Saut de niveau dans la hiérarchie: {heading.name} après H{current_level}'
                })
            current_level = level
        
        return results
    
    def test_form_labels(self, soup):
        """Test des labels des formulaires"""
        print("📋 Test des labels de formulaires...")
        
        inputs = soup.find_all(['input', 'textarea', 'select'])
        results = []
        
        for input_elem in inputs:
            input_type = input_elem.get('type', 'text')
            input_id = input_elem.get('id', '')
            
            # Ignorer les inputs cachés
            if input_type == 'hidden':
                continue
            
            # Chercher un label associé
            label = None
            if input_id:
                label = soup.find('label', {'for': input_id})
            
            if not label:
                # Chercher un label parent
                label = input_elem.find_parent('label')
            
            if not label:
                results.append({
                    'element': str(input_elem)[:100],
                    'status': 'FAIL',
                    'message': 'Input sans label associé'
                })
            else:
                label_text = label.get_text().strip()
                if not label_text:
                    results.append({
                        'element': str(input_elem)[:100],
                        'status': 'FAIL',
                        'message': 'Label vide'
                    })
                else:
                    results.append({
                        'element': str(input_elem)[:100],
                        'status': 'PASS',
                        'message': f'Label trouvé: "{label_text}"'
                    })
        
        return results
    
    def test_color_contrast(self, soup):
        """Test du contraste des couleurs (basique)"""
        print("🎨 Test du contraste des couleurs...")
        
        # Ce test est basique et ne remplace pas un outil spécialisé
        results = []
        
        # Vérifier les éléments avec du texte
        text_elements = soup.find_all(['p', 'span', 'div', 'a', 'button'])
        
        for elem in text_elements:
            style = elem.get('style', '')
            if 'color:' in style or 'background:' in style:
                results.append({
                    'element': str(elem)[:100],
                    'status': 'WARN',
                    'message': 'Couleurs inline détectées - vérifier le contraste manuellement'
                })
        
        if not results:
            results.append({
                'status': 'PASS',
                'message': 'Aucune couleur inline détectée'
            })
        
        return results
    
    def test_keyboard_navigation(self, soup):
        """Test de la navigation au clavier"""
        print("⌨️  Test de la navigation au clavier...")
        
        results = []
        
        # Vérifier les éléments interactifs
        interactive_elements = soup.find_all(['a', 'button', 'input', 'select', 'textarea'])
        
        for elem in interactive_elements:
            # Vérifier si l'élément est visible
            if elem.get('hidden') or elem.get('style', '').find('display: none') != -1:
                continue
            
            # Vérifier le tabindex
            tabindex = elem.get('tabindex')
            if tabindex and int(tabindex) < 0:
                results.append({
                    'element': str(elem)[:100],
                    'status': 'WARN',
                    'message': 'Élément avec tabindex négatif'
                })
            else:
                results.append({
                    'element': str(elem)[:100],
                    'status': 'PASS',
                    'message': 'Élément accessible au clavier'
                })
        
        return results
    
    def test_language_attribute(self, soup):
        """Test de l'attribut de langue"""
        print("🌍 Test de l'attribut de langue...")
        
        results = []
        
        html_tag = soup.find('html')
        if html_tag:
            lang = html_tag.get('lang')
            if lang:
                results.append({
                    'status': 'PASS',
                    'message': f'Langue définie: {lang}'
                })
            else:
                results.append({
                    'status': 'FAIL',
                    'message': 'Attribut de langue manquant'
                })
        else:
            results.append({
                'status': 'ERROR',
                'message': 'Balise HTML non trouvée'
            })
        
        return results
    
    def test_focus_indicators(self, soup):
        """Test des indicateurs de focus"""
        print("🎯 Test des indicateurs de focus...")
        
        results = []
        
        # Vérifier les styles CSS pour les indicateurs de focus
        style_tags = soup.find_all('style')
        css_content = ' '.join([style.get_text() for style in style_tags])
        
        if ':focus' in css_content or 'focus:' in css_content:
            results.append({
                'status': 'PASS',
                'message': 'Styles de focus détectés'
            })
        else:
            results.append({
                'status': 'WARN',
                'message': 'Aucun style de focus détecté'
            })
        
        return results
    
    def test_page(self, endpoint, page_name):
        """Test d'accessibilité d'une page"""
        print(f"\n🔍 Test d'accessibilité: {page_name}")
        print("-" * 40)
        
        soup = self.get_page_content(endpoint)
        if not soup:
            return {
                'page': page_name,
                'status': 'ERROR',
                'message': 'Impossible de charger la page'
            }
        
        page_results = {
            'page': page_name,
            'endpoint': endpoint,
            'tests': {}
        }
        
        page_results['tests']['alt_text'] = self.test_alt_text(soup)
        page_results['tests']['heading_structure'] = self.test_heading_structure(soup)
        page_results['tests']['form_labels'] = self.test_form_labels(soup)
        page_results['tests']['color_contrast'] = self.test_color_contrast(soup)
        page_results['tests']['keyboard_navigation'] = self.test_keyboard_navigation(soup)
        page_results['tests']['language_attribute'] = self.test_language_attribute(soup)
        page_results['tests']['focus_indicators'] = self.test_focus_indicators(soup)
        
        return page_results
    
    def run_all_tests(self):
        """Lance tous les tests d'accessibilité"""
        print("♿ Lancement des tests d'accessibilité BF1 TV")
        print("=" * 50)
        
        # Pages à tester
        pages_to_test = [
            ('/', 'Page d\'accueil'),
            ('/login/', 'Page de connexion'),
            ('/register/', 'Page d\'inscription'),
            ('/cost-simulator/', 'Simulateur de coût'),
            ('/dashboard/', 'Tableau de bord'),
        ]
        
        for endpoint, page_name in pages_to_test:
            result = self.test_page(endpoint, page_name)
            self.results[page_name] = result
        
        self.print_results()
    
    def print_results(self):
        """Affiche les résultats des tests"""
        print("\n📊 Résultats des tests d'accessibilité")
        print("=" * 50)
        
        for page_name, page_result in self.results.items():
            print(f"\n📄 {page_name}:")
            
            if 'tests' in page_result:
                for test_name, test_results in page_result['tests'].items():
                    print(f"\n  🔍 {test_name.replace('_', ' ').title()}:")
                    
                    if isinstance(test_results, list):
                        for result in test_results:
                            status_icon = {
                                'PASS': '✅',
                                'FAIL': '❌',
                                'WARN': '⚠️',
                                'ERROR': '🔴'
                            }.get(result.get('status', 'UNKNOWN'), '❓')
                            
                            print(f"    {status_icon} {result.get('message', 'Test effectué')}")
                    else:
                        status_icon = {
                            'PASS': '✅',
                            'FAIL': '❌',
                            'WARN': '⚠️',
                            'ERROR': '🔴'
                        }.get(test_results.get('status', 'UNKNOWN'), '❓')
                        print(f"    {status_icon} {test_results.get('message', 'Test effectué')}")
            else:
                status_icon = {
                    'PASS': '✅',
                    'FAIL': '❌',
                    'WARN': '⚠️',
                    'ERROR': '🔴'
                }.get(page_result.get('status', 'UNKNOWN'), '❓')
                print(f"  {status_icon} {page_result.get('message', 'Test effectué')}")
        
        # Sauvegarde des résultats
        with open('accessibility_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Résultats sauvegardés dans accessibility_results.json")


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tests d\'accessibilité BF1 TV')
    parser.add_argument('--url', default='http://localhost:8000', help='URL de base de l\'application')
    
    args = parser.parse_args()
    
    tester = AccessibilityTest(args.url)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
