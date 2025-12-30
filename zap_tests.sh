#!/bin/bash

# Script de tests de sécurité avec OWASP ZAP pour BF1 TV
# Usage: ./zap_tests.sh [URL]

BASE_URL=${1:-"http://localhost:8000"}
RESULTS_DIR="security_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🔒 Tests de sécurité BF1 TV avec OWASP ZAP"
echo "URL de base: $BASE_URL"
echo "Timestamp: $TIMESTAMP"
echo "=========================================="

# Créer le répertoire des résultats
mkdir -p $RESULTS_DIR

# Configuration ZAP
ZAP_HOST="localhost"
ZAP_PORT="8080"
ZAP_API_KEY=""

# Fonction pour attendre que ZAP soit prêt
wait_for_zap() {
    echo "⏳ Attente que ZAP soit prêt..."
    while ! curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/core/view/version/" > /dev/null; do
        sleep 2
    done
    echo "✅ ZAP est prêt"
}

# Fonction pour démarrer ZAP
start_zap() {
    echo "🚀 Démarrage de ZAP..."
    zap.sh -daemon -host $ZAP_HOST -port $ZAP_PORT -config api.key=$ZAP_API_KEY &
    ZAP_PID=$!
    wait_for_zap
}

# Fonction pour arrêter ZAP
stop_zap() {
    echo "🛑 Arrêt de ZAP..."
    if [ ! -z "$ZAP_PID" ]; then
        kill $ZAP_PID
    fi
}

