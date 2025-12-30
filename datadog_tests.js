/**
 * Tests de performance avec DataDog pour BF1 TV
 * Usage: node datadog_tests.js [URL]
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

class DataDogTester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.results = {};
        this.apiKey = process.env.DATADOG_API_KEY || '';
        this.appKey = process.env.DATADOG_APP_KEY || '';
        this.apiUrl = 'https://api.datadoghq.com/api/v1';
    }

    async testPage(endpoint, pageName) {
        console.log(`\n🔍 Test DataDog: ${pageName}`);
        console.log(`URL: ${this.baseUrl}${endpoint}`);
        
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            if (!this.apiKey || !this.appKey) {
                throw new Error('Clés API DataDog manquantes. Définissez DATADOG_API_KEY et DATADOG_APP_KEY dans les variables d\'environnement.');
            }

            // Configuration du test
            const testOptions = {
                name: `BF1 TV - ${pageName}`,
                type: 'api',
                config: {
                    assertions: [
                        {
                            type: 'responseTime',
                            operator: 'is',
                            target: 2000
                        },
                        {
                            type: 'statusCode',
                            operator: 'is',
                            target: 200
                        }
                    ],
                    request: {
                        method: 'GET',
                        url: url,
                        timeout: 30
                    }
                },
                locations: ['aws:us-east-1', 'aws:eu-west-1', 'aws:ap-southeast-1'],
                message: `Test de performance pour ${pageName}`,
                tags: ['bf1tv', 'performance'],
                options: {
                    tick_every: 60,
                    min_failure_duration: 0,
                    min_location_failed: 1,
                    follow_redirects: true,
                    retry: {
                        count: 3,
                        interval: 300
                    }
                }
            };

            // Lancer le test
            console.log('⏳ Lancement du test...');
            const testResponse = await axios.post(`${this.apiUrl}/synthetics/tests`, testOptions, {
                headers: {
                    'DD-API-KEY': this.apiKey,
                    'DD-APPLICATION-KEY': this.appKey,
                    'Content-Type': 'application/json'
                }
            });

            const testId = testResponse.data.public_id;
            console.log(`📋 ID du test: ${testId}`);
            console.log('⏳ Attente des résultats...');

            // Attendre les résultats
            const results = await this.waitForResults(testId);
            
            // Analyser les résultats
            const analysis = this.analyzeResults(results);
            
            this.results[pageName] = {
                endpoint,
                url,
                testId,
                results,
                analysis
            };

            console.log(`✅ Test terminé pour ${pageName}`);
            console.log(`   📊 Temps de réponse: ${analysis.responseTime}ms`);
            console.log(`   📊 Disponibilité: ${analysis.availability}%`);
            console.log(`   📊 Erreurs: ${analysis.errorRate}%`);

        } catch (error) {
            console.error(`❌ Erreur lors du test de ${pageName}:`, error.message);
            this.results[pageName] = {
                endpoint,
                url,
                error: error.message
            };
        }
    }

    async waitForResults(testId) {
        return new Promise((resolve, reject) => {
            const checkStatus = async () => {
                try {
                    const statusResponse = await axios.get(`${this.apiUrl}/synthetics/tests/${testId}`, {
                        headers: {
                            'DD-API-KEY': this.apiKey,
                            'DD-APPLICATION-KEY': this.appKey
                        }
                    });

                    const status = statusResponse.data.status;
                    
                    if (status === 'live') {
                        const resultsResponse = await axios.get(`${this.apiUrl}/synthetics/tests/${testId}/results`, {
                            headers: {
                                'DD-API-KEY': this.apiKey,
                                'DD-APPLICATION-KEY': this.appKey
                            }
                        });
                        resolve(resultsResponse.data);
                    } else if (status === 'paused') {
                        reject(new Error('Test en pause'));
                    } else {
                        // Test en cours
                        setTimeout(checkStatus, 10000); // Vérifier toutes les 10 secondes
                    }
                } catch (error) {
                    reject(error);
                }
            };
            
            checkStatus();
        });
    }

    analyzeResults(results) {
        const analysis = {
            responseTime: 0,
            availability: 0,
            errorRate: 0,
            recommendations: []
        };

        if (results.results && results.results.length > 0) {
            const latestResult = results.results[0];
            
            analysis.responseTime = latestResult.responseTime;
            analysis.availability = latestResult.availability;
            analysis.errorRate = latestResult.errorRate;

            // Générer des recommandations basées sur les métriques
            if (analysis.responseTime > 1000) {
                analysis.recommendations.push({
                    type: 'performance',
                    message: 'Temps de réponse élevé - optimiser le serveur',
                    impact: 'high'
                });
            }

            if (analysis.availability < 99) {
                analysis.recommendations.push({
                    type: 'availability',
                    message: 'Disponibilité faible - vérifier la stabilité',
                    impact: 'high'
                });
            }

            if (analysis.errorRate > 1) {
                analysis.recommendations.push({
                    type: 'errors',
                    message: 'Taux d\'erreur élevé - vérifier les logs',
                    impact: 'high'
                });
            }
        }

        return analysis;
    }

    async runAllTests() {
        console.log('🚀 Lancement des tests DataDog BF1 TV');
        console.log('=' .repeat(50));

        // Pages à tester
        const pagesToTest = [
            { endpoint: '/', name: 'Page d\'accueil' },
            { endpoint: '/login/', name: 'Page de connexion' },
            { endpoint: '/register/', name: 'Page d\'inscription' },
            { endpoint: '/cost-simulator/', name: 'Simulateur de coût' }
        ];

        // Tester chaque page
        for (const page of pagesToTest) {
            await this.testPage(page.endpoint, page.name);
        }

        // Générer le rapport
        await this.generateReport();

        console.log('\n🎉 Tests DataDog terminés!');
    }

    async generateReport() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const resultsDir = 'datadog_results';
        
        // Créer le répertoire des résultats
        if (!fs.existsSync(resultsDir)) {
            fs.mkdirSync(resultsDir);
        }

        // Générer le rapport JSON
        const jsonReport = {
            timestamp: new Date().toISOString(),
            baseUrl: this.baseUrl,
            results: this.results
        };

        const jsonFile = path.join(resultsDir, `datadog_results_${timestamp}.json`);
        fs.writeFileSync(jsonFile, JSON.stringify(jsonReport, null, 2));

        // Générer le rapport Markdown
        const mdReport = this.generateMarkdownReport();
        const mdFile = path.join(resultsDir, `datadog_report_${timestamp}.md`);
        fs.writeFileSync(mdFile, mdReport);

        console.log(`\n📊 Rapport JSON généré: ${jsonFile}`);
        console.log(`📋 Rapport Markdown généré: ${mdFile}`);
    }

    generateMarkdownReport() {
        let report = `# Rapport de Performance DataDog BF1 TV

**Date:** ${new Date().toLocaleString()}
**URL de base:** ${this.baseUrl}
**Outil:** DataDog

## Résumé des Tests

`;

        // Calculer les moyennes
        let totalResponseTime = 0;
        let totalAvailability = 0;
        let totalErrorRate = 0;
        let pageCount = 0;

        Object.values(this.results).forEach(result => {
            if (result.analysis && !result.error) {
                totalResponseTime += result.analysis.responseTime;
                totalAvailability += result.analysis.availability;
                totalErrorRate += result.analysis.errorRate;
                pageCount++;
            }
        });

        if (pageCount > 0) {
            report += `- ⚡ Temps de réponse moyen: ${Math.round(totalResponseTime / pageCount)}ms
- 📊 Disponibilité moyenne: ${(totalAvailability / pageCount).toFixed(2)}%
- 📊 Taux d'erreur moyen: ${(totalErrorRate / pageCount).toFixed(2)}%

`;
        }

        // Détails pour chaque page
        report += `## Détails par Page

`;

        Object.entries(this.results).forEach(([pageName, result]) => {
            report += `### ${pageName}\n\n`;
            report += `**URL:** ${result.url}\n\n`;

            if (result.error) {
                report += `❌ **Erreur:** ${result.error}\n\n`;
            } else {
                const analysis = result.analysis;
                report += `- ⚡ Temps de réponse: ${analysis.responseTime}ms
- 📊 Disponibilité: ${analysis.availability}%
- 📊 Taux d'erreur: ${analysis.errorRate}%

`;

                // Évaluation des métriques
                if (analysis.responseTime < 500) {
                    report += `✅ **Temps de réponse excellent**\n\n`;
                } else if (analysis.responseTime < 1000) {
                    report += `⚠️  **Temps de réponse acceptable**\n\n`;
                } else if (analysis.responseTime < 2000) {
                    report += `🟡 **Temps de réponse à améliorer**\n\n`;
                } else {
                    report += `🔴 **Temps de réponse critique**\n\n`;
                }

                if (analysis.availability >= 99.9) {
                    report += `✅ **Disponibilité excellente**\n\n`;
                } else if (analysis.availability >= 99) {
                    report += `⚠️  **Disponibilité acceptable**\n\n`;
                } else if (analysis.availability >= 95) {
                    report += `🟡 **Disponibilité à améliorer**\n\n`;
                } else {
                    report += `🔴 **Disponibilité critique**\n\n`;
                }

                if (analysis.errorRate < 0.1) {
                    report += `✅ **Taux d'erreur excellent**\n\n`;
                } else if (analysis.errorRate < 1) {
                    report += `⚠️  **Taux d'erreur acceptable**\n\n`;
                } else if (analysis.errorRate < 5) {
                    report += `🟡 **Taux d'erreur à améliorer**\n\n`;
                } else {
                    report += `🔴 **Taux d'erreur critique**\n\n`;
                }

                // Recommandations
                if (analysis.recommendations.length > 0) {
                    report += `#### Recommandations\n\n`;
                    
                    analysis.recommendations.forEach(rec => {
                        const impactIcon = {
                            'high': '🔴',
                            'medium': '🟡',
                            'low': '🟢'
                        }[rec.impact] || '❓';

                        report += `- ${impactIcon} **${rec.type}:** ${rec.message}\n`;
                    });
                    report += '\n';
                } else {
                    report += `✅ **Aucune recommandation majeure!**\n\n`;
                }

                // Lien vers le test DataDog
                if (result.testId) {
                    report += `#### Détails du Test\n\n`;
                    report += `- **ID du test:** ${result.testId}\n`;
                    report += `- **Lien DataDog:** https://app.datadoghq.com/synthetics/details/${result.testId}\n\n`;
                }
            }
        });

        // Recommandations générales
        report += `## Recommandations Générales

### Optimisation de la Performance
- Optimiser la configuration du serveur web
- Utiliser la compression gzip/brotli
- Implémenter la mise en cache
- Optimiser les requêtes à la base de données
- Utiliser un CDN

### Amélioration de la Disponibilité
- Mettre en place un monitoring 24/7
- Implémenter la redondance
- Utiliser un load balancer
- Mettre en place des sauvegardes automatiques
- Implémenter un plan de reprise d'activité

### Réduction du Taux d'Erreur
- Mettre en place des tests de santé
- Implémenter la surveillance proactive
- Utiliser des alertes automatiques
- Mettre en place des procédures de maintenance
- Implémenter la surveillance des dépendances

## Standards de Performance

- **Temps de réponse:** < 500ms
- **Disponibilité:** > 99.9%
- **Taux d'erreur:** < 0.1%

`;

        return report;
    }
}

// Fonction principale
async function main() {
    const baseUrl = process.argv[2] || 'http://localhost:8000';
    const tester = new DataDogTester(baseUrl);
    
    try {
        await tester.runAllTests();
    } catch (error) {
        console.error('❌ Erreur lors des tests:', error);
        process.exit(1);
    }
}

// Exécution
if (require.main === module) {
    main();
}

module.exports = DataDogTester;
