#!/usr/bin/env python3
"""
Script d'importation de Pour La Science dans OpenSearch
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv
from opensearchpy import OpenSearch, helpers
from sentence_transformers import SentenceTransformer
from extract_text import extract_text_from_folder
from clean_text_pagewise import process_folder

# Charger les variables d'environnement depuis .env à la racine du projet
PROJECT_ROOT = Path(__file__).parent.parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(env_path)

# Configuration depuis .env
OPENSEARCH_URL = os.environ['OPENSEARCH_URL']
INDEX_NAME = os.environ['PLS_INDEX_NAME']
INDEX_NAME_SEMANTIC = os.environ['PLS_INDEX_NAME_SEMANTIC']
INDEX_NAME_PIPELINE = os.environ['PLS_INDEX_NAME_PIPELINE']
PIPELINE_NAME = os.environ['PLS_PIPELINE_NAME']
EMBEDDING_MODEL = os.environ['EMBEDDING_MODEL']
ML_MODEL_ID = os.environ['MODEL_ID']

PLS_FOLDER = PROJECT_ROOT / "PourLaScienceFiles"
PLS_TXT_FOLDER = PROJECT_ROOT / "PourLaScienceText"
PLS_CLEAN_FOLDER = PROJECT_ROOT / "PourLaScienceClean"


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


def create_index_if_not_exists(client):
    """Crée l'index standard (le supprime s'il existe déjà)"""
    if client.indices.exists(index=INDEX_NAME):
        print(f"Suppression de l'index existant '{INDEX_NAME}'...")
        client.indices.delete(index=INDEX_NAME)

    # Définition du mapping pour l'index
    mapping = {
        "mappings": {
            "properties": {
                "text": { "type": "text", "analyzer": "standard" },
                "filename": { "type": "keyword" },
                "page": { "type": "integer" },
                "line_in_page": { "type": "integer" },
                "title": { "type": "text", "analyzer": "standard" }
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
                "text": { "type": "text", "analyzer": "standard" },
                "filename": { "type": "keyword" },
                "page": { "type": "integer" },
                "line_in_page": { "type": "integer" },
                "title": { "type": "text", "analyzer": "standard" },
                "text_embedding": {
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
                        "text": "text_embedding"
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
                "text": { "type": "text", "analyzer": "standard" },
                "filename": { "type": "keyword" },
                "page": { "type": "integer" },
                "line_in_page": { "type": "integer" },
                "title": { "type": "text", "analyzer": "standard" },
                "text_embedding": {
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


def load_pls_data(file: str):
    """Charge les données d'un fichier PLS"""
    clean_filename = file.name.replace('.clean.txt', '')
    file_lines = []
    with open(file, "r", encoding="utf-8") as f:
        current_page = 1
        line_in_page = 0
        pending_title = None

        for line in f:
            cleaned_line = line.strip()

            if not cleaned_line:
                continue

            # Vérifier si c'est une ligne de tag de page
            page_match = re.match(r'=== PAGE (\d+) ===', cleaned_line)
            if page_match:
                current_page = int(page_match.group(1))
                line_in_page = 0
                # Réinitialiser le titre en attente lors d'un changement de page
                pending_title = None
                continue

            # À partir de la page 4, vérifier si c'est un titre (ligne en majuscules)
            # On vérifie que la ligne contient au moins une lettre et que toutes les lettres sont en majuscules
            has_letters = any(c.isalpha() for c in cleaned_line)
            is_all_uppercase = all(c.isupper() or not c.isalpha() for c in cleaned_line)

            if current_page >= 4 and has_letters and is_all_uppercase:
                # Cette ligne est un titre, on la garde pour la ligne suivante
                pending_title = cleaned_line
                continue

            # Si c'est une ligne de texte normale
            line_in_page += 1
            line_data = {
                'text': cleaned_line,
                'filename': clean_filename,
                'page': current_page,
                'line_in_page': line_in_page,
                'title': pending_title
            }
            file_lines.append(line_data)

            # Réinitialiser le titre en attente après utilisation
            pending_title = None
    return file_lines


def generate_bulk_actions(entries, index_name):
    """Génère les actions bulk pour l'import standard"""
    for entry in entries:
        source = {
            "text": entry["text"],
            "filename": entry["filename"],
            "page": entry["page"],
            "line_in_page": entry["line_in_page"],
        }
        # Ajouter le titre seulement s'il existe
        if entry.get("title"):
            source["title"] = entry["title"]

        yield {
            "_index": index_name,
            "_source": source,
        }


def generate_bulk_actions_with_embeddings(entries, model, index_name):
    """Génère les actions bulk pour l'import avec embeddings"""
    print("Génération des embeddings...")
    for i, entry in enumerate(entries):
        # if (i + 1) % 10 == 0:
        #     print(f"  Traitement de l'entrée {i + 1}/{len(entries)}...")

        # Génération des embeddings
        text_embedding = model.encode(entry["text"]).tolist()

        source = {
            "text": entry["text"],
            "filename": entry["filename"],
            "page": entry["page"],
            "line_in_page": entry["line_in_page"],
            "text_embedding": text_embedding
        }
        # Ajouter le titre seulement s'il existe
        if entry.get("title"):
            source["title"] = entry["title"]

        yield {
            "_index": index_name,
            "_source": source,
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


def import_folder(dir):
    """Fonction principale"""
    print("=== Import de Pour La Science dans OpenSearch ===\n")

    pls_folder = PROJECT_ROOT / dir

    # Connexion à OpenSearch
    print("Connexion à OpenSearch...")
    client = create_opensearch_client()

    # Vérification de la connexion
    info = client.info()
    print(f"Connecté à OpenSearch version {info['version']['number']}\n")

    # Chargement des données
    print(f"Chargement des données depuis {pls_folder}...")
    pdfs = sorted(p for p in pls_folder.iterdir())
    print(f"{len(pdfs)} cleaned pdf trouvées\n")

    # ===== Import dans l'index standard =====
    print("=" * 60)
    print("IMPORT STANDARD (sans embeddings)")
    print("=" * 60)

    create_index_if_not_exists(client)
    print("\nImport des données en cours...")

    for clean_pdf in pdfs:
        entries = load_pls_data(clean_pdf)
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

    for clean_pdf in pdfs:
        entries = load_pls_data(clean_pdf)
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

            for clean_pdf in pdfs:
                entries = load_pls_data(clean_pdf)
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
        print("MODEL_ID non configuré dans .env")

    print("=" * 60)
    print("=== Import terminé avec succès ===")
    print("=" * 60)


def main():
    extract_text_from_folder(PLS_FOLDER, PLS_TXT_FOLDER)
    process_folder(PLS_TXT_FOLDER, PLS_CLEAN_FOLDER)
    import_folder(PLS_CLEAN_FOLDER)

if __name__ == "__main__":
    main()
