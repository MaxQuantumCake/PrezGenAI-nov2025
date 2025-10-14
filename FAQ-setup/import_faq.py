#!/usr/bin/env python3
"""
Script d'importation de la FAQ CielNet dans OpenSearch
"""

import json
from pathlib import Path
from opensearchpy import OpenSearch, helpers
from sentence_transformers import SentenceTransformer
from config import (
    OPENSEARCH_HOST,
    OPENSEARCH_PORT,
    INDEX_NAME,
    INDEX_NAME_SEMANTIC,
    INDEX_NAME_PIPELINE,
    PIPELINE_NAME,
    EMBEDDING_MODEL,
    ML_MODEL_ID
)

# Chemin vers le fichier JSON (relatif à la racine du projet)
PROJECT_ROOT = Path(__file__).parent.parent
FAQ_FILE = PROJECT_ROOT / "FAQ-CielNet" / "data" / "cielnet_faq.json"


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


def create_index_if_not_exists(client):
    """Crée l'index standard (le supprime s'il existe déjà)"""
    if client.indices.exists(index=INDEX_NAME):
        print(f"Suppression de l'index existant '{INDEX_NAME}'...")
        client.indices.delete(index=INDEX_NAME)

    # Définition du mapping pour l'index
    mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "section": {"type": "keyword"},
                "question": {"type": "text", "analyzer": "french"},
                "answer": {"type": "text", "analyzer": "french"},
                "confidence": {"type": "keyword"},
                "tags": {"type": "keyword"},
            }
        }
    }
    client.indices.create(index=INDEX_NAME, body=mapping)
    print(f"Index '{INDEX_NAME}' créé avec succès")


def create_semantic_index_if_not_exists(client, embedding_dim):
    """Crée l'index sémantique avec support KNN (le supprime s'il existe déjà)"""
    if client.indices.exists(index=INDEX_NAME_SEMANTIC):
        print(f"Suppression de l'index existant '{INDEX_NAME_SEMANTIC}'...")
        client.indices.delete(index=INDEX_NAME_SEMANTIC)

    # Définition du mapping pour l'index avec embeddings
    mapping = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "section": {"type": "keyword"},
                "question": {"type": "text", "analyzer": "french"},
                "answer": {"type": "text", "analyzer": "french"},
                "confidence": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "question_embedding": {
                    "type": "knn_vector",
                    "dimension": embedding_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene"
                    }
                },
                "answer_embedding": {
                    "type": "knn_vector",
                    "dimension": embedding_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene"
                    }
                }
            }
        }
    }
    client.indices.create(index=INDEX_NAME_SEMANTIC, body=mapping)
    print(f"Index '{INDEX_NAME_SEMANTIC}' créé avec succès")


def create_ingest_pipeline(client, model_id):
    """Crée le pipeline d'ingestion avec génération automatique d'embeddings"""
    pipeline_body = {
        "description": "Pipeline pour générer automatiquement les embeddings",
        "processors": [
            {
                "text_embedding": {
                    "model_id": model_id,
                    "field_map": {
                        "question": "question_embedding",
                        "answer": "answer_embedding"
                    }
                }
            }
        ]
    }

    try:
        client.ingest.put_pipeline(id=PIPELINE_NAME, body=pipeline_body)
        print(f"Pipeline '{PIPELINE_NAME}' créé avec succès")
        return True
    except Exception as e:
        print(f"Erreur lors de la création du pipeline: {e}")
        return False


def get_ml_model_dimension(client, model_id):
    """Récupère la dimension d'embedding du modèle ML déployé"""
    try:
        response = client.transport.perform_request(
            "GET",
            f"/_plugins/_ml/models/{model_id}"
        )
        dimension = response.get("model_config", {}).get("embedding_dimension")
        if dimension:
            print(f"Dimension du modèle ML: {dimension}")
            return dimension
        else:
            print("Impossible de récupérer la dimension du modèle ML, utilisation de 768 par défaut")
            return 768
    except Exception as e:
        print(f"Erreur lors de la récupération du modèle: {e}")
        print("Utilisation de 768 par défaut")
        return 768


def create_pipeline_index_if_not_exists(client, embedding_dim):
    """Crée l'index avec pipeline d'ingestion (le supprime s'il existe déjà)"""
    if client.indices.exists(index=INDEX_NAME_PIPELINE):
        print(f"Suppression de l'index existant '{INDEX_NAME_PIPELINE}'...")
        client.indices.delete(index=INDEX_NAME_PIPELINE)

    # Définition du mapping pour l'index avec pipeline
    mapping = {
        "settings": {
            "index": {
                "knn": True,
                "knn.algo_param.ef_search": 100,
                "default_pipeline": PIPELINE_NAME
            }
        },
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "section": {"type": "keyword"},
                "question": {"type": "text", "analyzer": "french"},
                "answer": {"type": "text", "analyzer": "french"},
                "confidence": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "question_embedding": {
                    "type": "knn_vector",
                    "dimension": embedding_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene"
                    }
                },
                "answer_embedding": {
                    "type": "knn_vector",
                    "dimension": embedding_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "lucene"
                    }
                }
            }
        }
    }
    client.indices.create(index=INDEX_NAME_PIPELINE, body=mapping)
    print(f"Index '{INDEX_NAME_PIPELINE}' créé avec succès")


