#!/bin/bash

# Script de tests de performance avec Apache Bench pour BF1 TV
# Usage: ./ab_tests.sh [URL]

BASE_URL=${1:-"http://localhost:8000"}
RESULTS_DIR="performance_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "🚀 Tests de performance BF1 TV avec Apache Bench"
echo "URL de base: $BASE_URL"
echo "Timestamp: $TIMESTAMP"
echo "=================================================="

# Créer le répertoire des résultats
mkdir -p $RESULTS_DIR

# Configuration des tests
CONCURRENT_USERS=10
TOTAL_REQUESTS=100
TEST_DURATION=30

# Fonction pour exécuter un test
run_test() {
    local test_name=$1
    local endpoint=$2
    local method=${3:-GET}
    local data_file=$4
    
    echo "🔍 Test: $test_name"
    echo "Endpoint: $endpoint"
    echo "Méthode: $method"
    
    local output_file="$RESULTS_DIR/${test_name}_${TIMESTAMP}.txt"
    
    if [ "$method" = "POST" ] && [ -n "$data_file" ]; then
        ab -n $TOTAL_REQUESTS -c $CONCURRENT_USERS -p $data_file -T "application/x-www-form-urlencoded" "$BASE_URL$endpoint" > $output_file
    else
        ab -n $TOTAL_REQUESTS -c $CONCURRENT_USERS "$BASE_URL$endpoint" > $output_file
    fi
    
    # Extraire les métriques importantes
    echo "📊 Résultats pour $test_name:"
    grep "Requests per second" $output_file
    grep "Time per request" $output_file
    grep "Transfer rate" $output_file
    grep "Failed requests" $output_file
    echo ""
}

# Fonction pour exécuter un test de durée
run_duration_test() {
    local test_name=$1
    local endpoint=$2
    local duration=$3
    
    echo "⏱️  Test de durée: $test_name ($duration secondes)"
    
    local output_file="$RESULTS_DIR/${test_name}_duration_${TIMESTAMP}.txt"
    
    ab -t $duration -c $CONCURRENT_USERS "$BASE_URL$endpoint" > $output_file
    
    echo "📊 Résultats pour $test_name (durée):"
    grep "Requests per second" $output_file
    grep "Time per request" $output_file
    grep "Transfer rate" $output_file
    grep "Failed requests" $output_file
    echo ""
}

# Tests de base
echo "🧪 Tests de base"
echo "=================="

run_test "home_page" "/"
run_test "login_page" "/login/"
run_test "register_page" "/register/"
run_test "cost_simulator" "/cost-simulator/"
run_test "admin_interface" "/admin/"

# Tests de fichiers statiques
echo "📄 Tests de fichiers statiques"
echo "==============================="

run_test "static_css" "/static/css/tailwind.css"
run_test "favicon" "/favicon.ico"

# Tests de durée
echo "⏱️  Tests de durée"
echo "=================="

run_duration_test "home_page_duration" "/" $TEST_DURATION
run_duration_test "cost_simulator_duration" "/cost-simulator/" $TEST_DURATION

# Tests avec différentes charges
echo "⚡ Tests avec différentes charges"
echo "================================="

# Test avec plus d'utilisateurs concurrents
echo "🔍 Test avec 50 utilisateurs concurrents"
ab -n 500 -c 50 "$BASE_URL/" > "$RESULTS_DIR/high_load_${TIMESTAMP}.txt"
grep "Requests per second" "$RESULTS_DIR/high_load_${TIMESTAMP}.txt"
grep "Failed requests" "$RESULTS_DIR/high_load_${TIMESTAMP}.txt"
echo ""

# Test avec plus de requêtes
echo "🔍 Test avec 1000 requêtes"
ab -n 1000 -c 20 "$BASE_URL/" > "$RESULTS_DIR/many_requests_${TIMESTAMP}.txt"
grep "Requests per second" "$RESULTS_DIR/many_requests_${TIMESTAMP}.txt"
grep "Failed requests" "$RESULTS_DIR/many_requests_${TIMESTAMP}.txt"
echo ""

# Test de stress
echo "💥 Test de stress (5 minutes)"
ab -t 300 -c 100 "$BASE_URL/" > "$RESULTS_DIR/stress_test_${TIMESTAMP}.txt"
grep "Requests per second" "$RESULTS_DIR/stress_test_${TIMESTAMP}.txt"
grep "Failed requests" "$RESULTS_DIR/stress_test_${TIMESTAMP}.txt"
echo ""

# Génération du rapport
echo "📋 Génération du rapport de performance"
echo "======================================="

REPORT_FILE="$RESULTS_DIR/performance_report_${TIMESTAMP}.md"

cat > $REPORT_FILE << EOF
# Rapport de Performance BF1 TV

**Date:** $(date)
**URL de base:** $BASE_URL
**Configuration:**
- Utilisateurs concurrents: $CONCURRENT_USERS
- Requêtes totales: $TOTAL_REQUESTS
- Durée des tests: $TEST_DURATION secondes

## Résultats des Tests

### Tests de Base

EOF

# Ajouter les résultats de chaque test
for file in $RESULTS_DIR/*_${TIMESTAMP}.txt; do
    if [ -f "$file" ]; then
        test_name=$(basename "$file" "_${TIMESTAMP}.txt")
        echo "### $test_name" >> $REPORT_FILE
        echo '```' >> $REPORT_FILE
        grep -E "(Requests per second|Time per request|Transfer rate|Failed requests)" "$file" >> $REPORT_FILE
        echo '```' >> $REPORT_FILE
        echo "" >> $REPORT_FILE
    fi
done

cat >> $REPORT_FILE << EOF

## Recommandations

- **Performance excellente:** > 1000 req/s
- **Performance bonne:** 500-1000 req/s
- **Performance acceptable:** 100-500 req/s
- **Performance à améliorer:** < 100 req/s

## Fichiers de Résultats

Tous les fichiers de résultats détaillés sont disponibles dans le répertoire \`$RESULTS_DIR\`.

EOF

echo "✅ Rapport généré: $REPORT_FILE"
echo ""
echo "🎉 Tests de performance terminés!"
echo "📁 Résultats disponibles dans: $RESULTS_DIR/"
echo "📋 Rapport principal: $REPORT_FILE"
