# BF1 TV - Application de Gestion Publicitaire

Une application web complète développée avec Django pour la gestion des campagnes publicitaires de BF1 TV au Burkina Faso.

## 🎯 Objectifs

- Moderniser et simplifier l'accès à la publicité télévisée au Burkina Faso
- Offrir une expérience utilisateur pédagogique et inclusive
- Couvrir l'ensemble du processus : souscription, gestion des spots, paiement, facturation et consultation historique

## ✨ Fonctionnalités principales

### 🔐 Système d'authentification sécurisée
- Connexion multi-profils : clients, administrateurs, diffuseurs, responsables rédaction
- Gestion des sessions et des rôles avec permissions différenciées
- Sécurité des données avec hachage des mots de passe

### 📢 Module de souscription aux campagnes
- Formulaire détaillé pour soumettre des demandes de campagnes
- Possibilité d'uploader un spot publicitaire ou de demander une création
- Validation des données côté client et serveur

### 🎬 Gestion des spots publicitaires
- Système de téléversement de médias (vidéo + image) avec validation
- Interface administrateur pour valider et planifier les spots
- Calendrier de diffusion visible pour les clients

### 💳 Paiement (prévu / optionnel)
- Variables d’environnement prêtes côté production pour Mobile Money
- Activation contrôlée par feature-flag (`ENABLE_PAYMENTS`) et implémentation à compléter selon le prestataire

### 📄 Génération et gestion de documents
- Exports PDF/Excel de rapports et listes (selon dépendances installées)
- Génération PDF de certains documents (ex: détails d’une demande de couverture)
- Notifications email (backend console en dev, SMTP en prod)

### 📊 Tableau de bord administrateur
- Interface complète de gestion des demandes, paiements et diffusions
- Visualisations de données et statistiques mensuelles
- Modération et validation des contenus

### 📚 Archivage et historique des campagnes
- Accès aux anciennes campagnes
- Réutilisation ou modification de spots précédents
- Historique organisé avec filtres et options de recherche

## 🛠️ Technologies utilisées

### Backend
- **Django 5.2.5** - Framework web Python
- **PostgreSQL** - Base de données relationnelle
- **Django ORM** - Mapping objet-relationnel
- **Django Admin** - Interface d'administration

### Frontend
- **HTML5, CSS3, JavaScript** - Technologies web standard
- **Tailwind CSS** - Framework CSS utilitaire
- **Font Awesome** - Icônes
- **Alpine.js** - Framework JavaScript léger

### Outils et bibliothèques
- **django-crispy-forms** - Formulaires stylés
- **Pillow** - Traitement d'images
- **ReportLab** - Génération de PDF
- **psycopg2** - Driver PostgreSQL

## 🚀 Installation et configuration

### Prérequis
- Python 3.8+
- PostgreSQL 12+
- pip (gestionnaire de paquets Python)

### Installation

1. **Cloner le projet**
```bash
git clone <repository-url>
cd spot_bf1
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configuration de la base de données**
```bash
# Créer la base de données PostgreSQL
createdb spot_bf1_db

