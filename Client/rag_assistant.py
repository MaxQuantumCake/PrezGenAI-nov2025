#!/usr/bin/env python3
"""
Assistant RAG - Combine recherche OpenSearch et génération avec Ollama
Utilise les modules faq_search, pls_search et ollama_client
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# Ajouter le dossier Client au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

# Importer les modules de recherche
import faq_search
import pls_search
from ollama_client import OllamaClient

# Charger les variables d'environnement
PROJECT_ROOT = Path(__file__).parent.parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(env_path)

# Configuration
EMBEDDING_MODEL = os.environ['EMBEDDING_MODEL']
ML_MODEL_ID = os.environ.get('MODEL_ID', '')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')


# ============================================================================
# FORMATAGE DES RÉSULTATS
# ============================================================================

def format_faq_results_as_context(response):
    """Formate les résultats FAQ en contexte pour le LLM"""
    hits = response["hits"]["hits"]

    if not hits:
        return "Aucun résultat trouvé dans la FAQ."

    context_parts = []
    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        score = hit["_score"]

        context_parts.append(
            f"[Document {i} - Pertinence: {score:.2f}]\n"
            f"Question: {source['question']}\n"
            f"Réponse: {source['answer']}\n"
        )

    return "\n".join(context_parts)


def format_pls_results_as_context(response):
    """Formate les résultats Pour La Science en contexte pour le LLM"""
    hits = response["hits"]["hits"]

    if not hits:
        return "Aucun résultat trouvé dans Pour La Science."

    context_parts = []
    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        score = hit["_score"]

        title = source.get('title', '')
        title_str = f"Titre: {title}\n" if title else ""

        context_parts.append(
            f"[Document {i} - Pertinence: {score:.2f}]\n"
            f"Source: {source['filename']} (Page {source['page']})\n"
            f"{title_str}"
            f"Contenu: {source['text']}\n"
        )

    return "\n".join(context_parts)


def display_faq_results(response):
    """Affiche les résultats FAQ de manière lisible"""
    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]

    print(f"\n{'=' * 70}")
    print(f"📚 Résultats FAQ : {total} documents trouvés")
    print(f"{'=' * 70}\n")

    if not hits:
        print("Aucun résultat trouvé.")
        return

    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        score = hit["_score"]

        print(f"--- Document {i} (score: {score:.4f}) ---")
        print(f"Q: {source['question']}")
        answer = source['answer']
        if len(answer) > 150:
            answer = answer[:150] + "..."
        print(f"R: {answer}")
        if source.get('tags'):
            print(f"Tags: {', '.join(source['tags'])}")
        print()


def display_pls_results(response):
    """Affiche les résultats Pour La Science de manière lisible"""
    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]

    print(f"\n{'=' * 70}")
    print(f"📰 Résultats Pour La Science : {total} documents trouvés")
    print(f"{'=' * 70}\n")

    if not hits:
        print("Aucun résultat trouvé.")
        return

    for i, hit in enumerate(hits, 1):
        source = hit["_source"]
        score = hit["_score"]

        print(f"--- Document {i} (score: {score:.4f}) ---")
        print(f"Fichier: {source['filename']} - Page {source['page']}")

        if source.get('title'):
            print(f"Titre: {source['title']}")

        text = source['text']
        if len(text) > 150:
            text = text[:150] + "..."
        print(f"Texte: {text}")
        print()


# ============================================================================
# INTERFACE UTILISATEUR
# ============================================================================

def select_corpus():
    """Sélection du corpus de recherche"""
    print("\nChoisissez le corpus de recherche :")
    print("-" * 70)
    print("1. FAQ CielNet")
    print("2. Pour La Science")
    print("-" * 70)

    while True:
        choice = input("\nVotre choix (1-2) : ").strip()
        if choice == '1':
            print("✓ Corpus sélectionné : FAQ CielNet")
            return 'faq'
        elif choice == '2':
            print("✓ Corpus sélectionné : Pour La Science")
            return 'pour_la_science'
        else:
            print("Choix invalide. Veuillez entrer 1 ou 2.")


def select_search_mode():
    """Sélection du mode de recherche"""
    print("\nChoisissez le mode de recherche :")
    print("-" * 70)
    print("1. Mot-clé (BM25)")
    print("2. Sémantique (KNN avec embeddings)")
    print("3. Neural (embeddings OpenSearch)")
    print("4. Hybride (BM25 + Neural)")
    print("-" * 70)

    while True:
        choice = input("\nVotre choix (1-4) : ").strip()
        if choice == '1':
            print("✓ Mode : Recherche par mot-clé")
            return 'keyword'
        elif choice == '2':
            print("✓ Mode : Recherche sémantique")
            return 'semantic'
        elif choice == '3':
            if not ML_MODEL_ID:
                print("⚠️  MODEL_ID non configuré - Mode mot-clé utilisé par défaut")
                return 'keyword'
            print("✓ Mode : Recherche neural")
            return 'neural'
        elif choice == '4':
            if not ML_MODEL_ID:
                print("⚠️  MODEL_ID non configuré - Mode mot-clé utilisé par défaut")
                return 'keyword'
            print("✓ Mode : Recherche hybride")
            return 'hybrid'
        else:
            print("Choix invalide. Veuillez entrer 1, 2, 3 ou 4.")


def select_llm_model(ollama_client):
    """Sélection du modèle LLM"""
    models = ollama_client.list_models()

    if not models:
        print("⚠️  Aucun modèle Ollama trouvé, utilisation du modèle par défaut")
        return ollama_client.model

    model_names = [m.get('name') for m in models]

    print("\nModèles Ollama disponibles :")
    print("-" * 70)

    for i, model_name in enumerate(model_names, 1):
        marker = " (actuel)" if model_name == ollama_client.model else ""
        print(f"{i}. {model_name}{marker}")

    print("-" * 70)

    while True:
        choice = input(f"\nVotre choix (1-{len(model_names)}) ou Entrée pour garder actuel : ").strip()

        if not choice:
            print(f"✓ Modèle sélectionné : {ollama_client.model}")
            return ollama_client.model

        if choice.isdigit() and 1 <= int(choice) <= len(model_names):
            selected = model_names[int(choice) - 1]
            print(f"✓ Modèle sélectionné : {selected}")
            return selected
        else:
            print(f"Choix invalide. Veuillez entrer un nombre entre 1 et {len(model_names)}.")


def perform_search(opensearch_client, embedding_model, corpus_type, search_mode, question, num_results=5):
    """Effectue la recherche selon le corpus et le mode sélectionnés"""

    if corpus_type == 'faq':
        # Déterminer l'index
        if search_mode in ['neural', 'hybrid']:
            index_name = faq_search.FAQ_INDEX_NAME_PIPELINE
        elif search_mode == 'semantic':
            index_name = faq_search.FAQ_INDEX_NAME_SEMANTIC
        else:
            index_name = faq_search.FAQ_INDEX_NAME

        # Effectuer la recherche
        if search_mode == 'keyword':
            return faq_search.search_faq_by_keyword(opensearch_client, index_name, question, num_results)
        elif search_mode == 'semantic':
            return faq_search.search_faq_semantic(opensearch_client, embedding_model, question, num_results)
        elif search_mode == 'neural':
            return faq_search.search_faq_neural(opensearch_client, ML_MODEL_ID, question, num_results)
        elif search_mode == 'hybrid':
            return faq_search.search_faq_hybrid(opensearch_client, ML_MODEL_ID, question, num_results)

    else:  # pour_la_science
        # Déterminer l'index
        if search_mode in ['neural', 'hybrid']:
            index_name = pls_search.PLS_INDEX_NAME_PIPELINE
        elif search_mode == 'semantic':
            index_name = pls_search.PLS_INDEX_NAME_SEMANTIC
        else:
            index_name = pls_search.PLS_INDEX_NAME

        # Effectuer la recherche
        if search_mode == 'keyword':
            return pls_search.search_pls_by_keyword(opensearch_client, index_name, question, num_results)
        elif search_mode == 'semantic':
            return pls_search.search_pls_semantic(opensearch_client, embedding_model, question, num_results)
        elif search_mode == 'neural':
            return pls_search.search_pls_neural(opensearch_client, ML_MODEL_ID, question, num_results)
        elif search_mode == 'hybrid':
            return pls_search.search_pls_hybrid(opensearch_client, ML_MODEL_ID, question, num_results)


def generate_rag_answer(ollama_client, question, context):
    """Génère une réponse RAG avec Ollama"""
    prompt = f"""Tu es un assistant qui répond aux questions en te basant UNIQUEMENT sur le contexte fourni.

