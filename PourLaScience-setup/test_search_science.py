#!/usr/bin/env python3
"""
Script de test de recherche dans les index OpenSearch Pour La Science
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
INDEX_NAME = os.environ['PLS_INDEX_NAME']
INDEX_NAME_SEMANTIC = os.environ['PLS_INDEX_NAME_SEMANTIC']
INDEX_NAME_PIPELINE = os.environ['PLS_INDEX_NAME_PIPELINE']
EMBEDDING_MODEL = os.environ['EMBEDDING_MODEL']
ML_MODEL_ID = os.environ.get('MODEL_ID', '')


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


def search_text_standard(client, query_text):
    """Effectue une recherche textuelle standard dans l'index Pour La Science"""
    query = {
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["text^2", "title^3", "filename"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        "size": 5,
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

    response = client.search(index=INDEX_NAME, body=query)
    return response


def search_text_semantic(client, query_text, model):
    """Effectue une recherche sémantique KNN dans l'index (embeddings manuels)"""
    # Génération de l'embedding de la requête
    query_embedding = model.encode(query_text).tolist()

    # Recherche KNN sur les embeddings de texte
    query = {
        "size": 5,
        "_source": ["page", "line_in_page", "text", "filename", "title"],
        "query": {
            "knn": {
                "text_embedding": {
                    "vector": query_embedding,
                    "k": 5
                }
            }
        }
    }

    response = client.search(index=INDEX_NAME_SEMANTIC, body=query)
    return response


def search_text_neural(client, query_text, model_id):
    """Effectue une recherche sémantique avec neural search (pipeline OpenSearch)"""
    # Recherche neural sur les embeddings générés par OpenSearch
    query = {
        "size": 5,
        "_source": ["page", "line_in_page", "text", "filename", "title"],
        "query": {
            "neural": {
                "text_embedding": {
                    "query_text": query_text,
                    "model_id": model_id,
                    "k": 5
                }
            }
        }
    }

    response = client.search(index=INDEX_NAME_PIPELINE, body=query)
    return response


def display_results(response, query_text, search_type="textuelle"):
    """Affiche les résultats de recherche"""
    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]

    print(f"\n=== Recherche {search_type} : '{query_text}' ===\n")
    print(f"Nombre de résultats : {total}\n")

    if not hits:
        print("Aucun résultat trouvé.")
        return

    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        score = hit["_score"]

        print(f"--- Résultat {i} (score: {score:.4f}) ---")
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


def main():
    """Fonction principale"""
    print("=" * 70)
    print("=== Test de recherche dans les index Pour La Science ===")
    print("=" * 70)

    # Connexion à OpenSearch
    print("\nConnexion à OpenSearch...")
    client = create_opensearch_client()

    # Vérification de la connexion
    info = client.info()
    print(f"Connecté à OpenSearch version {info['version']['number']}")

    # Requête de test
    query_text = "climat soleil"

    # ===== Recherche textuelle =====
    print("\n" + "=" * 70)
    print("RECHERCHE TEXTUELLE (BM25)")
    print("=" * 70)

    try:
        response_text = search_text_standard(client, query_text)
        display_results(response_text, query_text, search_type="textuelle")
    except Exception as e:
        print(f"Erreur lors de la recherche textuelle: {e}")

    # ===== Recherche sémantique (embeddings manuels) =====
    print("\n" + "=" * 70)
    print("RECHERCHE SÉMANTIQUE (KNN avec embeddings manuels)")
    print("=" * 70)

    try:
        print("\nChargement du modèle d'embedding...")
        model = SentenceTransformer(EMBEDDING_MODEL)
        print(f"Modèle chargé : {EMBEDDING_MODEL}")

        response_semantic = search_text_semantic(client, query_text, model)
        display_results(response_semantic, query_text, search_type="sémantique (manuel)")
    except Exception as e:
        print(f"Erreur lors de la recherche sémantique: {e}")
        print("Vérifiez que l'index avec embeddings manuels existe et contient le champ 'text_embedding'")

    # ===== Recherche neural (pipeline OpenSearch) =====
    if ML_MODEL_ID:
        print("\n" + "=" * 70)
        print("RECHERCHE NEURAL (avec pipeline OpenSearch)")
        print("=" * 70)

        print(f"\nUtilisation du modèle ML: {ML_MODEL_ID}")

        try:
            response_neural = search_text_neural(client, query_text, ML_MODEL_ID)
            display_results(response_neural, query_text, search_type="neural (pipeline)")
        except Exception as e:
            print(f"Erreur lors de la recherche neural: {e}")
            print("Vérifiez que le pipeline et le modèle ML sont configurés correctement")
    else:
        print("\n" + "=" * 70)
        print("RECHERCHE NEURAL IGNORÉE")
        print("=" * 70)
        print("MODEL_ID non configuré dans .env\n")

    print("=" * 70)
    print("=== Recherches terminées ===")
    print("=" * 70)


if __name__ == "__main__":
    main()