# Appliquer les migrations
python manage.py makemigrations
python manage.py migrate
```

5. **Initialiser les données de base**
```bash
python manage.py init_data
```

6. **Lancer le serveur de développement**
```bash
python manage.py runserver
```

L'application sera accessible à l'adresse : http://localhost:8000

### Comptes par défaut

### Compte administrateur

Créez un compte admin localement via :

```bash
python manage.py createsuperuser
```

URL admin : http://localhost:8000/admin/

## 📁 Structure du projet

```
spot_bf1/
├── spot/                          # Application principale
│   ├── models.py                  # Modèles de données
│   ├── views.py                   # Vues de l'application
│   ├── forms.py                   # Formulaires
│   ├── admin.py                   # Configuration admin
│   ├── signals.py                 # Signaux Django
│   ├── urls.py                    # URLs de l'application
│   ├── templates/                 # Templates HTML
│   │   └── spot/
│   │       ├── base.html          # Template de base
│   │       ├── home.html          # Page d'accueil
│   │       ├── dashboard.html     # Tableau de bord
│   │       ├── campaign_*.html    # Templates campagnes
│   │       ├── spot_*.html        # Templates spots
│   │       └── admin_*.html       # Templates admin
│   └── management/                # Commandes de gestion
│       └── commands/
│           └── init_data.py       # Initialisation des données
├── spot_bf1/                      # Configuration du projet
│   ├── settings.py                # Paramètres Django
│   ├── urls.py                    # URLs principales
│   └── wsgi.py                    # Configuration WSGI
├── static/                        # Fichiers statiques
├── media/                         # Fichiers média
├── requirements.txt               # Dépendances Python
└── README.md                      # Documentation
```

## 🧩 Architecture et modules (vue d’ensemble)

### Applications
- `spot/` : application principale (modèles, vues, templates, exports, notifications, chatbot, diffusion, rédaction).
- `spot_bf1/` : configuration Django (settings, urls, asgi/wsgi, logs).

### Stockage
- Base de données : PostgreSQL par défaut (dev) avec fallback SQLite si `DJANGO_USE_SQLITE=1`.
- Médias : `media/` (uploads image/vidéo, pièces jointes) servi en dev par Django, en prod par Nginx.
- Statique : `static/` (sources) + `staticfiles/` (collectstatic).

### Temps réel (WebSocket)
Le projet utilise Django Channels (ASGI) pour pousser des mises à jour en temps réel :
- `ws/admin/pending-counts/` : compteurs d’éléments “en attente” côté console admin.
- `ws/diffusion/planning/` : snapshot + mises à jour du planning côté diffusion.

## 👥 Rôles et parcours

- **Client** : créer des campagnes, déposer des médias, suivre la diffusion, consulter notifications/échanges.
- **Administrateur** : valider/rejeter campagnes et spots, suivre l’activité globale, gérer la console.
- **Diffuseur** : interface dédiée `/diffusion/` (planning, confirmation des diffusions, exports).
- **Responsable rédaction** : écrans “editorial” (assignations, planning, notifications, ressources).

## 🌐 Routes clés

### Public / Auth
- `/` et `/home/` : accueil
- `/register/` : inscription
- `/login/` et `/logout/` : session

### Client
- `/campaigns/` + `/campaigns/create/` + `/campaigns/<uuid>/`
- `/campaigns/<uuid>/upload/` : dépôt média
- `/broadcasts/` : grille de diffusion
- `/notifications/` + `/profile/`

### Diffusion
- `/diffusion/` : home diffuseur
- `/diffusion/planning/` : planning, confirmation/annulation diffusion
- `/diffusion/spots/` et exports : CSV / XLSX / PDF selon vues et dépendances

### Console admin
- `/console/login/` + `/console/dashboard/`
- `/console/campaigns/…` et `/console/spots/…` (validation)

## 🎨 Design et couleurs

L'application utilise les couleurs officielles de BF1 TV :
- **Rouge principal** : #DC2626
- **Rouge foncé** : #B91C1C
- **Rouge clair** : #FEE2E2
- **Blanc** : #FFFFFF
- **Gris** : #F8FAFC

## 📱 Responsive Design

L'application est entièrement responsive et s'adapte à tous les appareils :
- **Mobile** : Interface optimisée pour les smartphones
- **Tablette** : Adaptation pour les écrans moyens
- **Desktop** : Interface complète pour les ordinateurs

## 🔒 Sécurité

- Authentification sécurisée avec hachage des mots de passe
- Protection CSRF sur tous les formulaires
- Validation des données côté client et serveur
- Gestion des permissions par rôle utilisateur
- Upload sécurisé des fichiers vidéo

## 🧪 Tests

```bash
# Lancer les tests
python manage.py test

# Tests avec couverture
coverage run --source='.' manage.py test
coverage report
```

## 📊 Rapports et Exports

- Vue `Rapports` (`/reports/overview/`) affiche une synthèse filtrée par période.
- Exports disponibles:
  - `Excel` (`/reports/export/?start=YYYY-MM-DD&end=YYYY-MM-DD`)
  - `PDF` (`/reports/export/pdf/?start=YYYY-MM-DD&end=YYYY-MM-DD`)

### Spécifications de filtrage
- Les paramètres `start` et `end` au format `YYYY-MM-DD` sont toujours appliqués.
- Si absents ou invalides, défaut au mois courant.
- Si `start > end`, inversion automatique.
- Période maximale: 365 jours.
- Cohérence des critères entre formats: mêmes calculs et requêtes que la vue `Rapports`.

### Expérience utilisateur
- Le filtre affiché dans l’interface correspond exactement à la période exportée.
- Un indicateur de chargement est visible lors du filtrage.
- En cas d’erreur de dépendance (ex: `openpyxl` manquant), un message explicite est affiché.

### Captures d’écran (à ajouter)
- `static/screenshots/reports_overview.png`: Vue des rapports avec filtres.
- `static/screenshots/export_excel.png`: Exemple d’export Excel.
- `static/screenshots/export_pdf.png`: Exemple d’export PDF.

### Limitations connues
- L’export Excel requiert `openpyxl`. Installez via `pip install openpyxl`.
- Le parsing de contenu PDF n’est pas prévu côté interface.

### Tests de filtrage
- Tests unitaires couvrent:
  - Plages valides
  - Périodes vides (défaut au mois)
  - Chevauchements/inversion de dates
  - Formats de date invalides

## 📈 Déploiement

### Base de données (PostgreSQL par défaut)
Le projet est configuré pour utiliser PostgreSQL par défaut. L’option SQLite ci-dessous existe uniquement pour dépanner un environnement local rapide (sans serveur PostgreSQL).

### Développement local (SQLite)
Si tu veux éviter PostgreSQL en local, tu peux lancer avec SQLite :
```bash
set DJANGO_USE_SQLITE=1
python manage.py migrate
python manage.py init_data
python manage.py runserver 0.0.0.0:8000
```

### Docker (recommandé pour un environnement complet)
Le `docker-compose.yml` fournit : PostgreSQL + Redis + Django + Nginx.
```bash
docker compose up --build
```
Ports :
- App Django : `http://localhost:8000`
- Nginx : `http://localhost` (et `https://localhost` si SSL configuré)

