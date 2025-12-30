# Migration PostgreSQL – Administration Django

Ce guide aide à restaurer l'administration après migration de SQLite vers PostgreSQL.

## 1) Configuration base de données
- Vérifiez `DATABASES` dans `spot_bf1/spot_bf1/settings.py`:
  - `ENGINE: django.db.backends.postgresql`
  - `NAME, USER, PASSWORD, HOST, PORT`
  - Assurez-vous que le port correspond à votre instance (ex: `5432` ou `5433`).

## 2) Migrations et permissions
- Appliquez les migrations:
  - `python manage.py migrate`
- Si vous utilisez un modèle utilisateur personnalisé (`AUTH_USER_MODEL = 'spot.User'`), toutes les migrations de `auth` et de votre app doivent être appliquées.

## 3) Superuser et staff
- Créez ou vérifiez le superuser:
  - `python manage.py createsuperuser`
- Vérifiez qu'il a `is_superuser=True` et `is_staff=True`.

## 4) Vérifications automatisées
- Lancez la commande:
  - `python manage.py check_admin_integrity`
- Elle affiche:
  - Liste des superusers
  - Nombre de comptes staff, groupes et permissions
  - Présence de `django.contrib.admin` dans `INSTALLED_APPS`
  - Présence de `/admin/` dans les URLs
  - Infos DB (engine, host, port)

## 5) Accès à l'interface admin
- Ouvrez `/admin/` et connectez-vous avec le superuser.
- Si l'accès échoue, consultez les logs du serveur et vérifiez:
  - Connexion PostgreSQL (host/port/credentials)
  - Migrations manquantes
  - Incohérences du modèle utilisateur

## 6) Séparation des rôles
- Testez avec un compte normal (non staff, non superuser):
  - Pas d'accès à `/admin/` (403 ou redirection login).
- Testez le superuser:
  - Accès complet.
- Vérifiez vos limitations existantes (middlewares, permissions custom, etc.).

## 7) Différences SQLite vs PostgreSQL
- Types et contraintes plus strictes (nullable, unique).
- Séquences d'auto-incrément et bigints.
- Comportements de transactions (ATOMIC_REQUESTS recommandé).

## 8) Dépannage rapide
- Port incorrect: ajustez `DATABASES['default']['PORT']`.
- Permissions absentes: réappliquez `migrate`, vérifiez `django.contrib.auth`.
- Superuser manquant: `createsuperuser`.
- Modèle utilisateur personnalisé: assurez que la migration initiale est bien appliquée avant les autres apps.