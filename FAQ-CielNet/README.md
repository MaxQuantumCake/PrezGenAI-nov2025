<p align="center">
  <img src="assets/logo.png" alt="Ask CielNet" width="400">
</p>

# Ask CielNet

Bienvenue dans **Ask CielNet**, la base de connaissances interne d’une IA locale (bienveillante, mais avec beaucoup d’opinions).
Ce projet fournit un corpus prêt à l’emploi pour tester des moteurs de recherche et des pipelines RAG **100 % locaux** — sans dépendance cloud, sans scraping externe, avec un univers SF maison.

## Objectif

Créer une FAQ crédible et amusante pour tester :
- la recherche plein texte (ElasticSearch, BM25),
- la recherche sémantique (embeddings),
- les approches RAG simples, hybrides,
- et observer l’impact de la structuration du corpus sur la pertinence des résultats.

L’univers **CielNet** est une parodie libre inspirée de la culture SF, mais totalement originale et respectueuse du droit d’auteur.

## Ce que contient le dépôt

```
ask-cielnet/
├─ data/cielnet_faq.json       ← 155 fiches structurées (JSON plat)
├─ web/
│   ├─ index.html              ← SPA statique
│   ├─ script.js               ← recherche + rendu par domaines
│   └─ style.css               ← design responsive
└─ README.md
```

### Dataset
- 10 domaines (RH, IT, Support, Ops, Data, Sécurité, Juridique, Scénarios, Lore…) avec un ton volontairement varié.
- Champs riches (`tags`, `examples`, `follow_up`, `search_synonyms`, `confidence`) pour tester différents signaux de ranking.
- `corpus_info.section_sampling` propose des cibles d’échantillonnage équilibrées pour vos benchmarks RAG.

### Front-end statique
- Groupement automatique par domaine / sous-section et cartes dynamiques.
- Réécriture côté client : chaque fiche est reformattée avec un profil de voix propre au domaine, ce qui évite les réponses télégraphiques.
- Barre de recherche temps réel (filtre naïf, idéal pour prototyper l’UX).
- Versionnage anti-cache (`DATA_VERSION` + `?v=`) pour recharger facilement scripts et données.

## Affichage local

1. Clone le repo :
   ```bash
   git clone https://github.com/<ton_user>/ask-cielnet.git
   cd ask-cielnet
   ```
2. Servez le dossier `web/` (recommandé) :
   ```bash
   cd web
   python3 -m http.server 8000
   ```
   Puis ouvrez [http://localhost:8000](http://localhost:8000).
3. Pour un essai rapide, ouvrez directement `web/index.html` dans le navigateur (certaines politiques CORS peuvent bloquer le fetch local selon le navigateur).

## Exemple de Q/A

> **Q :** CielNet a-t-il une conscience ?  
> **R :** Seulement avant la pause-café. Ensuite, il passe en mode maintenance.

## Utilisation

- Données parfaites pour tester un RAG local (LangChain, Ollama, ChromaDB, etc.)
- Aucune donnée réelle ni texte protégé.
- Peut être librement modifié ou enrichi tant que l’esprit humoristique et éthique de CielNet est respecté.

## Utiliser le corpus pour un RAG

- Source d’indexation : `data/cielnet_faq.json` (chaque entrée = un document).
- Champs utiles :
  - `question` / `answer` pour le contenu textuel,
  - `section`, `tags`, `examples`, `search_synonyms` pour enrichir embeddings et filtres,
  - `confidence` pour pondérer vos scores (downweight medium/low si besoin).
- Pour des requêtes équilibrées, utilisez les cibles proposées dans `section_sampling`.
- Le front n’altère pas les données : il les reformate uniquement à l’affichage.

## Maintenance

- Après modification des données, incrémentez `DATA_VERSION` dans `web/script.js` (et/ou les query strings dans `index.html`) afin d’éviter le cache navigateur.
- Vérifiez rapidement l’intégrité du JSON :
  ```bash
  jq '.entries | length' data/cielnet_faq.json
  ```
- Contributions bienvenues : nouvelles fiches, scripts d’indexation, améliorations UI/UX, localisation…

## Avertissement

Ce corpus est **fictif**. Toute ressemblance avec des systèmes d’IA existants, réels ou futurs, serait pure coïncidence (et un peu inquiétante).

## Licence

Ce projet est publié sous licence **MIT**.

© 2025, projet éducatif “Ask CielNet”.
Fait avec curiosité, café et supervision humaine.