### Production

1. **Configuration des variables d'environnement**
```bash
export DEBUG=False
export SECRET_KEY='your-secret-key'
export DATABASE_URL='postgresql://user:password@host:port/dbname'
```

2. **Collecte des fichiers statiques**
```bash
python manage.py collectstatic
```

3. **Déploiement avec Gunicorn**
```bash
gunicorn spot_bf1.wsgi:application
```

### Variables d’environnement (repères)
Un exemple est disponible dans `.env.example`. Les variables importantes :
- `SECRET_KEY`, `ALLOWED_HOSTS`, `DEBUG`
- `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`
- `REDIS_URL` (prod)
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`
- `SITE_URL`
- Mobile Money (prévu) : `MOBILE_MONEY_API_URL`, `MOBILE_MONEY_API_KEY`, `MOBILE_MONEY_MERCHANT_ID`
- Chatbot local : `CHATBOT_ENABLED`, `CHATBOT_PROVIDER`, `CHATBOT_MODEL_PATH` (optionnel)

## 📌 Notes techniques / points à surveiller
- Certaines sections historiques (paiement, facturation) sont décrites comme objectifs, mais l’implémentation actuelle privilégie exports/notifications et workflows campagne→spot→diffusion.
- En prod, privilégier `settings_production.py` + variables d’environnement (pas de secrets en dur).

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

Pour toute question ou support :
- Email : zoupoumarcel@gmail.com 
- Téléphone : +226 70 80 33 44
- Adresse : Ouagadougou, Burkina Faso

## 🙏 Remerciements

- Équipe BF1 TV pour la confiance accordée
- Communauté Django pour l'excellent framework
- Contributeurs open source pour les bibliothèques utilisées

---

**BF1 TV** - Votre partenaire publicitaire de confiance au Burkina Faso 🇧🇫
 # BF1 TV – Gestion Publicitaire

Un système web de gestion des campagnes publicitaires (spots, calendriers, notifications, échanges) destiné aux équipes BF1 TV et aux annonceurs. Le projet offre une expérience moderne avec une interface Tailwind/Crispy, notifications en temps réel via Django Channels, et une intégration simplifiée pour le déploiement (Docker, Nginx, Gunicorn/Daphne).

---

## Sommaire

- [Utilisateur](#utilisateur)
  - [Présentation](#présentation)
  - [Fonctionnalités principales](#fonctionnalités-principales)
  - [Prérequis d’utilisation](#prérequis-dutilisation)
  - [Prise en main rapide](#prise-en-main-rapide)
  - [Captures d’écran](#captures-décran)
- [Technique](#technique)
  - [Architecture globale](#architecture-globale)
  - [Technologies et versions](#technologies-et-versions)
  - [Structure des fichiers](#structure-des-fichiers)
  - [Dépendances principales](#dépendances-principales)
  - [Points d’extension](#points-dextension)
- [Déploiement](#déploiement)
  - [Installation locale](#installation-locale)
  - [Configuration requise](#configuration-requise)
  - [Variables d’environnement](#variables-denvironnement)
  - [Mise à jour](#mise-à-jour)
  - [Options de déploiement](#options-de-déploiement)

---

## Utilisateur

### Présentation

- Objectif: centraliser la création, le suivi et la diffusion des spots publicitaires, simplifier les échanges entre annonceurs et équipe BF1 TV, et offrir une visibilité claire sur les calendriers de diffusion.
- Valeur ajoutée: interface unifiée, notifications intelligentes, flux de travail cohérent (de la campagne au spot), intégration et performances solides.

### Fonctionnalités principales

- Gestion des campagnes: création, description, statut, objectifs, suivi.
- Téléversement et gestion des spots: import de médias (vidéo), métadonnées, association aux campagnes.
- Calendrier de diffusion: planification, vue calendrier, suivi des programmations.
- Notifications: redirections intelligentes vers campagne/spot/thread, filtres et compteur des non lus.
- Échanges et demandes: messages, threads, demandes administratives (avec toasts et messages cohérents).
- Tableau de bord: vues synthétiques et actions rapides.
- Chatbot et Widget WhatsApp: aide contextuelle et canal direct vers le support.
- Export/rapports: génération de pièces (PDF via ReportLab) et visuels pour communication.

### Prérequis d’utilisation

- Matériel: ordinateur ou tablette avec écran >= 1280px recommandé.
- Logiciel: navigateur moderne (Chrome, Edge, Firefox, Safari) à jour; connexion Internet stable.
- Compte: identifiants fournis par l’administrateur ou inscription selon la politique du site.

### Prise en main rapide

1. Se connecter: accéder à `/login/`, puis arriver sur le tableau de bord.
2. Créer une campagne: remplir les informations essentielles (titre, objectif), enregistrer.
3. Téléverser un spot: l’associer à une campagne existante, importer le média.
4. Planifier la diffusion: utiliser le calendrier pour définir les créneaux.
5. Suivre ses notifications: visiter `/notifications/`, filtrer et ouvrir les éléments pertinents.
6. Contacter le support: via le Chatbot ou le widget WhatsApp.

### Captures d’écran

![Aperçu des spots](static/bf1_spots.jpg)

---

## Technique

### Architecture globale

```mermaid
graph TD
  U[Utilisateur] --> B[Navigateur (Tailwind/Crispy)]
  B --> A[Django ASGI]
  A --> V[Views/Templates]
  A --> C[Channels (WebSocket)]
  A --> D[(PostgreSQL)]
  A --> R[(Redis: cache / option channel layer)]
  A --> S[Static/Media via Whitenoise ou Nginx]
