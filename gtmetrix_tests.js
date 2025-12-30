/**
 * Tests de performance avec GTmetrix pour BF1 TV
 * Usage: node gtmetrix_tests.js [URL]
 */

const axios = require('axios');
const fs = require('fs');
const path = require('path');

class GTmetrixTester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.results = {};
        this.apiKey = process.env.GTMETRIX_API_KEY || '';
        this.apiUrl = 'https://gtmetrix.com/api/2.0';
    }

    async testPage(endpoint, pageName) {
        console.log(`\n🔍 Test GTmetrix: ${pageName}`);
        console.log(`URL: ${this.baseUrl}${endpoint}`);
        
        const url = `${this.baseUrl}${endpoint}`;
        
        try {
            if (!this.apiKey) {
                throw new Error('Clé API GTmetrix manquante. Définissez GTMETRIX_API_KEY dans les variables d\'environnement.');
            }

            // Configuration du test
            const testOptions = {
                url: url,
                location: 'Vancouver, Canada',
                browser: 'Chrome',
                device: 'Desktop',
                connection: 'Cable',
                video: 1,
                screenshot: 1,
                report: 'full'
            };

            // Lancer le test
            console.log('⏳ Lancement du test...');
            const testResponse = await axios.post(`${this.apiUrl}/tests`, testOptions, {
                headers: {
                    'Authorization': `Basic ${Buffer.from(this.apiKey + ':').toString('base64')}`,
                    'Content-Type': 'application/json'
                }
            });

            const testId = testResponse.data.data.id;
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
            console.log(`   📊 Score de structure: ${analysis.structureScore}/100`);
            console.log(`   ⚡ Page Load Time: ${analysis.pageLoadTime}ms`);
            console.log(`   🎯 Total Page Size: ${analysis.totalPageSize}KB`);

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
                    const statusResponse = await axios.get(`${this.apiUrl}/tests/${testId}`, {
                        headers: {
                            'Authorization': `Basic ${Buffer.from(this.apiKey + ':').toString('base64')}`
                        }
                    });

                    const status = statusResponse.data.data.attributes.state;
                    
                    if (status === 'completed') {
                        const resultsResponse = await axios.get(`${this.apiUrl}/tests/${testId}`, {
                            headers: {
                                'Authorization': `Basic ${Buffer.from(this.apiKey + ':').toString('base64')}`
                            }
                        });
                        resolve(resultsResponse.data);
                    } else if (status === 'error') {
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
            performanceScore: 0,
            structureScore: 0,
            pageLoadTime: 0,
            totalPageSize: 0,
            recommendations: []
        };

        if (results.data && results.data.attributes) {
            const attributes = results.data.attributes;
            
            analysis.performanceScore = Math.round(attributes.performance_score);
            analysis.structureScore = Math.round(attributes.structure_score);
            analysis.pageLoadTime = Math.round(attributes.page_load_time);
            analysis.totalPageSize = Math.round(attributes.total_page_size / 1024); // Convertir en KB

            // Générer des recommandations basées sur les scores
            if (analysis.performanceScore < 90) {
                analysis.recommendations.push({
                    type: 'performance',
                    message: 'Score de performance faible - optimiser les ressources',
                    impact: 'high'
                });
            }

            if (analysis.structureScore < 90) {
                analysis.recommendations.push({
                    type: 'structure',
                    message: 'Score de structure faible - optimiser le code',
                    impact: 'medium'
                });
            }

            if (analysis.pageLoadTime > 3000) {
                analysis.recommendations.push({
                    type: 'loading',
                    message: 'Temps de chargement élevé - optimiser les ressources',
                    impact: 'high'
                });
            }

            if (analysis.totalPageSize > 2000) {
                analysis.recommendations.push({
                    type: 'size',
                    message: 'Taille de page élevée - optimiser les ressources',
                    impact: 'medium'
                });
            }
        }

        return analysis;
    }

    async runAllTests() {
        console.log('🚀 Lancement des tests GTmetrix BF1 TV');
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

        console.log('\n🎉 Tests GTmetrix terminés!');
    }

    async generateReport() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const resultsDir = 'gtmetrix_results';
        
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

        const jsonFile = path.join(resultsDir, `gtmetrix_results_${timestamp}.json`);
        fs.writeFileSync(jsonFile, JSON.stringify(jsonReport, null, 2));

        // Générer le rapport Markdown
        const mdReport = this.generateMarkdownReport();
        const mdFile = path.join(resultsDir, `gtmetrix_report_${timestamp}.md`);
        fs.writeFileSync(mdFile, mdReport);

        console.log(`\n📊 Rapport JSON généré: ${jsonFile}`);
        console.log(`📋 Rapport Markdown généré: ${mdFile}`);
    }

    generateMarkdownReport() {
        let report = `# Rapport de Performance GTmetrix BF1 TV

**Date:** ${new Date().toLocaleString()}
**URL de base:** ${this.baseUrl}
**Outil:** GTmetrix

## Résumé des Tests

`;

        // Calculer les moyennes
        let totalPerformanceScore = 0;
        let totalStructureScore = 0;
        let totalPageLoadTime = 0;
        let totalPageSize = 0;
        let pageCount = 0;

        Object.values(this.results).forEach(result => {
            if (result.analysis && !result.error) {
                totalPerformanceScore += result.analysis.performanceScore;
                totalStructureScore += result.analysis.structureScore;
                totalPageLoadTime += result.analysis.pageLoadTime;
                totalPageSize += result.analysis.totalPageSize;
                pageCount++;
            }
        });

        if (pageCount > 0) {
            report += `- 📊 Score de performance moyen: ${Math.round(totalPerformanceScore / pageCount)}/100
- 📊 Score de structure moyen: ${Math.round(totalStructureScore / pageCount)}/100
- ⚡ Page Load Time moyen: ${Math.round(totalPageLoadTime / pageCount)}ms
- 🎯 Taille de page moyenne: ${Math.round(totalPageSize / pageCount)}KB

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
- 📊 Score de structure: ${analysis.structureScore}/100
- ⚡ Page Load Time: ${analysis.pageLoadTime}ms
- 🎯 Taille de page: ${analysis.totalPageSize}KB

`;

                // Évaluation des scores
                if (analysis.performanceScore >= 90) {
                    report += `✅ **Performance excellente**\n\n`;
                } else if (analysis.performanceScore >= 70) {
                    report += `⚠️  **Performance acceptable**\n\n`;
                } else if (analysis.performanceScore >= 50) {
                    report += `🟡 **Performance à améliorer**\n\n`;
                } else {
                    report += `🔴 **Performance critique**\n\n`;
                }

                if (analysis.structureScore >= 90) {
                    report += `✅ **Structure excellente**\n\n`;
                } else if (analysis.structureScore >= 70) {
                    report += `⚠️  **Structure acceptable**\n\n`;
                } else if (analysis.structureScore >= 50) {
                    report += `🟡 **Structure à améliorer**\n\n`;
                } else {
                    report += `🔴 **Structure critique**\n\n`;
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

                // Lien vers le test GTmetrix
                if (result.testId) {
                    report += `#### Détails du Test\n\n`;
                    report += `- **ID du test:** ${result.testId}\n`;
                    report += `- **Lien GTmetrix:** https://gtmetrix.com/reports/${result.url.replace(/[^a-zA-Z0-9]/g, '')}/${result.testId}/\n\n`;
                }
            }
        });

        // Recommandations générales
        report += `## Recommandations Générales

### Optimisation de la Performance
- Optimiser les images (compression, formats modernes)
- Minifier les fichiers CSS et JavaScript
- Utiliser la compression gzip/brotli
- Implémenter la mise en cache
- Utiliser un CDN

### Optimisation de la Structure
- Optimiser le code HTML
- Éliminer le code CSS et JavaScript inutilisé
- Optimiser les requêtes à la base de données
- Utiliser des polices web optimisées
- Implémenter le lazy loading

### Optimisation du Réseau
- Utiliser HTTP/2
- Optimiser les requêtes
- Réduire le nombre de requêtes
- Utiliser la préconnexion
- Optimiser les ressources critiques

## Standards de Performance

- **Score de performance:** > 90/100
- **Score de structure:** > 90/100
- **Page Load Time:** < 3000ms
- **Taille de page:** < 2000KB

`;

        return report;
    }
}

// Fonction principale
async function main() {
    const baseUrl = process.argv[2] || 'http://localhost:8000';
    const tester = new GTmetrixTester(baseUrl);
    
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

module.exports = GTmetrixTester;