CONTEXTE DOCUMENTAIRE:
{context}

QUESTION: {question}

INSTRUCTIONS:
- Réponds à la question en te basant uniquement sur le contexte fourni
- Si le contexte ne contient pas d'information pertinente pour répondre, dis-le clairement
- Sois précis, concis et factuel
- Cite les sources quand c'est pertinent (numéro de document, page, etc.)

RÉPONSE:"""

    print(f"\n{'=' * 70}")
    print(f"🤖 Réponse de {ollama_client.model} :")
    print(f"{'=' * 70}\n")

    full_response = ""
    for chunk in ollama_client.generate(prompt, stream=True):
        print(chunk, end='', flush=True)
        full_response += chunk

    print("\n")
    return full_response


# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def main():
    """Fonction principale"""
    print("=" * 70)
    print("=== 🚀 Assistant RAG - Recherche Augmentée par Génération ===")
    print("=" * 70)

    # [1/4] Connexion à OpenSearch
    print("\n[1/4] Connexion à OpenSearch...")
    try:
        opensearch_client = faq_search.create_opensearch_client()
        info = opensearch_client.info()
        print(f"✓ Connecté à OpenSearch version {info['version']['number']}")
    except Exception as e:
        print(f"✗ Erreur de connexion à OpenSearch : {e}")
        return

    # [2/4] Connexion à Ollama
    print("\n[2/4] Connexion à Ollama...")
    ollama_client = OllamaClient()

    if not ollama_client.check_connection():
        print("✗ Impossible de se connecter à Ollama")
        print("💡 Assurez-vous qu'Ollama est lancé : ollama serve")
        return

    print(f"✓ Connecté à Ollama")

    # [3/4] Configuration
    print("\n[3/4] Configuration")
    corpus_type = select_corpus()
    search_mode = select_search_mode()
    llm_model = select_llm_model(ollama_client)
    ollama_client.model = llm_model

    # Charger le modèle d'embedding si nécessaire
    embedding_model = None
    if search_mode == 'semantic':
        print(f"\n⏳ Chargement du modèle d'embedding {EMBEDDING_MODEL}...")
        try:
            embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            print("✓ Modèle d'embedding chargé")
        except Exception as e:
            print(f"✗ Erreur lors du chargement : {e}")
            return

    # [4/4] Interface de questions-réponses
    print("\n[4/4] Assistant RAG prêt")
    print("\n" + "=" * 70)
    print("💬 Posez vos questions !")
    print("\nCommandes disponibles :")
    print("  - Tapez votre question pour obtenir une réponse")
    print("  - '/config' pour changer la configuration")
    print("  - '/exit' pour quitter")
    print("-" * 70)

    while True:
        question = input("\n❓ Question > ").strip()

        if not question:
            continue

        if question.lower() in ['/exit', '/quit', '/q']:
            print("\n👋 Au revoir!")
            break

        if question.lower() == '/config':
            print("\n" + "=" * 70)
            print("Reconfiguration")
            print("=" * 70)

            corpus_type = select_corpus()
            search_mode = select_search_mode()
            llm_model = select_llm_model(ollama_client)
            ollama_client.model = llm_model

            # Recharger l'embedding model si nécessaire
            if search_mode == 'semantic' and embedding_model is None:
                print(f"\n⏳ Chargement du modèle d'embedding {EMBEDDING_MODEL}...")
                try:
                    embedding_model = SentenceTransformer(EMBEDDING_MODEL)
                    print("✓ Modèle d'embedding chargé")
                except Exception as e:
                    print(f"✗ Erreur : {e}")
                    search_mode = 'keyword'
                    print("⚠️  Retour au mode mot-clé")

            continue

        # Effectuer la recherche
        print(f"\n🔍 Recherche en cours ({search_mode})...")

        try:
            response = perform_search(
                opensearch_client,
                embedding_model,
                corpus_type,
                search_mode,
                question
            )

            # Afficher les résultats de recherche
            if corpus_type == 'faq':
                display_faq_results(response)
                context = format_faq_results_as_context(response)
            else:
                display_pls_results(response)
                context = format_pls_results_as_context(response)

            # Générer la réponse avec le LLM
            generate_rag_answer(ollama_client, question, context)

        except Exception as e:
            print(f"\n✗ Erreur : {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()