```

- Dev: ASGI (Daphne) et Channel Layer en mémoire (`InMemoryChannelLayer`).
- Prod: cache Redis activé; Channel Layer Redis recommandée (configurable si nécessaire).
- Servir les statiques: Whitenoise en dev; Nginx en prod (via Docker Compose).

### Technologies et versions

- Python: 3.12 (recommandé)
- Django: `5.2.5`
- Channels: `4.1.0` + Daphne `4.1.2`
- Crispy Forms: `2.1` + `crispy-tailwind` `0.5.0`
- Base de données: PostgreSQL
- Autres: `Pillow 10.4.0`, `reportlab 4.2.2`, `python-decouple 3.8`, `whitenoise 6.6.0`, `gunicorn 21.2.0`, `django-extensions 3.2.3`

### Structure des fichiers

- `spot_bf1/` (racine du projet)
  - `manage.py`: commandes Django.
  - `spot_bf1/`: configuration projet (ASGI/WSGI, `settings.py`, `settings_production.py`, `urls.py`).
  - `spot/`: application principale (models, views, templates, signals, middleware, routing Channels).
  - `static/`: assets statiques (icônes, images, svg).
  - `media/`: fichiers téléversés et données locales (chatbot, correspondences, spots).
  - Outils/tests: `accessibility_test.py`, `performance_test.py`, `security_test.py`, scripts JS (Lighthouse, GTMetrix, Pingdom, Datadog, NewRelic), `locustfile.py`.
  - Déploiement: `Dockerfile`, `docker-compose.yml`, `nginx.conf`, `gunicorn.conf.py`, `start.sh`.

### Dépendances principales

- Backend: Django, Channels, Daphne
- Frontend: Crispy Forms + Tailwind (via packs Crispy)
- DB/Cache: PostgreSQL, Redis (cache prod)
- Statique: Whitenoise (dev), Nginx (prod)
- Utilitaires: Pillow (images), ReportLab (PDF), python-decouple, django-extensions

### Points d’extension

- Apps Django: ajouter des applications sous `spot/` ou en créer de nouvelles.
- Signals: brancher des traitements aux événements (création spot/campagne, notifications) via `spot/signals.py`.
- Templates: élargir l’UI dans `spot/templates/spot`, réutiliser les composants (`includes/`).
- WebSocket/Temps réel: créer de nouveaux consumers sous `spot/consumers.py` et routes Channels dans `spot/routing.py`.
- Services: factoriser les traitements métier sous `spot/services/`.
- Feature flags: exemple `ENABLE_PAYMENTS` dans `settings.py` pour activer des modules.
- Chatbot & Widget WhatsApp: options configurables dans `settings.py`/`settings_production.py`.

---

## Déploiement

### Installation locale

Pré-requis:

- Python 3.12, Node non requis (Tailwind via Crispy), PostgreSQL local, Redis optionnel.

Étapes:

```bash
# 1) Créer l’environnement Python
python -m venv env
./env/Scripts/activate  # Windows PowerShell

