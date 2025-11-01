#!/usr/bin/env python3
"""
Script de recherche dans les index Pour La Science
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer

# Charger les variables d'environnement depuis .env à la racine du projet
PROJECT_ROOT = Path(__file__).parent.parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(env_path)

# Configuration depuis .env
OPENSEARCH_URL = os.environ['OPENSEARCH_URL']
PLS_INDEX_NAME = os.environ['PLS_INDEX_NAME']
PLS_INDEX_NAME_SEMANTIC = os.environ['PLS_INDEX_NAME_SEMANTIC']
PLS_INDEX_NAME_PIPELINE = os.environ['PLS_INDEX_NAME_PIPELINE']
EMBEDDING_MODEL = os.environ['EMBEDDING_MODEL']
ML_MODEL_ID = os.environ.get('MODEL_ID', '')

# Dictionnaire des index disponibles
PLS_INDEXES = {
    '1': {'name': PLS_INDEX_NAME, 'description': 'Index simple (BM25)'},
    '2': {'name': PLS_INDEX_NAME_SEMANTIC, 'description': 'Index sémantique (embeddings manuels)'},
    '3': {'name': PLS_INDEX_NAME_PIPELINE, 'description': 'Index avec pipeline OpenSearch'}
}


def create_opensearch_client():
    """Crée et retourne un client OpenSearch"""
    client = OpenSearch(
        hosts=[OPENSEARCH_URL],
        http_compress=True,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
    return client


def search_pls_by_keyword(client, index_name, query_text, size=5):
    """
    Effectue une recherche par mot-clé dans Pour La Science

    Args:
        client: Client OpenSearch
        index_name: Nom de l'index dans lequel rechercher
        query_text: Texte de la requête
        size: Nombre de résultats à retourner (défaut: 5)

    Returns:
        Response OpenSearch avec les résultats
    """
    query = {
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["text^2", "title^3", "filename"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        "size": size,
        "sort": [
            {"_score": {"order": "desc"}},
            {"page": {"order": "asc"}},
            {"line_in_page": {"order": "asc"}}
        ],
        "_source": ["page", "line_in_page", "text", "filename", "title"],
        "highlight": {
            "fields": {
                "text": {},
                "title": {}
            }
        }
    }

    response = client.search(index=index_name, body=query)
    return response


def search_pls_semantic(client, model, query_text, size=5):
    """
    Effectue une recherche sémantique dans Pour La Science en calculant les embeddings
    ATTENTION: Cette fonction ne fonctionne qu'avec l'index sémantique (embeddings manuels)

    Args:
        client: Client OpenSearch
        model: Modèle SentenceTransformer pour générer les embeddings
        query_text: Texte de la requête
        size: Nombre de résultats à retourner (défaut: 5)

    Returns:
        Response OpenSearch avec les résultats
    """
    # Générer l'embedding de la requête
    query_embedding = model.encode(query_text).tolist()

    # Recherche KNN
    query = {
        "size": size,
        "_source": ["page", "line_in_page", "text", "filename", "title"],
        "query": {
            "knn": {
                "text_embedding": {
                    "vector": query_embedding,
                    "k": size
                }
            }
        }
    }

    response = client.search(index=PLS_INDEX_NAME_SEMANTIC, body=query)
    return response


def search_pls_neural(client, model_id, query_text, size=5):
    """
    Effectue une recherche sémantique avec neural search (pipeline OpenSearch)
    ATTENTION: Cette fonction ne fonctionne qu'avec l'index avec pipeline
    OpenSearch calcule automatiquement les embeddings

    Args:
        client: Client OpenSearch
        model_id: ID du modèle ML déployé dans OpenSearch
        query_text: Texte de la requête
        size: Nombre de résultats à retourner (défaut: 5)

    Returns:
        Response OpenSearch avec les résultats
    """
    # Recherche neural - OpenSearch calcule l'embedding automatiquement
    query = {
        "size": size,
        "_source": ["page", "line_in_page", "text", "filename", "title"],
        "query": {
            "neural": {
                "text_embedding": {
                    "query_text": query_text,
                    "model_id": model_id,
                    "k": size
                }
            }
        }
    }

    response = client.search(index=PLS_INDEX_NAME_PIPELINE, body=query)
    return response


def search_pls_hybrid(client, model_id, query_text, size=5):
    """
    Effectue une recherche hybride combinant BM25 et neural search
    ATTENTION: Cette fonction ne fonctionne qu'avec l'index avec pipeline
    Combine les avantages de la recherche lexicale et sémantique

    Args:
        client: Client OpenSearch
        model_id: ID du modèle ML déployé dans OpenSearch
        query_text: Texte de la requête
        size: Nombre de résultats à retourner (défaut: 5)

    Returns:
        Response OpenSearch avec les résultats
    """
    # Recherche hybride : combinaison de BM25 et neural search
    query = {
        "size": size,
        "_source": ["page", "line_in_page", "text", "filename", "title"],
        "query": {
            "hybrid": {
                "queries": [
                    {
                        "multi_match": {
                            "query": query_text,
                            "fields": ["text^2", "title^3", "filename"],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    {
                        "neural": {
                            "text_embedding": {
                                "query_text": query_text,
                                "model_id": model_id,
                                "k": size
                            }
                        }
                    }
                ]
            }
        }
    }

    response = client.search(index=PLS_INDEX_NAME_PIPELINE, body=query)
    return response


def select_index():
    """
    Permet à l'utilisateur de choisir l'index de recherche

    Returns:
        Tuple (index_name, index_description)
    """
    print("\nChoisissez l'index de recherche :")
    print("-" * 70)
    for key, index_info in PLS_INDEXES.items():
        print(f"{key}. {index_info['description']}")
    print("-" * 70)

    while True:
        choice = input("\nVotre choix (1-3) : ").strip()
        if choice in PLS_INDEXES:
            selected = PLS_INDEXES[choice]
            print(f"✓ Index sélectionné : {selected['description']}")
            return selected['name'], selected['description']
        else:
            print("Choix invalide. Veuillez entrer 1, 2 ou 3.")


def display_results(response):
    """
    Affiche les résultats de recherche de manière formatée

    Args:
        response: Réponse OpenSearch
    """
    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]

    print(f"\nNombre de résultats : {total}\n")

    if not hits:
        print("Aucun résultat trouvé.")
        return

    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        score = hit["_score"]

        print(f"{'=' * 70}")
        print(f"Résultat {i} (score: {score:.4f})")
        print(f"{'=' * 70}")
        print(f"Fichier: {source['filename']}")
        print(f"Page: {source['page']}, Ligne: {source['line_in_page']}")

        # Afficher le titre s'il existe
        if source.get('title'):
            # Afficher le titre avec surbrillance si disponible
            if 'highlight' in hit and 'title' in hit['highlight']:
                highlighted_title = ' '.join(hit['highlight']['title'])
                print(f"Titre: {highlighted_title}")
            else:
                print(f"Titre: {source['title']}")

        # Afficher le texte avec surbrillance si disponible
        if 'highlight' in hit and 'text' in hit['highlight']:
            highlighted_text = ' '.join(hit['highlight']['text'])
            print(f"Texte: {highlighted_text}")
        else:
            text = source['text']
            if len(text) > 200:
                text = text[:200] + "..."
            print(f"Texte: {text}")

        print()


def select_search_mode(index_name):
    """
    Permet à l'utilisateur de choisir le mode de recherche

    Args:
        index_name: Nom de l'index sélectionné

    Returns:
        Mode de recherche ('keyword', 'semantic', 'neural' ou 'hybrid')
    """
    # Pour l'index simple, seul le mot-clé est disponible
    if index_name == PLS_INDEX_NAME:
        return 'keyword'

    # Pour l'index sémantique (embeddings manuels)
    if index_name == PLS_INDEX_NAME_SEMANTIC:
        print("\nChoisissez le mode de recherche :")
        print("-" * 70)
        print("1. Recherche par mot-clé (BM25)")
        print("2. Recherche sémantique (KNN avec embeddings manuels)")
        print("-" * 70)

        while True:
            choice = input("\nVotre choix (1-2) : ").strip()
            if choice == '1':
                print("✓ Mode : Recherche par mot-clé")
                return 'keyword'
            elif choice == '2':
                print("✓ Mode : Recherche sémantique (KNN)")
                return 'semantic'
            else:
                print("Choix invalide. Veuillez entrer 1 ou 2.")

    # Pour l'index avec pipeline
    if index_name == PLS_INDEX_NAME_PIPELINE:
        print("\nChoisissez le mode de recherche :")
        print("-" * 70)
        print("1. Recherche par mot-clé (BM25)")
        print("2. Recherche neural (embeddings calculés par OpenSearch)")
        print("3. Recherche hybride (BM25 + Neural combinés)")
        print("-" * 70)

        while True:
            choice = input("\nVotre choix (1-3) : ").strip()
            if choice == '1':
                print("✓ Mode : Recherche par mot-clé")
                return 'keyword'
            elif choice == '2':
                if not ML_MODEL_ID:
                    print("✗ MODEL_ID non configuré dans .env - Mode mot-clé utilisé par défaut")
                    return 'keyword'
                print("✓ Mode : Recherche neural")
                return 'neural'
            elif choice == '3':
                if not ML_MODEL_ID:
                    print("✗ MODEL_ID non configuré dans .env - Mode mot-clé utilisé par défaut")
                    return 'keyword'
                print("✓ Mode : Recherche hybride")
                return 'hybrid'
            else:
                print("Choix invalide. Veuillez entrer 1, 2 ou 3.")

    return 'keyword'


def main():
    """Fonction principale"""
    print("=" * 70)
    print("=== Recherche dans Pour La Science ===")
    print("=" * 70)

    # Connexion à OpenSearch
    print("\nConnexion à OpenSearch...")
    try:
        client = create_opensearch_client()
        info = client.info()
        print(f"✓ Connecté à OpenSearch version {info['version']['number']}")
    except Exception as e:
        print(f"✗ Erreur de connexion : {e}")
        return

    # Sélection de l'index
    index_name, index_description = select_index()

    # Sélection du mode de recherche
    search_mode = select_search_mode(index_name)

    # Charger le modèle d'embedding si nécessaire
    model = None
    if search_mode == 'semantic':
        print(f"\nChargement du modèle d'embedding...")
        try:
            model = SentenceTransformer(EMBEDDING_MODEL)
            print(f"✓ Modèle chargé : {EMBEDDING_MODEL}")
        except Exception as e:
            print(f"✗ Erreur lors du chargement du modèle : {e}")
            return

    # Interface de recherche interactive
    mode_map = {
        'keyword': 'Mot-clé',
        'semantic': 'Sémantique (KNN)',
        'neural': 'Neural (OpenSearch)',
        'hybrid': 'Hybride (BM25 + Neural)'
    }
    mode_str = mode_map.get(search_mode, 'Mot-clé')

    print(f"\nCommandes disponibles :")
    print("  - Tapez votre requête pour rechercher")
    print("  - 'change' pour changer d'index/mode")
    print("  - 'exit' pour quitter")
    print("-" * 70)

    while True:
        query_text = input(f"\n[{index_description} - {mode_str}] Recherche > ").strip()

        if query_text.lower() in ['exit', 'quit', 'q']:
            print("\nAu revoir!")
            break

        if query_text.lower() == 'change':
            index_name, index_description = select_index()
            search_mode = select_search_mode(index_name)
            mode_str = mode_map.get(search_mode, 'Mot-clé')

            # Recharger le modèle si on passe en mode sémantique
            if search_mode == 'semantic' and model is None:
                print(f"\nChargement du modèle d'embedding...")
                try:
                    model = SentenceTransformer(EMBEDDING_MODEL)
                    print(f"✓ Modèle chargé : {EMBEDDING_MODEL}")
                except Exception as e:
                    print(f"✗ Erreur lors du chargement du modèle : {e}")
                    search_mode = 'keyword'
                    mode_str = mode_map.get(search_mode, 'Mot-clé')
            continue

        if not query_text:
            print("Veuillez entrer une requête valide.")
            continue

        try:
            if search_mode == 'semantic':
                response = search_pls_semantic(client, model, query_text)
            elif search_mode == 'neural':
                response = search_pls_neural(client, ML_MODEL_ID, query_text)
            elif search_mode == 'hybrid':
                response = search_pls_hybrid(client, ML_MODEL_ID, query_text)
            else:
                response = search_pls_by_keyword(client, index_name, query_text)
            display_results(response)
        except Exception as e:
            print(f"Erreur lors de la recherche : {e}")


if __name__ == "__main__":
    main()
