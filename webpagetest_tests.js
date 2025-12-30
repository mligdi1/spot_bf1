/**
 * Tests de performance avec WebPageTest pour BF1 TV
 * Usage: node webpagetest_tests.js [URL]
 */

const WebPageTest = require('webpagetest');
const fs = require('fs');
const path = require('path');

class WebPageTestTester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.results = {};
        this.wpt = new WebPageTest('www.webpagetest.org');
    }

    async testPage(endpoint, pageName) {
        console.log(`\n🔍 Test WebPageTest: ${pageName}`);
        console.log(`URL: ${this.baseUrl}${endpoint}`);
        
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            // Configuration du test
            const options = {
                runs: 3,
                location: 'Dulles:Chrome',
                connectivity: 'Cable',
                video: 1,
                screenshot: 1,
                breakdown: 1,
                domains: 1,
                requests: 1,
                timeline: 1,
                waterfall: 1,
                firstViewOnly: false,
                private: true,
                label: `BF1 TV - ${pageName}`,
                custom: {
                    'firstViewOnly': false,
                    'video': 1,
                    'screenshot': 1,
                    'breakdown': 1,
                    'domains': 1,
                    'requests': 1,
                    'timeline': 1,
                    'waterfall': 1
                }
            };

            // Lancer le test
            console.log('⏳ Lancement du test...');
            const testId = await this.wpt.runTest(url, options);
            
            if (!testId) {
                throw new Error('Impossible de lancer le test');
            }

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
            console.log(`   📊 Score de performance: ${analysis.performanceScore}/100`);
            console.log(`   ⚡ First Byte: ${analysis.ttfb}ms`);
            console.log(`   🎯 Start Render: ${analysis.startRender}ms`);
            console.log(`   📱 Speed Index: ${analysis.speedIndex}ms`);

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
                    const status = await this.wpt.getTestStatus(testId);
                    
                    if (status.statusCode === 200) {
                        const results = await this.wpt.getTestResults(testId);
                        resolve(results);
                    } else if (status.statusCode === 100) {
                        // Test en cours
                        setTimeout(checkStatus, 10000); // Vérifier toutes les 10 secondes
                    } else {
                        reject(new Error(`Test échoué: ${status.statusText}`));
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
            performanceScore: 0,
            ttfb: 0,
            startRender: 0,
            speedIndex: 0,
            loadTime: 0,
            fullyLoaded: 0,
            recommendations: []
        };

        if (results.data && results.data.runs && results.data.runs[1]) {
            const run = results.data.runs[1].firstView;
            
            analysis.ttfb = run.TTFB;
            analysis.startRender = run.render;
            analysis.speedIndex = run.SpeedIndex;
            analysis.loadTime = run.loadTime;
            analysis.fullyLoaded = run.fullyLoaded;

            // Calculer un score de performance basé sur les métriques
            let score = 100;
            
            // Pénaliser selon les métriques
            if (analysis.ttfb > 200) score -= 10;
            if (analysis.startRender > 1000) score -= 15;
            if (analysis.speedIndex > 3000) score -= 20;
            if (analysis.loadTime > 3000) score -= 25;
            if (analysis.fullyLoaded > 5000) score -= 30;

            analysis.performanceScore = Math.max(0, score);

            // Générer des recommandations
            if (analysis.ttfb > 200) {
                analysis.recommendations.push({
                    type: 'server',
                    message: 'Time to First Byte élevé - optimiser le serveur',
                    impact: 'high'
                });
            }

            if (analysis.startRender > 1000) {
                analysis.recommendations.push({
                    type: 'rendering',
                    message: 'Temps de rendu élevé - optimiser le CSS',
                    impact: 'high'
                });
            }

            if (analysis.speedIndex > 3000) {
                analysis.recommendations.push({
                    type: 'performance',
                    message: 'Speed Index élevé - optimiser les ressources',
                    impact: 'medium'
                });
            }

            if (analysis.loadTime > 3000) {
                analysis.recommendations.push({
                    type: 'loading',
                    message: 'Temps de chargement élevé - optimiser les ressources',
                    impact: 'high'
                });
            }
        }

        return analysis;
    }

    async runAllTests() {
        console.log('🚀 Lancement des tests WebPageTest BF1 TV');
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

        console.log('\n🎉 Tests WebPageTest terminés!');
    }

    async generateReport() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const resultsDir = 'webpagetest_results';
        
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

        const jsonFile = path.join(resultsDir, `webpagetest_results_${timestamp}.json`);
        fs.writeFileSync(jsonFile, JSON.stringify(jsonReport, null, 2));

        // Générer le rapport Markdown
        const mdReport = this.generateMarkdownReport();
        const mdFile = path.join(resultsDir, `webpagetest_report_${timestamp}.md`);
        fs.writeFileSync(mdFile, mdReport);

        console.log(`\n📊 Rapport JSON généré: ${jsonFile}`);
        console.log(`📋 Rapport Markdown généré: ${mdFile}`);
    }

    generateMarkdownReport() {
        let report = `# Rapport de Performance WebPageTest BF1 TV

**Date:** ${new Date().toLocaleString()}
**URL de base:** ${this.baseUrl}
**Outil:** WebPageTest

## Résumé des Tests

`;

        // Calculer les moyennes
        let totalScore = 0;
        let pageCount = 0;
        let totalTtfb = 0;
        let totalStartRender = 0;
        let totalSpeedIndex = 0;

        Object.values(this.results).forEach(result => {
            if (result.analysis && !result.error) {
                totalScore += result.analysis.performanceScore;
                totalTtfb += result.analysis.ttfb;
                totalStartRender += result.analysis.startRender;
                totalSpeedIndex += result.analysis.speedIndex;
                pageCount++;
            }
        });

        if (pageCount > 0) {
            report += `- 📊 Score de performance moyen: ${Math.round(totalScore / pageCount)}/100
- ⚡ Time to First Byte moyen: ${Math.round(totalTtfb / pageCount)}ms
- 🎯 Start Render moyen: ${Math.round(totalStartRender / pageCount)}ms
- 📱 Speed Index moyen: ${Math.round(totalSpeedIndex / pageCount)}ms

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
                report += `- 📊 Score de performance: ${analysis.performanceScore}/100
- ⚡ Time to First Byte: ${analysis.ttfb}ms
- 🎯 Start Render: ${analysis.startRender}ms
- 📱 Speed Index: ${analysis.speedIndex}ms
- ⏱️  Load Time: ${analysis.loadTime}ms
- 🚀 Fully Loaded: ${analysis.fullyLoaded}ms

`;

                // Évaluation du score
                if (analysis.performanceScore >= 90) {
                    report += `✅ **Performance excellente**\n\n`;
                } else if (analysis.performanceScore >= 70) {
                    report += `⚠️  **Performance acceptable**\n\n`;
                } else if (analysis.performanceScore >= 50) {
                    report += `🟡 **Performance à améliorer**\n\n`;
                } else {
                    report += `🔴 **Performance critique**\n\n`;
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

                // Lien vers le test WebPageTest
                if (result.testId) {
                    report += `#### Détails du Test\n\n`;
                    report += `- **ID du test:** ${result.testId}\n`;
                    report += `- **Lien WebPageTest:** https://www.webpagetest.org/result/${result.testId}/\n\n`;
                }
            }
        });

        // Recommandations générales
        report += `## Recommandations Générales

### Optimisation du Serveur
- Optimiser la configuration du serveur web
- Utiliser la compression gzip/brotli
- Implémenter la mise en cache
- Optimiser les requêtes à la base de données

### Optimisation du Rendu
- Optimiser le CSS critique
- Éviter les ressources bloquantes
- Utiliser la préconnexion
- Optimiser le Critical Rendering Path

### Optimisation des Ressources
- Minifier les fichiers CSS et JavaScript
- Optimiser les images
- Utiliser un CDN
- Implémenter le lazy loading

## Standards de Performance

- **Time to First Byte:** < 200ms
- **Start Render:** < 1000ms
- **Speed Index:** < 3000ms
- **Load Time:** < 3000ms
- **Fully Loaded:** < 5000ms

`;

        return report;
    }
}

// Fonction principale
async function main() {
    const baseUrl = process.argv[2] || 'http://localhost:8000';
    const tester = new WebPageTestTester(baseUrl);
    
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

module.exports = WebPageTestTester;