# 2) Installer les dépendances
pip install -r requirements.txt

# 4) Appliquer les migrations
python manage.py migrate

# 5) Créer un compte administrateur
python manage.py createsuperuser

# 6) Lancer le serveur
python manage.py runserver
```

Commandes utiles:

- Générer les favicons: `python manage.py generate_favicons`
- Collecter les statiques (prod): `python manage.py collectstatic`

### Configuration requise

- Dev:
  - DB: PostgreSQL (par défaut `localhost:5433`, cf. `settings.py`).
  - ASGI: `spot_bf1.asgi.application` actif, Channels en mémoire.
  - Statique: `static/` servi par Django (Whitenoise activé).
- Prod (via Docker Compose):
  - `db` (PostgreSQL 15), `redis` (Redis 7), `web` (Django), `nginx`.
  - Statiques/Média montés en volume.

### Variables d’environnement

Production (`settings_production.py`):

- Sécurité: `SECRET_KEY`, `ALLOWED_HOSTS`
- Base de données: `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`
- Cache: `REDIS_URL`
- Fichiers: `STATIC_ROOT`, `MEDIA_ROOT`
- Email: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`
- Site: `SITE_URL`
- WhatsApp Widget: `WHATSAPP_PHONE`, `WHATSAPP_DEFAULT_MESSAGE`, `WHATSAPP_WIDGET_ENABLED`, `WHATSAPP_WIDGET_POSITION`, `WHATSAPP_WIDGET_COLOR`, `WHATSAPP_WIDGET_SIZE`

Options techniques (dev):

- Chatbot local: `CHATBOT_MODEL_PATH`, `CHATBOT_MAX_CONTEXT`, `CHATBOT_KNOWLEDGE_DIR`, `CHATBOT_ENABLE_PERSISTENT_MEMORY`, `CHATBOT_MEMORY_PATH`

### Mise à jour

Procédure type (prod):

```bash
# 1) Récupérer les dernières modifications
git pull

# 2) Mettre à jour les dépendances
pip install -r requirements.txt

# 3) Appliquer les migrations
python manage.py migrate

# 4) Collecter les statiques
python manage.py collectstatic --noinput

# 5) Redémarrer les services (ex: systemd, Docker)
# Docker Compose
docker compose down && docker compose up -d --build
```

### Options de déploiement

- Local (développement): `runserver`, DB locale, Whitenoise.
- Docker (prod): `docker-compose.yml` avec services `db`, `redis`, `web`, `nginx`.
- Cloud/VM: Nginx en frontal (80/443), Gunicorn pour WSGI et Daphne pour ASGI, Redis managé (cache et channel layer), PostgreSQL managé.

Exemple Docker Compose (extrait):

```yaml
services:
  db:
    image: postgres:15
  redis:
    image: redis:7-alpine
  web:
    build: .
    environment:
      - DJANGO_SETTINGS_MODULE=spot_bf1.settings_production
      - REDIS_URL=redis://redis:6379/1
  nginx:
    image: nginx:alpine
```

---

## Notes et bonnes pratiques

- Sécurité: en prod, `DEBUG=False`, configurez `ALLOWED_HOSTS`, HTTPS forcé (HSTS, cookies sécurisés), mots de passe via secrets.
- Performances: activer cache Redis, utiliser Nginx pour statiques, exécuter les tests de performance (`locustfile.py`, scripts Lighthouse/GTMetrix/Pingdom).
- Observabilité: journaux rotatifs (`logging_config`/prod), tests Datadog/NewRelic disponibles.
- Accessibilité: lancer `accessibility_test.py` et `accessibility_tests.js`.
- Notifications: vérifier `/notifications/` pour l’UX (badge non lus, toasts positionnés et non obstruants).

---

## Support

- Problème ou question: contactez l’équipe via le widget WhatsApp ou la page Contact.
- Incidents techniques: fournir les logs (`logs/errors.log`, logs serveur) et la version de l’application.
