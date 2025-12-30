#!/usr/bin/env python3
"""
Tests de performance pour BF1 TV
"""

import time
import requests
import concurrent.futures
from statistics import mean, median
import json


class PerformanceTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
    
    def test_endpoint(self, endpoint, method="GET", data=None, headers=None):
        """Test un endpoint et mesure le temps de réponse"""
        url = f"{self.base_url}{endpoint}"
        
        start_time = time.time()
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers)
            
            end_time = time.time()
            response_time = end_time - start_time
            
            return {
                'status_code': response.status_code,
                'response_time': response_time,
                'success': response.status_code < 400
            }
        except Exception as e:
            end_time = time.time()
            return {
                'status_code': 0,
                'response_time': end_time - start_time,
                'success': False,
                'error': str(e)
            }
    
    def test_concurrent_requests(self, endpoint, num_requests=10):
        """Test des requêtes concurrentes"""
        print(f"🔄 Test de {num_requests} requêtes concurrentes sur {endpoint}")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(self.test_endpoint, endpoint) for _ in range(num_requests)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        response_times = [r['response_time'] for r in results]
        success_rate = sum(1 for r in results if r['success']) / len(results) * 100
        
        return {
            'endpoint': endpoint,
            'num_requests': num_requests,
            'avg_response_time': mean(response_times),
            'median_response_time': median(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'success_rate': success_rate
        }
    
    def test_home_page(self):
        """Test de la page d'accueil"""
        print("🏠 Test de la page d'accueil...")
        result = self.test_endpoint('/')
        self.results['home_page'] = result
        return result
    
    def test_login_page(self):
        """Test de la page de connexion"""
        print("🔐 Test de la page de connexion...")
        result = self.test_endpoint('/login/')
        self.results['login_page'] = result
        return result
    
    def test_cost_simulator(self):
        """Test du simulateur de coût"""
        print("🧮 Test du simulateur de coût...")
        result = self.test_endpoint('/cost-simulator/')
        self.results['cost_simulator'] = result
        return result
    
    def test_admin_interface(self):
        """Test de l'interface d'administration"""
        print("⚙️  Test de l'interface d'administration...")
        result = self.test_endpoint('/admin/')
        self.results['admin_interface'] = result
        return result
    
    def test_static_files(self):
        """Test des fichiers statiques"""
        print("📄 Test des fichiers statiques...")
        # Test d'un fichier CSS (Tailwind)
        result = self.test_endpoint('/static/css/tailwind.css')
        self.results['static_files'] = result
        return result
    
    def run_all_tests(self):
        """Lance tous les tests"""
        print("🚀 Lancement des tests de performance BF1 TV")
        print("=" * 50)
        
        # Tests individuels
        self.test_home_page()
        self.test_login_page()
        self.test_cost_simulator()
        self.test_admin_interface()
        self.test_static_files()
        
        # Tests de charge
        print("\n📊 Tests de charge...")
        load_tests = [
            ('/', 20),
            ('/cost-simulator/', 10),
            ('/login/', 15),
        ]
        
        for endpoint, num_requests in load_tests:
            result = self.test_concurrent_requests(endpoint, num_requests)
            self.results[f'load_test_{endpoint.replace("/", "_")}'] = result
        
        self.print_results()
    
    def print_results(self):
        """Affiche les résultats des tests"""
        print("\n📈 Résultats des tests de performance")
        print("=" * 50)
        
        # Tests individuels
        print("\n🔍 Tests individuels:")
        for test_name, result in self.results.items():
            if 'load_test' not in test_name:
                status = "✅" if result['success'] else "❌"
                print(f"  {status} {test_name}: {result['response_time']:.3f}s (HTTP {result['status_code']})")
        
        # Tests de charge
        print("\n⚡ Tests de charge:")
        for test_name, result in self.results.items():
            if 'load_test' in test_name:
                endpoint = result['endpoint']
                print(f"\n  📍 {endpoint}:")
                print(f"    • Requêtes: {result['num_requests']}")
                print(f"    • Temps moyen: {result['avg_response_time']:.3f}s")
                print(f"    • Temps médian: {result['median_response_time']:.3f}s")
                print(f"    • Temps min: {result['min_response_time']:.3f}s")
                print(f"    • Temps max: {result['max_response_time']:.3f}s")
                print(f"    • Taux de succès: {result['success_rate']:.1f}%")
        
        # Recommandations
        print("\n💡 Recommandations:")
        avg_times = [r['avg_response_time'] for r in self.results.values() if 'avg_response_time' in r]
        if avg_times:
            overall_avg = mean(avg_times)
            if overall_avg < 0.5:
                print("  ✅ Performance excellente (< 0.5s)")
            elif overall_avg < 1.0:
                print("  ✅ Performance bonne (< 1.0s)")
            elif overall_avg < 2.0:
                print("  ⚠️  Performance acceptable (< 2.0s)")
            else:
                print("  ❌ Performance à améliorer (> 2.0s)")
        
        # Sauvegarde des résultats
        with open('performance_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Résultats sauvegardés dans performance_results.json")


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tests de performance BF1 TV')
    parser.add_argument('--url', default='http://localhost:8000', help='URL de base de l\'application')
    parser.add_argument('--requests', type=int, default=10, help='Nombre de requêtes pour les tests de charge')
    
    args = parser.parse_args()
    
    tester = PerformanceTest(args.url)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
