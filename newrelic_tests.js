/**
 * Tests de performance avec New Relic pour BF1 TV
 * Usage: node newrelic_tests.js [URL]
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

class NewRelicTester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.results = {};
        this.apiKey = process.env.NEWRELIC_API_KEY || '';
        this.apiUrl = 'https://api.newrelic.com/graphql';
    }

    async testPage(endpoint, pageName) {
        console.log(`\n🔍 Test New Relic: ${pageName}`);
        console.log(`URL: ${this.baseUrl}${endpoint}`);
        
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            if (!this.apiKey) {
                throw new Error('Clé API New Relic manquante. Définissez NEWRELIC_API_KEY dans les variables d\'environnement.');
            }

            // Configuration du test
            const testOptions = {
                name: `BF1 TV - ${pageName}`,
                url: url,
                frequency: 5,
                locations: ['AWS_US_EAST_1', 'AWS_EU_WEST_1', 'AWS_AP_SOUTHEAST_1'],
                slaThreshold: 2000,
                script: `
                    $browser.get('${url}');
                    $browser.waitForAndFindElement($browser.findElement($driver.By.tagName('body')), 10000);
                    $browser.takeScreenshot();
                `
            };

            // Lancer le test
            console.log('⏳ Lancement du test...');
            const testResponse = await axios.post(`${this.apiUrl}/v1/synthetics/tests`, testOptions, {
                headers: {
                    'X-Api-Key': this.apiKey,
                    'Content-Type': 'application/json'
                }
            });

            const testId = testResponse.data.test.id;
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
                    const statusResponse = await axios.get(`${this.apiUrl}/v1/synthetics/tests/${testId}`, {
                        headers: {
                            'X-Api-Key': this.apiKey
                        }
                    });

                    const status = statusResponse.data.test.status;
                    
                    if (status === 'enabled') {
                        const resultsResponse = await axios.get(`${this.apiUrl}/v1/synthetics/tests/${testId}/results`, {
                            headers: {
                                'X-Api-Key': this.apiKey
                            }
                        });
                        resolve(resultsResponse.data);
                    } else if (status === 'disabled') {
                        reject(new Error('Test désactivé'));
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
        console.log('🚀 Lancement des tests New Relic BF1 TV');
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

        console.log('\n🎉 Tests New Relic terminés!');
    }

    async generateReport() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const resultsDir = 'newrelic_results';
        
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

        const jsonFile = path.join(resultsDir, `newrelic_results_${timestamp}.json`);
        fs.writeFileSync(jsonFile, JSON.stringify(jsonReport, null, 2));

        // Générer le rapport Markdown
        const mdReport = this.generateMarkdownReport();
        const mdFile = path.join(resultsDir, `newrelic_report_${timestamp}.md`);
        fs.writeFileSync(mdFile, mdReport);

        console.log(`\n📊 Rapport JSON généré: ${jsonFile}`);
        console.log(`📋 Rapport Markdown généré: ${mdFile}`);
    }

    generateMarkdownReport() {
        let report = `# Rapport de Performance New Relic BF1 TV

**Date:** ${new Date().toLocaleString()}
**URL de base:** ${this.baseUrl}
**Outil:** New Relic

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

                // Lien vers le test New Relic
                if (result.testId) {
                    report += `#### Détails du Test\n\n`;
                    report += `- **ID du test:** ${result.testId}\n`;
                    report += `- **Lien New Relic:** https://one.newrelic.com/synthetics/tests/${result.testId}\n\n`;
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
    const tester = new NewRelicTester(baseUrl);
    
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

module.exports = NewRelicTester;
