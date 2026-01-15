/**
 * Tests de performance avec Lighthouse pour BF1 TV
 * Usage: node lighthouse_tests.js [URL]
 */

const lighthouse = require('lighthouse');
const chromeLauncher = require('chrome-launcher');
const fs = require('fs');
const path = require('path');

class LighthouseTester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.results = {};
    }

    async testPage(endpoint, pageName) {
        console.log(`\n🔍 Test Lighthouse: ${pageName}`);
        console.log(`URL: ${this.baseUrl}${endpoint}`);
        
        const url = `${this.baseUrl}${endpoint}`;
        
        // Configuration Lighthouse
        const config = {
            extends: 'lighthouse:default',
            settings: {
                onlyAudits: [
                    'first-contentful-paint',
                    'largest-contentful-paint',
                    'first-meaningful-paint',
                    'speed-index',
                    'cumulative-layout-shift',
                    'total-blocking-time',
                    'interactive',
                    'performance-budget',
                    'unused-css-rules',
                    'unused-javascript',
                    'modern-image-formats',
                    'uses-optimized-images',
                    'uses-text-compression',
                    'uses-responsive-images',
                    'efficient-animated-content',
                    'preload-lcp-image',
                    'uses-rel-preconnect',
                    'uses-rel-preload',
                    'render-blocking-resources',
                    'unminified-css',
                    'unminified-javascript',
                    'uses-long-cache-ttl',
                    'total-byte-weight',
                    'uses-http2',
                    'uses-passive-event-listeners'
                ]
            }
        };

        try {
            // Lancer Chrome
            const chrome = await chromeLauncher.launch({ chromeFlags: ['--headless'] });
            
            // Configuration des options
            const options = {
                logLevel: 'info',
                output: 'json',
                onlyCategories: ['performance'],
                port: chrome.port
            };

            // Exécuter Lighthouse
            const runnerResult = await lighthouse(url, options, config);
            
            // Fermer Chrome
            await chrome.kill();

            // Analyser les résultats
            const analysis = this.analyzeResults(runnerResult.lhr);
            
            this.results[pageName] = {
                endpoint,
                url,
                results: runnerResult.lhr,
                analysis
            };

            console.log(`✅ Test terminé pour ${pageName}`);
            console.log(`   📊 Score de performance: ${analysis.performanceScore}/100`);
            console.log(`   ⚡ First Contentful Paint: ${analysis.fcp}ms`);
            console.log(`   🎯 Largest Contentful Paint: ${analysis.lcp}ms`);
            console.log(`   📱 Cumulative Layout Shift: ${analysis.cls}`);

        } catch (error) {
            console.error(`❌ Erreur lors du test de ${pageName}:`, error.message);
            this.results[pageName] = {
                endpoint,
                url,
                error: error.message
            };
        }
    }

    analyzeResults(lhr) {
        const analysis = {
            performanceScore: Math.round(lhr.categories.performance.score * 100),
            fcp: Math.round(lhr.audits['first-contentful-paint'].numericValue),
            lcp: Math.round(lhr.audits['largest-contentful-paint'].numericValue),
            cls: lhr.audits['cumulative-layout-shift'].numericValue,
            tbt: Math.round(lhr.audits['total-blocking-time'].numericValue),
            si: Math.round(lhr.audits['speed-index'].numericValue),
            ttfb: Math.round(lhr.audits['server-response-time'].numericValue),
            recommendations: []
        };

        // Analyser les audits et générer des recommandations
        Object.entries(lhr.audits).forEach(([auditId, audit]) => {
            if (audit.score !== null && audit.score < 0.9) {
                const recommendation = {
                    id: auditId,
                    title: audit.title,
                    description: audit.description,
                    score: Math.round(audit.score * 100),
                    impact: audit.score < 0.5 ? 'high' : audit.score < 0.8 ? 'medium' : 'low'
                };

                if (audit.details && audit.details.items) {
                    recommendation.items = audit.details.items.slice(0, 3);
                }

                analysis.recommendations.push(recommendation);
            }
        });

        return analysis;
    }

    async runAllTests() {
        console.log('🚀 Lancement des tests Lighthouse BF1 TV');
        console.log('=' .repeat(50));

        // Pages à tester
        const pagesToTest = [
            { endpoint: '/', name: 'Page d\'accueil' },
            { endpoint: '/login/', name: 'Page de connexion' },
            { endpoint: '/register/', name: 'Page d\'inscription' },
            { endpoint: '/cost-simulator/', name: 'Simulateur de coût' },
            { endpoint: '/home/', name: 'Accueil connecté' }
        ];

        // Tester chaque page
        for (const page of pagesToTest) {
            await this.testPage(page.endpoint, page.name);
        }

        // Générer le rapport
        await this.generateReport();

        console.log('\n🎉 Tests Lighthouse terminés!');
    }

    async generateReport() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const resultsDir = 'lighthouse_results';
        
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

        const jsonFile = path.join(resultsDir, `lighthouse_results_${timestamp}.json`);
        fs.writeFileSync(jsonFile, JSON.stringify(jsonReport, null, 2));

        // Générer le rapport Markdown
        const mdReport = this.generateMarkdownReport();
        const mdFile = path.join(resultsDir, `lighthouse_report_${timestamp}.md`);
        fs.writeFileSync(mdFile, mdReport);

        console.log(`\n📊 Rapport JSON généré: ${jsonFile}`);
        console.log(`📋 Rapport Markdown généré: ${mdFile}`);
    }

    generateMarkdownReport() {
        let report = `# Rapport de Performance Lighthouse BF1 TV

**Date:** ${new Date().toLocaleString()}
**URL de base:** ${this.baseUrl}
**Outil:** Google Lighthouse

## Résumé des Tests

`;

        // Calculer les moyennes
        let totalScore = 0;
        let pageCount = 0;
        let totalFcp = 0;
        let totalLcp = 0;
        let totalCls = 0;

        Object.values(this.results).forEach(result => {
            if (result.analysis && !result.error) {
                totalScore += result.analysis.performanceScore;
                totalFcp += result.analysis.fcp;
                totalLcp += result.analysis.lcp;
                totalCls += result.analysis.cls;
                pageCount++;
            }
        });

        if (pageCount > 0) {
            report += `- 📊 Score de performance moyen: ${Math.round(totalScore / pageCount)}/100
- ⚡ First Contentful Paint moyen: ${Math.round(totalFcp / pageCount)}ms
- 🎯 Largest Contentful Paint moyen: ${Math.round(totalLcp / pageCount)}ms
- 📱 Cumulative Layout Shift moyen: ${(totalCls / pageCount).toFixed(3)}

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
- ⚡ First Contentful Paint: ${analysis.fcp}ms
- 🎯 Largest Contentful Paint: ${analysis.lcp}ms
- 📱 Cumulative Layout Shift: ${analysis.cls}
- ⏱️  Total Blocking Time: ${analysis.tbt}ms
- 🚀 Speed Index: ${analysis.si}ms
- 🌐 Time to First Byte: ${analysis.ttfb}ms

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
                    
                    // Grouper par impact
                    const highImpact = analysis.recommendations.filter(r => r.impact === 'high');
                    const mediumImpact = analysis.recommendations.filter(r => r.impact === 'medium');
                    const lowImpact = analysis.recommendations.filter(r => r.impact === 'low');

                    if (highImpact.length > 0) {
                        report += `##### 🔴 Impact Élevé\n\n`;
                        highImpact.forEach(rec => {
                            report += `- **${rec.title}** (Score: ${rec.score}/100)\n`;
                            report += `  ${rec.description}\n\n`;
                        });
                    }

                    if (mediumImpact.length > 0) {
                        report += `##### 🟡 Impact Moyen\n\n`;
                        mediumImpact.forEach(rec => {
                            report += `- **${rec.title}** (Score: ${rec.score}/100)\n`;
                            report += `  ${rec.description}\n\n`;
                        });
                    }

                    if (lowImpact.length > 0) {
                        report += `##### 🟢 Impact Faible\n\n`;
                        lowImpact.forEach(rec => {
                            report += `- **${rec.title}** (Score: ${rec.score}/100)\n`;
                            report += `  ${rec.description}\n\n`;
                        });
                    }
                } else {
                    report += `✅ **Aucune recommandation majeure!**\n\n`;
                }
            }
        });

        // Recommandations générales
        report += `## Recommandations Générales

### Optimisation des Images
- Utiliser des formats modernes (WebP, AVIF)
- Optimiser la taille des images
- Implémenter le lazy loading
- Utiliser des images responsives

### Optimisation du CSS et JavaScript
- Minifier les fichiers CSS et JavaScript
- Éliminer le code CSS et JavaScript inutilisé
- Utiliser la compression gzip/brotli
- Implémenter le code splitting

### Optimisation du Réseau
- Utiliser HTTP/2
- Implémenter la mise en cache
- Utiliser un CDN
- Optimiser les polices web

### Optimisation du Rendu
- Éviter les ressources bloquantes
- Utiliser la préconnexion
- Optimiser le Critical Rendering Path
- Implémenter le Service Worker

## Standards de Performance

- **First Contentful Paint:** < 1.8s
- **Largest Contentful Paint:** < 2.5s
- **Cumulative Layout Shift:** < 0.1
- **Total Blocking Time:** < 200ms
- **Speed Index:** < 3.4s

`;

        return report;
    }
}

// Fonction principale
async function main() {
    const baseUrl = process.argv[2] || 'http://localhost:8000';
    const tester = new LighthouseTester(baseUrl);
    
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

module.exports = LighthouseTester;