def load_faq_data():
    """Charge les données de la FAQ depuis le fichier JSON"""
    with open(FAQ_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("entries", [])


def generate_bulk_actions(entries, index_name):
    """Génère les actions bulk pour l'import standard"""
    for entry in entries:
        yield {
            "_index": index_name,
            "_id": entry["id"],
            "_source": {
                "id": entry["id"],
                "section": entry["section"],
                "question": entry["question"],
                "answer": entry["answer"],
                "confidence": entry["confidence"],
                "tags": entry["tags"],
            },
        }


def generate_bulk_actions_with_embeddings(entries, model, index_name):
    """Génère les actions bulk pour l'import avec embeddings"""
    print("Génération des embeddings...")
    for i, entry in enumerate(entries):
        if (i + 1) % 10 == 0:
            print(f"  Traitement de l'entrée {i + 1}/{len(entries)}...")

        # Génération des embeddings
        question_embedding = model.encode(entry["question"]).tolist()
        answer_embedding = model.encode(entry["answer"]).tolist()

        yield {
            "_index": index_name,
            "_id": entry["id"],
            "_source": {
                "id": entry["id"],
                "section": entry["section"],
                "question": entry["question"],
                "answer": entry["answer"],
                "confidence": entry["confidence"],
                "tags": entry["tags"],
                "question_embedding": question_embedding,
                "answer_embedding": answer_embedding,
            },
        }


def import_data(client, entries, index_name):
    """Importe les données dans OpenSearch (sans embeddings)"""
    success, failed = helpers.bulk(client, generate_bulk_actions(entries, index_name))
    print(f"Import terminé : {success} documents importés avec succès")
    if failed:
        print(f"Échecs : {len(failed)}")
    return success, failed


def import_data_with_embeddings(client, entries, model, index_name):
    """Importe les données dans OpenSearch (avec embeddings)"""
    success, failed = helpers.bulk(
        client,
        generate_bulk_actions_with_embeddings(entries, model, index_name),
        chunk_size=50
    )
    print(f"Import terminé : {success} documents importés avec succès")
    if failed:
        print(f"Échecs : {len(failed)}")
    return success, failed


def main():
    """Fonction principale"""
    print("=== Import de la FAQ CielNet dans OpenSearch ===\n")

    # Connexion à OpenSearch
    print("Connexion à OpenSearch...")
    client = create_opensearch_client()

    # Vérification de la connexion
    info = client.info()
    print(f"Connecté à OpenSearch version {info['version']['number']}\n")

    # Chargement des données
    print(f"Chargement des données depuis {FAQ_FILE}...")
    entries = load_faq_data()
    print(f"{len(entries)} entrées trouvées\n")

    # ===== Import dans l'index standard =====
    print("=" * 60)
    print("IMPORT STANDARD (sans embeddings)")
    print("=" * 60)

    create_index_if_not_exists(client)
    print("\nImport des données en cours...")
    import_data(client, entries, INDEX_NAME)

    client.indices.refresh(index=INDEX_NAME)
    count = client.count(index=INDEX_NAME)
    print(f"Nombre total de documents dans l'index '{INDEX_NAME}' : {count['count']}\n")

    # ===== Import dans l'index sémantique =====
    print("=" * 60)
    print("IMPORT SÉMANTIQUE (avec embeddings manuels)")
    print("=" * 60)

    print("\nChargement du modèle d'embedding...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    embedding_dim = model.get_sentence_embedding_dimension()
    print(f"Modèle chargé : {EMBEDDING_MODEL} (dimension: {embedding_dim})\n")

    create_semantic_index_if_not_exists(client, embedding_dim)
    print("\nImport des données avec embeddings en cours...")
    import_data_with_embeddings(client, entries, model, INDEX_NAME_SEMANTIC)

    client.indices.refresh(index=INDEX_NAME_SEMANTIC)
    count = client.count(index=INDEX_NAME_SEMANTIC)
    print(f"Nombre total de documents dans l'index '{INDEX_NAME_SEMANTIC}' : {count['count']}\n")

    # ===== Import dans l'index avec pipeline =====
    if ML_MODEL_ID:
        print("=" * 60)
        print("IMPORT AVEC PIPELINE D'INGESTION")
        print("=" * 60)

        print(f"\nUtilisation du modèle ML: {ML_MODEL_ID}")

        # Récupérer la dimension du modèle ML
        ml_embedding_dim = get_ml_model_dimension(client, ML_MODEL_ID)

        if create_ingest_pipeline(client, ML_MODEL_ID):
            create_pipeline_index_if_not_exists(client, ml_embedding_dim)

            print("\nImport des données (embeddings générés automatiquement)...")
            import_data(client, entries, INDEX_NAME_PIPELINE)

            client.indices.refresh(index=INDEX_NAME_PIPELINE)
            count = client.count(index=INDEX_NAME_PIPELINE)
            print(f"Nombre total de documents dans l'index '{INDEX_NAME_PIPELINE}' : {count['count']}\n")
        else:
            print("Impossible de créer le pipeline.")
    else:
        print("\n" + "=" * 60)
        print("IMPORT AVEC PIPELINE IGNORÉ")
        print("=" * 60)
        print("ML_MODEL_ID non configuré dans config.py")

    print("=" * 60)
    print("=== Import terminé avec succès ===")
    print("=" * 60)


if __name__ == "__main__":
    main()
