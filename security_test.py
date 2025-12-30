#!/usr/bin/env python3
"""
Tests de sécurité pour BF1 TV
"""

import requests
import json
from urllib.parse import urljoin


class SecurityTest:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
    
    def test_https_redirect(self):
        """Test de la redirection HTTPS"""
        print("🔒 Test de la redirection HTTPS...")
        try:
            # Test avec HTTP
            response = requests.get(self.base_url.replace('https://', 'http://'), allow_redirects=False)
            if response.status_code in [301, 302]:
                self.results['https_redirect'] = {
                    'status': 'PASS',
                    'message': 'Redirection HTTPS configurée'
                }
            else:
                self.results['https_redirect'] = {
                    'status': 'FAIL',
                    'message': 'Pas de redirection HTTPS'
                }
        except Exception as e:
            self.results['https_redirect'] = {
                'status': 'ERROR',
                'message': f'Erreur: {str(e)}'
            }
    
    def test_security_headers(self):
        """Test des en-têtes de sécurité"""
        print("🛡️  Test des en-têtes de sécurité...")
        try:
            response = requests.get(self.base_url)
            headers = response.headers
            
            security_headers = {
                'Strict-Transport-Security': 'HSTS configuré',
                'X-Frame-Options': 'Protection contre le clickjacking',
                'X-Content-Type-Options': 'Protection contre le MIME sniffing',
                'X-XSS-Protection': 'Protection XSS',
                'Content-Security-Policy': 'Politique de sécurité du contenu'
            }
            
            results = {}
            for header, description in security_headers.items():
                if header in headers:
                    results[header] = {
                        'status': 'PASS',
                        'message': f'{description} présent'
                    }
                else:
                    results[header] = {
                        'status': 'WARN',
                        'message': f'{description} manquant'
                    }
            
            self.results['security_headers'] = results
        except Exception as e:
            self.results['security_headers'] = {
                'status': 'ERROR',
                'message': f'Erreur: {str(e)}'
            }
    
    def test_sql_injection(self):
        """Test de protection contre l'injection SQL"""
        print("💉 Test de protection contre l'injection SQL...")
        
        # Payloads d'injection SQL courants
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' OR 1=1 --"
        ]
        
        test_endpoints = [
            '/login/',
            '/cost-simulator/',
            '/campaigns/'
        ]
        
        results = []
        for endpoint in test_endpoints:
            for payload in sql_payloads:
                try:
                    # Test avec POST
                    response = requests.post(
                        urljoin(self.base_url, endpoint),
                        data={'search': payload},
                        timeout=5
                    )
                    
                    # Vérifier si la réponse contient des erreurs SQL
                    if any(error in response.text.lower() for error in ['sql', 'database', 'mysql', 'postgresql']):
                        results.append({
                            'endpoint': endpoint,
                            'payload': payload,
                            'status': 'VULNERABLE',
                            'message': 'Erreur SQL détectée'
                        })
                    else:
                        results.append({
                            'endpoint': endpoint,
                            'payload': payload,
                            'status': 'SAFE',
                            'message': 'Aucune erreur SQL détectée'
                        })
                except Exception as e:
                    results.append({
                        'endpoint': endpoint,
                        'payload': payload,
                        'status': 'ERROR',
                        'message': f'Erreur: {str(e)}'
                    })
        
        self.results['sql_injection'] = results
    
    def test_xss_protection(self):
        """Test de protection contre XSS"""
        print("🎯 Test de protection contre XSS...")
        
        # Payloads XSS courants
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>"
        ]
        
        test_endpoints = [
            '/login/',
            '/cost-simulator/',
            '/campaigns/'
        ]
        
        results = []
        for endpoint in test_endpoints:
            for payload in xss_payloads:
                try:
                    response = requests.post(
                        urljoin(self.base_url, endpoint),
                        data={'search': payload},
                        timeout=5
                    )
                    
                    # Vérifier si le payload est échappé
                    if payload in response.text:
                        results.append({
                            'endpoint': endpoint,
                            'payload': payload,
                            'status': 'VULNERABLE',
                            'message': 'Payload XSS non échappé'
                        })
                    else:
                        results.append({
                            'endpoint': endpoint,
                            'payload': payload,
                            'status': 'SAFE',
                            'message': 'Payload XSS échappé'
                        })
                except Exception as e:
                    results.append({
                        'endpoint': endpoint,
                        'payload': payload,
                        'status': 'ERROR',
                        'message': f'Erreur: {str(e)}'
                    })
        
        self.results['xss_protection'] = results
    
    def test_csrf_protection(self):
        """Test de protection contre CSRF"""
        print("🔄 Test de protection contre CSRF...")
        
        try:
            # Test sans token CSRF
            response = requests.post(
                urljoin(self.base_url, '/login/'),
                data={
                    'username': 'test',
                    'password': 'test'
                }
            )
            
            if response.status_code == 403:
                self.results['csrf_protection'] = {
                    'status': 'PASS',
                    'message': 'Protection CSRF active'
                }
            else:
                self.results['csrf_protection'] = {
                    'status': 'FAIL',
                    'message': 'Protection CSRF manquante'
                }
        except Exception as e:
            self.results['csrf_protection'] = {
                'status': 'ERROR',
                'message': f'Erreur: {str(e)}'
            }
    
    def test_file_upload_security(self):
        """Test de sécurité des uploads de fichiers"""
        print("📁 Test de sécurité des uploads...")
        
        # Fichiers malveillants
        malicious_files = [
            ('test.php', '<?php echo "Hello World"; ?>', 'application/x-php'),
            ('test.jsp', '<% out.println("Hello World"); %>', 'application/x-jsp'),
            ('test.exe', b'\x4d\x5a', 'application/x-executable')
        ]
        
        results = []
        for filename, content, content_type in malicious_files:
            try:
                files = {'video_file': (filename, content, content_type)}
                response = requests.post(
                    urljoin(self.base_url, '/campaigns/1/upload/'),
                    files=files,
                    timeout=5
                )
                
                if response.status_code == 200:
                    results.append({
                        'filename': filename,
                        'status': 'VULNERABLE',
                        'message': 'Fichier malveillant accepté'
                    })
                else:
                    results.append({
                        'filename': filename,
                        'status': 'SAFE',
                        'message': 'Fichier malveillant rejeté'
                    })
            except Exception as e:
                results.append({
                    'filename': filename,
                    'status': 'ERROR',
                    'message': f'Erreur: {str(e)}'
                })
        
        self.results['file_upload_security'] = results
    
    def test_authentication_security(self):
        """Test de sécurité de l'authentification"""
        print("🔐 Test de sécurité de l'authentification...")
        
        # Test de force brute
        common_passwords = ['password', '123456', 'admin', 'test', 'qwerty']
        results = []
        
        for password in common_passwords:
            try:
                response = requests.post(
                    urljoin(self.base_url, '/login/'),
                    data={
                        'username': 'admin',
                        'password': password
                    },
                    timeout=5
                )
                
                if response.status_code == 200:
                    results.append({
                        'password': password,
                        'status': 'VULNERABLE',
                        'message': 'Mot de passe faible accepté'
                    })
                else:
                    results.append({
                        'password': password,
                        'status': 'SAFE',
                        'message': 'Mot de passe faible rejeté'
                    })
            except Exception as e:
                results.append({
                    'password': password,
                    'status': 'ERROR',
                    'message': f'Erreur: {str(e)}'
                })
        
        self.results['authentication_security'] = results
    
    def run_all_tests(self):
        """Lance tous les tests de sécurité"""
        print("🔒 Lancement des tests de sécurité BF1 TV")
        print("=" * 50)
        
        self.test_https_redirect()
        self.test_security_headers()
        self.test_sql_injection()
        self.test_xss_protection()
        self.test_csrf_protection()
        self.test_file_upload_security()
        self.test_authentication_security()
        
        self.print_results()
    
    def print_results(self):
        """Affiche les résultats des tests"""
        print("\n📊 Résultats des tests de sécurité")
        print("=" * 50)
        
        for test_name, result in self.results.items():
            print(f"\n🔍 {test_name.replace('_', ' ').title()}:")
            
            if isinstance(result, list):
                for item in result:
                    status_icon = {
                        'PASS': '✅',
                        'FAIL': '❌',
                        'WARN': '⚠️',
                        'SAFE': '✅',
                        'VULNERABLE': '❌',
                        'ERROR': '🔴'
                    }.get(item.get('status', 'UNKNOWN'), '❓')
                    
                    print(f"  {status_icon} {item.get('message', 'Test effectué')}")
            elif isinstance(result, dict):
                if 'status' in result:
                    status_icon = {
                        'PASS': '✅',
                        'FAIL': '❌',
                        'WARN': '⚠️',
                        'ERROR': '🔴'
                    }.get(result['status'], '❓')
                    print(f"  {status_icon} {result.get('message', 'Test effectué')}")
                else:
                    for header, info in result.items():
                        status_icon = {
                            'PASS': '✅',
                            'FAIL': '❌',
                            'WARN': '⚠️',
                            'ERROR': '🔴'
                        }.get(info.get('status', 'UNKNOWN'), '❓')
                        print(f"  {status_icon} {header}: {info.get('message', 'Test effectué')}")
        
        # Sauvegarde des résultats
        with open('security_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Résultats sauvegardés dans security_results.json")


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tests de sécurité BF1 TV')
    parser.add_argument('--url', default='http://localhost:8000', help='URL de base de l\'application')
    
    args = parser.parse_args()
    
    tester = SecurityTest(args.url)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