# Fonction pour exécuter un scan
run_scan() {
    local scan_name=$1
    local target_url=$2
    
    echo "🔍 Scan: $scan_name"
    echo "URL: $target_url"
    
    # Démarrer le scan
    curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/ascan/action/scan/?url=$target_url&recurse=true&inScopeOnly=false&scanPolicyName=&method=&postData=&contextId="
    
    # Attendre que le scan soit terminé
    while true; do
        status=$(curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/ascan/view/status/")
        progress=$(echo $status | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        
        if [ "$progress" = "100" ]; then
            break
        fi
        
        echo "Progression: $progress%"
        sleep 5
    done
    
    echo "✅ Scan terminé"
    
    # Récupérer les résultats
    local output_file="$RESULTS_DIR/${scan_name}_${TIMESTAMP}.json"
    curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/core/view/alerts/" > $output_file
    
    # Générer un rapport HTML
    local html_file="$RESULTS_DIR/${scan_name}_${TIMESTAMP}.html"
    curl -s "http://$ZAP_HOST:$ZAP_PORT/OTHER/core/other/htmlreport/" > $html_file
    
    echo "📊 Résultats sauvegardés: $output_file"
    echo "📋 Rapport HTML: $html_file"
}

# Fonction pour analyser les résultats
analyze_results() {
    local results_file=$1
    
    if [ -f "$results_file" ]; then
        echo "📈 Analyse des résultats:"
        
        # Compter les alertes par niveau
        high_count=$(grep -o '"risk":"High"' "$results_file" | wc -l)
        medium_count=$(grep -o '"risk":"Medium"' "$results_file" | wc -l)
        low_count=$(grep -o '"risk":"Low"' "$results_file" | wc -l)
        info_count=$(grep -o '"risk":"Informational"' "$results_file" | wc -l)
        
        echo "  🔴 Alertes critiques: $high_count"
        echo "  🟡 Alertes moyennes: $medium_count"
        echo "  🟢 Alertes faibles: $low_count"
        echo "  ℹ️  Informations: $info_count"
        
        # Afficher les alertes critiques
        if [ "$high_count" -gt 0 ]; then
            echo ""
            echo "🚨 Alertes critiques détectées:"
            grep -A 5 -B 5 '"risk":"High"' "$results_file" | grep '"name"' | head -5
        fi
    fi
}

# Fonction pour générer un rapport de sécurité
generate_security_report() {
    local report_file="$RESULTS_DIR/security_report_${TIMESTAMP}.md"
    
    cat > $report_file << EOF
# Rapport de Sécurité BF1 TV

**Date:** $(date)
**URL de base:** $BASE_URL
**Outil:** OWASP ZAP
**Version:** $(curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/core/view/version/" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)

## Résumé des Tests

EOF

    # Ajouter les résultats de chaque scan
    for file in $RESULTS_DIR/*_${TIMESTAMP}.json; do
        if [ -f "$file" ]; then
            scan_name=$(basename "$file" "_${TIMESTAMP}.json")
            echo "### $scan_name" >> $report_file
            echo "" >> $report_file
            
            # Compter les alertes
            high_count=$(grep -o '"risk":"High"' "$file" | wc -l)
            medium_count=$(grep -o '"risk":"Medium"' "$file" | wc -l)
            low_count=$(grep -o '"risk":"Low"' "$file" | wc -l)
            info_count=$(grep -o '"risk":"Informational"' "$file" | wc -l)
            
            echo "- 🔴 Alertes critiques: $high_count" >> $report_file
            echo "- 🟡 Alertes moyennes: $medium_count" >> $report_file
            echo "- 🟢 Alertes faibles: $low_count" >> $report_file
            echo "- ℹ️  Informations: $info_count" >> $report_file
            echo "" >> $report_file
            
            # Ajouter les détails des alertes critiques
            if [ "$high_count" -gt 0 ]; then
                echo "#### Alertes Critiques" >> $report_file
                echo "" >> $report_file
                grep -A 10 '"risk":"High"' "$file" | grep -E '"name"|"description"' | head -20 >> $report_file
                echo "" >> $report_file
            fi
        fi
    done
    
    cat >> $report_file << EOF

## Recommandations

### Priorité Haute
- Corriger toutes les alertes critiques immédiatement
- Mettre en place des tests de sécurité automatisés
- Effectuer des audits de sécurité réguliers

### Priorité Moyenne
- Corriger les alertes moyennes dans les 30 jours
- Mettre en place une politique de sécurité
- Former l'équipe aux bonnes pratiques de sécurité

### Priorité Faible
- Corriger les alertes faibles lors des prochaines mises à jour
- Documenter les mesures de sécurité
- Mettre en place un monitoring de sécurité

## Fichiers de Résultats

- **Rapports JSON:** \`$RESULTS_DIR/*_${TIMESTAMP}.json\`
- **Rapports HTML:** \`$RESULTS_DIR/*_${TIMESTAMP}.html\`
- **Rapport principal:** \`$report_file\`

EOF

    echo "📋 Rapport de sécurité généré: $report_file"
}

# Fonction principale
main() {
    echo "🔧 Vérification de ZAP..."
    
    # Vérifier si ZAP est installé
    if ! command -v zap.sh &> /dev/null; then
        echo "❌ OWASP ZAP n'est pas installé"
        echo "Installation: https://www.zaproxy.org/download/"
        exit 1
    fi
    
    # Démarrer ZAP
    start_zap
    
    # Exécuter les scans
    echo ""
    echo "🔍 Exécution des scans de sécurité"
    echo "=================================="
    
    run_scan "home_page" "$BASE_URL/"
    run_scan "login_page" "$BASE_URL/login/"
    run_scan "register_page" "$BASE_URL/register/"
    run_scan "cost_simulator" "$BASE_URL/cost-simulator/"
    run_scan "admin_interface" "$BASE_URL/admin/"
    
    # Analyser les résultats
    echo ""
    echo "📊 Analyse des résultats"
    echo "========================"
    
    for file in $RESULTS_DIR/*_${TIMESTAMP}.json; do
        if [ -f "$file" ]; then
            scan_name=$(basename "$file" "_${TIMESTAMP}.json")
            echo ""
            echo "🔍 $scan_name:"
            analyze_results "$file"
        fi
    done
    
    # Générer le rapport
    generate_security_report
    
    # Arrêter ZAP
    stop_zap
    
    echo ""
    echo "🎉 Tests de sécurité terminés!"
    echo "📁 Résultats disponibles dans: $RESULTS_DIR/"
    echo "📋 Rapport principal: $RESULTS_DIR/security_report_${TIMESTAMP}.md"
}

# Gestion des signaux
trap 'stop_zap; exit 1' INT TERM

# Exécution
main
