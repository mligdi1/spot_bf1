# Permissions et Accès

## Rôles

- `client`: accès complet aux fonctionnalités standard (campagnes, spots, diffusion, correspondance, rapports, conseils).
- `admin`: accès console d’administration uniquement; fonctionnalités clients bloquées.
- `editorial_manager`: accès exclusif à l’interface Rédaction.

## Restrictions

- `editorial_manager` ne peut pas accéder aux vues standard.
- Tentatives d’accès non autorisées sont journalisées et redirigées vers le dashboard Rédaction avec un message.

## Vues autorisées pour `editorial_manager`

- `editorial_dashboard`
- `editorial_coverage_detail`
- `editorial_assign_coverage`
- `editorial_journalists`
- `editorial_drivers`
- `login`, `logout`

## Nettoyage des permissions

- Les utilisateurs `editorial_manager` n’ont pas de permissions Django assignées (`is_staff` et `is_superuser` désactivés).

## Logs

- Préfixe `EDITORIAL_BLOCK` pour les tentatives bloquées.