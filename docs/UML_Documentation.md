# BF1 TV – Documentation UML

Ce document accompagne les diagrammes UML du projet BF1 TV. Il présente la méthodologie, les légendes, et la correspondance avec les fonctionnalités et données du site.

## Livrables

- Diagramme de cas d’utilisation (PlantUML): `UML_Cas_Utilisation_2025-11-25.puml`
- Diagramme de classes (PlantUML): `UML_Classes_2025-11-25.puml`
- Diagramme d’architecture (PlantUML/mermaid existant): `UML_Architecture_2025-11-25.puml`
- Ce guide: `UML_Documentation.md`

Les fichiers `.puml` sont modifiables et peuvent être rendus en PNG/PDF avec PlantUML. Exemple:

```bash
# Générer depuis PlantUML (nécessite Java et plantuml.jar)
java -jar plantuml.jar -tpdf docs/UML_Cas_Utilisation_2025-11-25.puml
java -jar plantuml.jar -tpdf docs/UML_Classes_2025-11-25.puml
```

## Méthodologie

1. Analyse des modèles (`spot/models.py`) pour identifier les entités, attributs et relations.
2. Analyse des vues (`spot/views.py`) et des signaux (`spot/signals.py`) pour dériver les cas d’utilisation (acteurs, scénarios, extensions).
3. Traduction en nomenclature française et simplification des attributs/méthodes.
4. Vérification de cohérence entre les diagrammes (entités référencées dans les cas d’utilisation et présentes dans les classes).

## Légendes et conventions

- Stéréotype `<<entity>>`: classe métier persistée (modèle Django).
- Multiplicités: `"1"`, `"*"`, `"0..1"` selon FK, M2M, optionnels.
- Types: simplifiés (string, text, date, datetime, decimal, url, bool).
- Choix (enum): représentés en texte dans les attributs (ex: `type: "info|success|warning|error"`).
- Inclusions (`<<include>>`) et extensions (`<<extend>>`) dans le cas d’utilisation suivent les bonnes pratiques UML.

## Acteurs (Cas d’utilisation)

- Visiteur: utilisateur non authentifié (inscription, contact).
- Client: utilisateur authentifié côté annonceur (campagnes, spots, calendrier, notifications, échanges).
- Administrateur: utilisateur interne BF1 (approbations, gestion des programmations, suivi global).
- Support: équipe en charge des demandes de contact.

## Correspondance fonctionnalités ↔ données

- Création/approbation de campagnes: `Campagne`, `HistoriqueCampagne`, `Notification`, signaux de création/approbation.
- Téléversement/validation de spots: `Spot`, `Notification`, `SpotSchedule` (programmations automatiques à l’approbation de campagne), `TimeSlot`.
- Calendrier de diffusion: `SpotSchedule`, `TimeSlot`.
- Notifications et redirections: `Notification` (liens vers `Campagne`, `Spot`, `FilCorrespondance`, `DemandeContact`).
- Échanges (threads): `FilCorrespondance`, `MessageCorrespondance`.
- Services et tarification: `CategorieService`, `Service`, `RegleTarification`.
- Conseils et contenus: `ArticleConseil`, `EtudeDeCas`, `SessionConseil`.

## Bonnes pratiques de modélisation UML respectées

- Séparation claire des responsabilités et relations.
- Multiplicités explicitement indiquées.
- Types d’attributs cohérents avec les modèles.
- Cas d’utilisation avec inclusions/extensions pour éviter la redondance.

## Évolutions et points d’extension

- Ajout d’un `Payment`/`Invoice` si la gestion de paiement revient (les modèles ont été supprimés dans le code, mais la structure permet de les réintroduire).
- Mise en place d’un Channel Layer Redis en production (déjà supporté côté settings) pour notifications en temps réel.
- Enrichissement des cas d’utilisation: marquage de notifications par type, filtres avancés, tableau de bord admin.

## Génération de PDF

Pour obtenir des versions PDF haute qualité:

- Utilisez PlantUML (standalone jar ou extension IDE) avec l’option `-tpdf`.
- Intégrez ces commandes dans votre pipeline CI/CD si nécessaire.