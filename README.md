# PrezGenAI - Projet de Génération et Interrogation de FAQ avec IA

Un système complet pour générer, enrichir et interroger des FAQ en utilisant les modèles d'IA locaux (Ollama) et la recherche sémantique (OpenSearch).

## Table des matières

- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
  - [Import de la FAQ CielNet](#import-de-la-faq-cielnet)
  - [Import de Pour La Science](#import-de-pour-la-science)
  - [Assistant RAG Interactif](#assistant-rag-interactif)
  - [Benchmark et Évaluation](#benchmark-et-évaluation)

## Prérequis

Avant de commencer, assurez-vous d'avoir installé les éléments suivants :

### 1. Python 3
- **Version requise** : Python 3.8 ou supérieur

### 2. Docker et Docker Compose
- **Docker** : Pour exécuter les services en conteneurs
- **Docker Compose** : Pour orchestrer les services (OpenSearch, SQLite Browser)

### 3. Ollama
- **Ollama** : Runtime pour exécuter les modèles LLM localement

## Installation

### Étape 1 : Cloner le projet

```bash
git clone <repository-url>
cd PrezGenAI-nov2025
```

### Étape 2 : Créer un environnement virtuel Python

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows
```

### Étape 3 : Installer les dépendances

```bash
pip3 install -r requirements.txt
```
**Dépendances principales** :
- `langchain` et `langchain-community` : Framework LLM
- `langchain-ollama` et `langchain-chroma` : Intégration avec Ollama et Chroma
- `opensearch-py` : Client Python pour OpenSearch
- `sentence-transformers` : Modèles d'embedding
- `chromadb` : Vector store local
- `pymupdf` : Extraction de PDF
- `requests` : Client HTTP
- `psutil` : Monitoring des ressources

### Étape 4 : Configurer le fichier .env

Copier le fichier `.env.example` en `.env` :

```bash
cp .env.example .env
```

Ajuster les valeurs selon votre environnement. Variables importantes :
- `OLLAMA_URL` : URL du serveur Ollama (défaut: `http://localhost:11434`)
- `OLLAMA_MODEL` : Modèle à utiliser (défaut: `llama3.2`)
- `OPENSEARCH_URL` : URL du serveur OpenSearch (défaut: `http://localhost:9200`)
- `EMBEDDING_MODEL` : Modèle d'embedding pour les vecteurs

### Étape 5 : Configurer et démarrer OpenSearch

Accédez au dossier OpenSearch :

```bash
cd Opensearch
```

Démarrez les conteneurs OpenSearch :

```bash
docker-compose up -d
```

Attendez que les conteneurs soient complètement démarrés (environ 30 secondes), puis exécutez le script de configuration :

```bash
python3 config_opensearch.py
```

Ce script initialise les index OpenSearch et les pipelines d'embedding nécessaires au projet.

Retournez au répertoire racine :

```bash
cd ..
```

### Étape 6 : Télécharger les modèles Ollama

Avant de démarrer Ollama, téléchargez les modèles requis :

```bash
ollama pull llama3.2
ollama pull gpt-oss:20b
```

Ces modèles seront utilisés par le projet pour la génération de texte et les embeddings.

### Étape 7 : Démarrer Ollama

```bash
ollama serve
```

Cette commande démarre le serveur Ollama. Laissez-le en arrière-plan dans un terminal séparé.

## Configuration

### Configuration OpenSearch

(À compléter selon votre setup OpenSearch)

### Configuration FAQ

Le projet supporte plusieurs sources de FAQ :
- **CielNet FAQ** : Index OpenSearch pour les FAQ CielNet
- **Pour La Science** : Index OpenSearch pour les articles Pour La Science

### Configuration Ollama

Assurez-vous que Ollama est en cours d'exécution et accessible sur `http://localhost:11434`.

Pour modifier le modèle utilisé, mettez à jour la variable `OLLAMA_MODEL` dans le fichier `.env`.

## Utilisation

### Import de la FAQ CielNet

Une fois que tous les services sont démarrés et configurés, vous pouvez importer les données de la FAQ CielNet dans OpenSearch.

Exécutez le script d'importation :

```bash
python3 FAQ-setup/import_faq.py
```

Ce script va :
1. Créer les index OpenSearch nécessaires (standard, sémantique, et avec pipeline)
2. Charger les données de la FAQ depuis le fichier `FAQ-CielNet/data/cielnet_faq.json`
3. Générer les embeddings pour la recherche sémantique
4. Importer tous les documents dans les différents index

Une fois l'import terminé, les données sont prêtes à être interrogées via le système RAG du projet.

### Import de Pour La Science

Cette source optionnelle permet d'enrichir le système avec des articles de la revue Pour La Science.

**Prérequis** :
- Avoir acheté une licence sur [pourlascience.fr](https://www.pourlascience.fr/)
- Télécharger les fichiers PDF depuis le site officiel

**Étapes d'importation** :

1. Créez le dossier `PourLaScienceFiles` s'il n'existe pas :
   ```bash
   mkdir -p PourLaScienceFiles
   ```

2. Placez vos fichiers PDF téléchargés dans ce dossier :
   ```bash
   cp /chemin/vers/vos/pdfs/*.pdf PourLaScienceFiles/
   ```

3. Exécutez le script d'importation :
   ```bash
   python3 PourLaScience-setup/import_science.py
   ```

Ce script va :
1. Extraire le texte des fichiers PDF
2. Nettoyer et structurer le texte (page par page)
3. Créer les index OpenSearch nécessaires
4. Générer les embeddings pour la recherche sémantique
5. Importer tous les documents dans les différents index

Une fois l'import terminé, les articles sont prêts à être interrogés via le système RAG du projet.

### Assistant RAG Interactif

Une fois les données importées, vous pouvez utiliser l'assistant RAG interactif pour poser des questions :

```bash
python3 Client/rag_assistant.py
```

**Configuration initiale** :
Le script va demander de sélectionner :
1. **Corpus** : FAQ CielNet ou Pour La Science
2. **Mode de recherche** :
   - Mot-clé (BM25) : Recherche basée sur les mots-clés
   - Sémantique (KNN) : Recherche basée sur la similarité sémantique
   - Neural : Recherche avec embeddings OpenSearch (nécessite MODEL_ID configuré)
   - Hybride : Combinaison de BM25 et Neural
3. **Modèle LLM** : Sélection parmi les modèles Ollama disponibles
4. **Mode Multi-Query** : Activation de la génération de questions alternatives pour enrichir la recherche

**Commandes disponibles** :
```
- Posez votre question pour obtenir une réponse RAG
- '/config' pour reconfigurer les paramètres
- '/exit' pour quitter
```

### Benchmark et Évaluation

Pour exécuter un benchmark complet avec des mesures de performance :

```bash
python3 Benchmark/run_benchmark.py
```

**Ce que fait le script** :
1. Charge les questions de test depuis :
   - `Benchmark/faq_question.txt` (questions FAQ)
   - `Benchmark/pls_question.txt` (questions Pour La Science)
2. Teste tous les modes de recherche (keyword, semantic, neural, hybrid)
3. Mesure pour chaque mode :
   - Temps de réponse
   - Utilisation CPU/RAM/GPU
   - Nombre de résultats
4. Teste le benchmark RAG complet avec :
   - Différentes combinaisons de modes de recherche et modèles LLM
   - Recherche simple vs multi-query
5. Génère des fichiers CSV avec les résultats dans `Benchmark/resultats/`

**Résultats produits** :
- `benchmark_faq_[mode]_[timestamp].csv` : Benchmark de recherche FAQ
- `benchmark_pls_[mode]_[timestamp].csv` : Benchmark de recherche PLS
- `benchmark_rag_faq_[mode]_[model]_[type]_[timestamp].csv` : Benchmark RAG FAQ
- `benchmark_rag_pls_[mode]_[model]_[type]_[timestamp].csv` : Benchmark RAG PLS

**Note** : Le benchmark est long (plusieurs heures) car il inclut des pauses entre les tests pour stabiliser les mesures.
