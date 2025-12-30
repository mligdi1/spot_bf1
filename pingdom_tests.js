/**
 * Tests de performance avec Pingdom pour BF1 TV
 * Usage: node pingdom_tests.js [URL]
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

class PingdomTester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.results = {};
        this.apiKey = process.env.PINGDOM_API_KEY || '';
        this.apiUrl = 'https://api.pingdom.com/api/3.1';
    }

    async testPage(endpoint, pageName) {
        console.log(`\n🔍 Test Pingdom: ${pageName}`);
        console.log(`URL: ${this.baseUrl}${endpoint}`);
        
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            if (!this.apiKey) {
                throw new Error('Clé API Pingdom manquante. Définissez PINGDOM_API_KEY dans les variables d\'environnement.');
            }

            // Configuration du test
            const testOptions = {
                name: `BF1 TV - ${pageName}`,
                host: url,
                type: 'http',
                resolution: 1,
                sendnotificationwhendown: 0,
                notifyagainevery: 0,
                notifywhenbackup: 0,
                use_legacy_notifications: 0,
                probe_filters: [],
                integrationids: [],
                tags: ['bf1tv', 'performance'],
                custom_message: `Test de performance pour ${pageName}`,
                integrationids: [],
                userids: [],
                teamids: []
            };

            // Lancer le test
            console.log('⏳ Lancement du test...');
            const testResponse = await axios.post(`${this.apiUrl}/checks`, testOptions, {
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`,
                    'Content-Type': 'application/json'
                }
            });

            const testId = testResponse.data.check.id;
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
            console.log(`   📊 Uptime: ${analysis.uptime}%`);

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
                    const statusResponse = await axios.get(`${this.apiUrl}/checks/${testId}`, {
                        headers: {
                            'Authorization': `Bearer ${this.apiKey}`
                        }
                    });

                    const status = statusResponse.data.check.status;
                    
                    if (status === 'up') {
                        const resultsResponse = await axios.get(`${this.apiUrl}/checks/${testId}`, {
                            headers: {
                                'Authorization': `Bearer ${this.apiKey}`
                            }
                        });
                        resolve(resultsResponse.data);
                    } else if (status === 'down') {
                        reject(new Error('Test échoué'));
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
            uptime: 0,
            recommendations: []
        };

        if (results.check) {
            const check = results.check;
            
            analysis.responseTime = check.responsetime;
            analysis.availability = check.availability;
            analysis.uptime = check.uptime;

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

            if (analysis.uptime < 99) {
                analysis.recommendations.push({
                    type: 'uptime',
                    message: 'Uptime faible - vérifier la fiabilité',
                    impact: 'medium'
                });
            }
        }

        return analysis;
    }

    async runAllTests() {
        console.log('🚀 Lancement des tests Pingdom BF1 TV');
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

        console.log('\n🎉 Tests Pingdom terminés!');
    }

    async generateReport() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const resultsDir = 'pingdom_results';
        
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

        const jsonFile = path.join(resultsDir, `pingdom_results_${timestamp}.json`);
        fs.writeFileSync(jsonFile, JSON.stringify(jsonReport, null, 2));

        // Générer le rapport Markdown
        const mdReport = this.generateMarkdownReport();
        const mdFile = path.join(resultsDir, `pingdom_report_${timestamp}.md`);
        fs.writeFileSync(mdFile, mdReport);

        console.log(`\n📊 Rapport JSON généré: ${jsonFile}`);
        console.log(`📋 Rapport Markdown généré: ${mdFile}`);
    }

    generateMarkdownReport() {
        let report = `# Rapport de Performance Pingdom BF1 TV

**Date:** ${new Date().toLocaleString()}
**URL de base:** ${this.baseUrl}
**Outil:** Pingdom

## Résumé des Tests

`;

        // Calculer les moyennes
        let totalResponseTime = 0;
        let totalAvailability = 0;
        let totalUptime = 0;
        let pageCount = 0;

        Object.values(this.results).forEach(result => {
            if (result.analysis && !result.error) {
                totalResponseTime += result.analysis.responseTime;
                totalAvailability += result.analysis.availability;
                totalUptime += result.analysis.uptime;
                pageCount++;
            }
        });

        if (pageCount > 0) {
            report += `- ⚡ Temps de réponse moyen: ${Math.round(totalResponseTime / pageCount)}ms
- 📊 Disponibilité moyenne: ${(totalAvailability / pageCount).toFixed(2)}%
- 📊 Uptime moyen: ${(totalUptime / pageCount).toFixed(2)}%

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
- 📊 Uptime: ${analysis.uptime}%

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

                if (analysis.uptime >= 99.9) {
                    report += `✅ **Uptime excellent**\n\n`;
                } else if (analysis.uptime >= 99) {
                    report += `⚠️  **Uptime acceptable**\n\n`;
                } else if (analysis.uptime >= 95) {
                    report += `🟡 **Uptime à améliorer**\n\n`;
                } else {
                    report += `🔴 **Uptime critique**\n\n`;
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

                // Lien vers le test Pingdom
                if (result.testId) {
                    report += `#### Détails du Test\n\n`;
                    report += `- **ID du test:** ${result.testId}\n`;
                    report += `- **Lien Pingdom:** https://my.pingdom.com/app/reports/uptime#check=${result.testId}\n\n`;
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

### Amélioration de l'Uptime
- Mettre en place des tests de santé
- Implémenter la surveillance proactive
- Utiliser des alertes automatiques
- Mettre en place des procédures de maintenance
- Implémenter la surveillance des dépendances

## Standards de Performance

- **Temps de réponse:** < 500ms
- **Disponibilité:** > 99.9%
- **Uptime:** > 99.9%

`;

        return report;
    }
}

// Fonction principale
async function main() {
    const baseUrl = process.argv[2] || 'http://localhost:8000';
    const tester = new PingdomTester(baseUrl);
    
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

module.exports = PingdomTester;
