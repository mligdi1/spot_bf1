/**
 * Tests d'accessibilité avec axe-core pour BF1 TV
 * Usage: node accessibility_tests.js [URL]
 */

const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

class AccessibilityTester {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.results = {};
        this.browser = null;
        this.page = null;
    }

    async init() {
        console.log('🚀 Initialisation du navigateur...');
        this.browser = await puppeteer.launch({
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        this.page = await this.browser.newPage();
        
        // Injecter axe-core
        await this.page.addScriptTag({
            url: 'https://unpkg.com/axe-core@4.7.0/axe.min.js'
        });
    }

    async testPage(endpoint, pageName) {
        console.log(`\n🔍 Test d'accessibilité: ${pageName}`);
        console.log(`URL: ${this.baseUrl}${endpoint}`);
        
        try {
            // Naviguer vers la page
            await this.page.goto(`${this.baseUrl}${endpoint}`, {
                waitUntil: 'networkidle2',
                timeout: 30000
            });

            // Attendre que la page soit complètement chargée
            await this.page.waitForTimeout(2000);

            // Exécuter les tests d'accessibilité
            const results = await this.page.evaluate(() => {
                return new Promise((resolve) => {
                    axe.run(document, {
                        rules: {
                            // Règles spécifiques à tester
                            'color-contrast': { enabled: true },
                            'keyboard-navigation': { enabled: true },
                            'focus-order-semantics': { enabled: true },
                            'heading-order': { enabled: true },
                            'landmark-unique': { enabled: true },
                            'link-name': { enabled: true },
                            'button-name': { enabled: true },
                            'image-alt': { enabled: true },
                            'form-field-multiple-labels': { enabled: true },
                            'label': { enabled: true }
                        }
                    }, (err, results) => {
                        if (err) {
                            resolve({ error: err.message });
                        } else {
                            resolve(results);
                        }
                    });
                });
            });

            // Analyser les résultats
            const analysis = this.analyzeResults(results);
            
            this.results[pageName] = {
                endpoint,
                results,
                analysis
            };

            console.log(`✅ Test terminé pour ${pageName}`);
            console.log(`   🔴 Violations critiques: ${analysis.critical}`);
            console.log(`   🟡 Violations sérieuses: ${analysis.serious}`);
            console.log(`   🟢 Violations modérées: ${analysis.moderate}`);
            console.log(`   ℹ️  Suggestions: ${analysis.minor}`);

        } catch (error) {
            console.error(`❌ Erreur lors du test de ${pageName}:`, error.message);
            this.results[pageName] = {
                endpoint,
                error: error.message
            };
        }
    }

    analyzeResults(results) {
        if (results.error) {
            return { error: results.error };
        }

        const analysis = {
            critical: 0,
            serious: 0,
            moderate: 0,
            minor: 0,
            violations: []
        };

        results.violations.forEach(violation => {
            const count = violation.nodes.length;
            
            switch (violation.impact) {
                case 'critical':
                    analysis.critical += count;
                    break;
                case 'serious':
                    analysis.serious += count;
                    break;
                case 'moderate':
                    analysis.moderate += count;
                    break;
                case 'minor':
                    analysis.minor += count;
                    break;
            }

            analysis.violations.push({
                id: violation.id,
                impact: violation.impact,
                description: violation.description,
                help: violation.help,
                helpUrl: violation.helpUrl,
                count: count,
                nodes: violation.nodes.map(node => ({
                    html: node.html,
                    target: node.target,
                    failureSummary: node.failureSummary
                }))
            });
        });

        return analysis;
    }

    async runAllTests() {
        console.log('♿ Lancement des tests d\'accessibilité BF1 TV');
        console.log('=' .repeat(50));

        await this.init();

        // Pages à tester
        const pagesToTest = [
            { endpoint: '/', name: 'Page d\'accueil' },
            { endpoint: '/login/', name: 'Page de connexion' },
            { endpoint: '/register/', name: 'Page d\'inscription' },
            { endpoint: '/cost-simulator/', name: 'Simulateur de coût' },
            { endpoint: '/home/', name: 'Accueil connecté' },
            { endpoint: '/admin/', name: 'Interface d\'administration' }
        ];

        // Tester chaque page
        for (const page of pagesToTest) {
            await this.testPage(page.endpoint, page.name);
        }

        // Générer le rapport
        await this.generateReport();

        // Fermer le navigateur
        await this.browser.close();

        console.log('\n🎉 Tests d\'accessibilité terminés!');
    }

    async generateReport() {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const resultsDir = 'accessibility_results';
        
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

        const jsonFile = path.join(resultsDir, `accessibility_results_${timestamp}.json`);
        fs.writeFileSync(jsonFile, JSON.stringify(jsonReport, null, 2));

        // Générer le rapport Markdown
        const mdReport = this.generateMarkdownReport();
        const mdFile = path.join(resultsDir, `accessibility_report_${timestamp}.md`);
        fs.writeFileSync(mdFile, mdReport);

        console.log(`\n📊 Rapport JSON généré: ${jsonFile}`);
        console.log(`📋 Rapport Markdown généré: ${mdFile}`);
    }

    generateMarkdownReport() {
        let report = `# Rapport d'Accessibilité BF1 TV

**Date:** ${new Date().toLocaleString()}
**URL de base:** ${this.baseUrl}
**Outil:** axe-core avec Puppeteer

## Résumé des Tests

`;

        // Calculer les totaux
        let totalCritical = 0;
        let totalSerious = 0;
        let totalModerate = 0;
        let totalMinor = 0;

        Object.values(this.results).forEach(result => {
            if (result.analysis && !result.analysis.error) {
                totalCritical += result.analysis.critical;
                totalSerious += result.analysis.serious;
                totalModerate += result.analysis.moderate;
                totalMinor += result.analysis.minor;
            }
        });

        report += `- 🔴 Violations critiques: ${totalCritical}
- 🟡 Violations sérieuses: ${totalSerious}
- 🟢 Violations modérées: ${totalModerate}
- ℹ️  Suggestions: ${totalMinor}

## Détails par Page

`;

        // Détails pour chaque page
        Object.entries(this.results).forEach(([pageName, result]) => {
            report += `### ${pageName}\n\n`;
            report += `**URL:** ${result.endpoint}\n\n`;

            if (result.error) {
                report += `❌ **Erreur:** ${result.error}\n\n`;
            } else if (result.analysis && result.analysis.error) {
                report += `❌ **Erreur d'analyse:** ${result.analysis.error}\n\n`;
            } else {
                const analysis = result.analysis;
                report += `- 🔴 Violations critiques: ${analysis.critical}
- 🟡 Violations sérieuses: ${analysis.serious}
- 🟢 Violations modérées: ${analysis.moderate}
- ℹ️  Suggestions: ${analysis.minor}

`;

                // Détails des violations
                if (analysis.violations.length > 0) {
                    report += `#### Violations Détectées\n\n`;
                    
                    analysis.violations.forEach(violation => {
                        const impactIcon = {
                            'critical': '🔴',
                            'serious': '🟡',
                            'moderate': '🟢',
                            'minor': 'ℹ️'
                        }[violation.impact] || '❓';

                        report += `##### ${impactIcon} ${violation.id}\n\n`;
                        report += `**Impact:** ${violation.impact}\n\n`;
                        report += `**Description:** ${violation.description}\n\n`;
                        report += `**Aide:** ${violation.help}\n\n`;
                        report += `**Nombre d'occurrences:** ${violation.count}\n\n`;
                        
                        if (violation.helpUrl) {
                            report += `**Lien d'aide:** ${violation.helpUrl}\n\n`;
                        }

                        // Exemples de violations
                        if (violation.nodes.length > 0) {
                            report += `**Exemples:**\n\n`;
                            violation.nodes.slice(0, 3).forEach((node, index) => {
                                report += `${index + 1}. \`${node.html}\`\n`;
                                if (node.failureSummary) {
                                    report += `   ${node.failureSummary}\n`;
                                }
                            });
                            report += '\n';
                        }
                    });
                } else {
                    report += `✅ **Aucune violation détectée!**\n\n`;
                }
            }
        });

        // Recommandations
        report += `## Recommandations

### Priorité Haute
- Corriger toutes les violations critiques immédiatement
- Mettre en place des tests d'accessibilité automatisés
- Effectuer des audits d'accessibilité réguliers

### Priorité Moyenne
- Corriger les violations sérieuses dans les 30 jours
- Mettre en place une politique d'accessibilité
- Former l'équipe aux bonnes pratiques d'accessibilité

### Priorité Faible
- Corriger les violations modérées lors des prochaines mises à jour
- Documenter les mesures d'accessibilité
- Mettre en place un monitoring d'accessibilité

## Standards de Référence

- [WCAG 2.1](https://www.w3.org/WAI/WCAG21/quickref/)
- [Section 508](https://www.section508.gov/)
- [RGAA 4.1](https://www.numerique.gouv.fr/publications/rgaa-accessibilite/)

`;

        return report;
    }
}

// Fonction principale
async function main() {
    const baseUrl = process.argv[2] || 'http://localhost:8000';
    const tester = new AccessibilityTester(baseUrl);
    
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

module.exports = AccessibilityTester;
