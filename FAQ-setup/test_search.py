#!/usr/bin/env python3
"""
Script de test de recherche dans l'index OpenSearch
"""

from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer
from config import (
    OPENSEARCH_HOST,
    OPENSEARCH_PORT,
    INDEX_NAME,
    INDEX_NAME_SEMANTIC,
    INDEX_NAME_PIPELINE,
    EMBEDDING_MODEL,
    ML_MODEL_ID
)


def create_opensearch_client():
    """Crée et retourne un client OpenSearch"""
    client = OpenSearch(
        hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
        http_compress=True,
        use_ssl=False,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
    )
    return client


def search_faq(client, query_text):
    """Effectue une recherche textuelle dans la FAQ"""
    query = {
        "query": {
            "multi_match": {
                "query": query_text,
                "fields": ["question^2", "answer", "tags^1.5"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        "size": 5,
        "_source": ["id", "section", "question", "answer", "tags", "confidence"]
    }

    response = client.search(index=INDEX_NAME, body=query)
    return response


def search_faq_semantic(client, query_text, model):
    """Effectue une recherche sémantique KNN dans la FAQ (embeddings manuels)"""
    # Génération de l'embedding de la requête
    query_embedding = model.encode(query_text).tolist()

    # Recherche KNN sur les embeddings de questions
    query = {
        "size": 5,
        "_source": ["id", "section", "question", "answer", "tags", "confidence"],
        "query": {
            "knn": {
                "question_embedding": {
                    "vector": query_embedding,
                    "k": 5
                }
            }
        }
    }

    response = client.search(index=INDEX_NAME_SEMANTIC, body=query)
    return response


def search_faq_neural(client, query_text, model_id):
    """Effectue une recherche sémantique avec neural search (pipeline OpenSearch)"""
    # Recherche neural sur les embeddings générés par OpenSearch
    query = {
        "size": 5,
        "_source": ["id", "section", "question", "answer", "tags", "confidence"],
        "query": {
            "neural": {
                "question_embedding": {
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
        print(f"ID: {source['id']}")
        print(f"Section: {source['section']}")
        print(f"Question: {source['question']}")
        print(f"Réponse: {source['answer'][:200]}{'...' if len(source['answer']) > 200 else ''}")
        print(f"Tags: {', '.join(source['tags'])}")
        print(f"Confiance: {source['confidence']}")
        print()


def main():
    """Fonction principale"""
    print("=" * 70)
    print("=== Test de recherche dans la FAQ CielNet ===")
    print("=" * 70)

    # Connexion à OpenSearch
    print("\nConnexion à OpenSearch...")
    client = create_opensearch_client()

    # Vérification de la connexion
    info = client.info()
    print(f"Connecté à OpenSearch version {info['version']['number']}")

    query_text = "Documentation pour l'utilisation d'api externe"

    # ===== Recherche textuelle =====
    print("\n" + "=" * 70)
    print("RECHERCHE TEXTUELLE (BM25)")
    print("=" * 70)

    response_text = search_faq(client, query_text)
    display_results(response_text, query_text, search_type="textuelle")

    # ===== Recherche sémantique (embeddings manuels) =====
    print("\n" + "=" * 70)
    print("RECHERCHE SÉMANTIQUE (KNN avec embeddings manuels)")
    print("=" * 70)

    print("\nChargement du modèle d'embedding...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"Modèle chargé : {EMBEDDING_MODEL}")

    response_semantic = search_faq_semantic(client, query_text, model)
    display_results(response_semantic, query_text, search_type="sémantique (manuel)")

    # ===== Recherche neural (pipeline OpenSearch) =====
    if ML_MODEL_ID:
        print("\n" + "=" * 70)
        print("RECHERCHE NEURAL (avec pipeline OpenSearch)")
        print("=" * 70)

        print(f"\nUtilisation du modèle ML: {ML_MODEL_ID}")

        response_neural = search_faq_neural(client, query_text, ML_MODEL_ID)
        display_results(response_neural, query_text, search_type="neural (pipeline)")
    else:
        print("\n" + "=" * 70)
        print("RECHERCHE NEURAL IGNORÉE")
        print("=" * 70)
        print("ML_MODEL_ID non configuré dans config.py\n")

    print("=" * 70)
    print("=== Recherches terminées ===")
    print("=" * 70)


if __name__ == "__main__":
    main()
