#!/usr/bin/env python3
"""
Script de benchmark pour tester les différentes combinaisons RAG
"""

import sys
import csv
import json
import time
import shutil
import subprocess
import threading
import queue
from pathlib import Path
from datetime import datetime
import psutil

# Ajouter le dossier Client au path pour importer les modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "Client"))

# Importer les modules de recherche
import faq_search
import pls_search
import rag_assistant
from sentence_transformers import SentenceTransformer
from ollama_client import OllamaClient


class ResourceMonitor:
    """Monitore l'utilisation CPU, RAM et GPU avec macmon sur Apple Silicon"""

    def __init__(self, use_macmon=True):
        self.use_macmon = use_macmon
        self.monitoring = False
        self.monitor_thread = None
        self.reader_thread = None
        self.macmon_proc = None
        self.data_queue = queue.Queue()
        self.cpu_samples = []
        self.ram_samples = []
        self.gpu_samples = []

    def _read_macmon_output(self):
        """Thread séparé pour lire la sortie macmon de manière non-bloquante"""
        try:
            for line in self.macmon_proc.stdout:
                self.data_queue.put(line)
        except Exception:
            pass

    def start(self):
        """Démarre le monitoring avec macmon ou psutil"""
        self.monitoring = True
        self.cpu_samples = []
        self.ram_samples = []
        self.gpu_samples = []

        # Démarrer macmon seulement si demandé
        if self.use_macmon and shutil.which("macmon"):
            try:
                self.macmon_proc = subprocess.Popen(
                    ["macmon", "pipe", "-i", "100"],  # 100ms interval (plus rapide)
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,  # Line buffered
                )
                # Thread dédié pour lire macmon (non-bloquant)
                self.reader_thread = threading.Thread(target=self._read_macmon_output, daemon=True)
                self.reader_thread.start()
                # Attendre un peu que macmon démarre
                time.sleep(0.2)
            except Exception:
                self.macmon_proc = None

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        """Arrête le monitoring et retourne les statistiques"""
        # Si on utilise macmon, attendre pour capturer des données
        if self.use_macmon and self.macmon_proc:
            time.sleep(0.5)

        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)

        if self.macmon_proc:
            self.macmon_proc.terminate()
            try:
                self.macmon_proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.macmon_proc.kill()

        stats = {
            'cpu_avg': None,
            'cpu_max': None,
            'ram_avg': None,
            'ram_max': None,
            'gpu_avg': None,
            'gpu_max': None
        }

        if self.cpu_samples:
            stats['cpu_avg'] = sum(self.cpu_samples) / len(self.cpu_samples)
            stats['cpu_max'] = max(self.cpu_samples)

        if self.ram_samples:
            stats['ram_avg'] = sum(self.ram_samples) / len(self.ram_samples)
            stats['ram_max'] = max(self.ram_samples)

        if self.gpu_samples:
            stats['gpu_avg'] = sum(self.gpu_samples) / len(self.gpu_samples)
            stats['gpu_max'] = max(self.gpu_samples)

        return stats

    def _parse_percent(self, value):
        """Convertir les valeurs macmon en pourcentage"""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value * 100.0) if value <= 1 else float(value)
        return None

    def _monitor_loop(self):
        """Boucle de monitoring (s'exécute dans un thread séparé)"""
        if self.macmon_proc:
            while self.monitoring:
                try:
                    # Essayer de lire depuis la queue avec timeout
                    line = self.data_queue.get(timeout=0.1)

                    data = json.loads(line)

                    # CPU - format: [freq_mhz, usage_ratio]
                    cpu_source = data.get("pcpu_usage")
                    if cpu_source and isinstance(cpu_source, list) and len(cpu_source) >= 2:
                        cpu_ratio = cpu_source[1]
                        if isinstance(cpu_ratio, (int, float)):
                            cpu_pct = float(cpu_ratio * 100.0)
                            self.cpu_samples.append(cpu_pct)

                    # RAM - format: {"ram_usage": bytes, "ram_total": bytes}
                    mem_source = data.get("memory")
                    if mem_source and isinstance(mem_source, dict):
                        ram_usage = mem_source.get("ram_usage")
                        ram_total = mem_source.get("ram_total")
                        if ram_usage is not None and ram_total and ram_total > 0:
                            ram_pct = (ram_usage / ram_total) * 100.0
                            self.ram_samples.append(ram_pct)

                    # GPU - format: [freq_mhz, usage_ratio]
                    gpu_source = data.get("gpu_usage")
                    if gpu_source and isinstance(gpu_source, list) and len(gpu_source) >= 2:
                        gpu_ratio = gpu_source[1]
                        if isinstance(gpu_ratio, (int, float)):
                            gpu_pct = float(gpu_ratio * 100.0)
                            self.gpu_samples.append(gpu_pct)

                except queue.Empty:
                    # Pas de données dans la queue, continuer
                    continue
                except json.JSONDecodeError:
                    continue
        else:
            # Fallback: utiliser psutil uniquement
            while self.monitoring:
                try:
                    cpu_percent = psutil.cpu_percent(interval=0.5)
                    self.cpu_samples.append(cpu_percent)

                    ram = psutil.virtual_memory()
                    self.ram_samples.append(ram.percent)

                    time.sleep(0.5)
                except Exception:
                    pass


def load_questions(filepath, limit=None):
    """
    Charge les questions depuis un fichier texte

    Args:
        filepath: Chemin du fichier contenant les questions
        limit: Nombre maximum de questions à charger (None = toutes)

    Returns:
        Liste de questions
    """
    questions = []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            # Vérifier la limite
            if limit is not None and len(questions) >= limit:
                break

            line = line.strip()

            # Ignorer les lignes vides et les commentaires
            if not line or line.startswith('#'):
                continue

            # Enlever le numéro au début (format: "1. **Titre:** Question")
            if '.' in line:
                parts = line.split('.', 1)
                if parts[0].strip().isdigit():
                    question = parts[1].strip()
                    # Enlever les astérisques
                    question = question.replace('**', '').replace('*', '')
                    questions.append(question)
                else:
                    questions.append(line)
            else:
                questions.append(line)

    return questions


def benchmark_search(opensearch_client, question, corpus, search_mode):
    """
    Effectue une recherche et mesure le temps de réponse

    Args:
        opensearch_client: Client OpenSearch
        question: La question à rechercher
        corpus: 'faq' ou 'pls'
        search_mode: 'keyword', 'semantic', 'neural', 'hybrid'

    Returns:
        dict: Résultats avec temps de réponse
    """
    # Démarrer le monitoring des ressources (psutil uniquement, plus rapide)
    monitor = ResourceMonitor(use_macmon=False)
    monitor.start()

    # Démarrer le chronomètre
    start_time = time.time()
    start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = {
        'question': question,
        'corpus': corpus,
        'search_mode': search_mode,
        'llm_model': '',
        'multiquery': '',
        'start_time': start_datetime,
        'end_time': None,
        'response_time': None,
        'num_results': 0,
        'cpu_avg': None,
        'cpu_max': None,
        'ram_avg': None,
        'ram_max': None,
        'gpu_avg': None,
        'gpu_max': None,
        'error': None
    }

    try:

        # Effectuer la recherche selon le corpus et le mode
        if corpus == 'faq':
            if search_mode == 'keyword':
                index_name = faq_search.FAQ_INDEX_NAME
                response = faq_search.search_faq_by_keyword(
                    opensearch_client,
                    index_name,
                    question,
                    size=5
                )
            elif search_mode == 'semantic':
                # Charger le modèle pour la recherche sémantique
                model = SentenceTransformer(faq_search.EMBEDDING_MODEL)
                response = faq_search.search_faq_semantic(
                    opensearch_client,
                    model,
                    question,
                    size=5
                )
            elif search_mode == 'neural':
                response = faq_search.search_faq_neural(
                    opensearch_client,
                    faq_search.ML_MODEL_ID,
                    question,
                    size=5
                )
            elif search_mode == 'hybrid':
                response = faq_search.search_faq_hybrid(
                    opensearch_client,
                    faq_search.ML_MODEL_ID,
                    question,
                    size=5
                )
            else:
                raise ValueError(f"Mode de recherche inconnu: {search_mode}")
        elif corpus == 'pls':
            if search_mode == 'keyword':
                index_name = pls_search.PLS_INDEX_NAME
                response = pls_search.search_pls_by_keyword(
                    opensearch_client,
                    index_name,
                    question,
                    size=5
                )
            elif search_mode == 'semantic':
                # Charger le modèle pour la recherche sémantique
                model = SentenceTransformer(pls_search.EMBEDDING_MODEL)
                response = pls_search.search_pls_semantic(
                    opensearch_client,
                    model,
                    question,
                    size=5
                )
            elif search_mode == 'neural':
                response = pls_search.search_pls_neural(
                    opensearch_client,
                    pls_search.ML_MODEL_ID,
                    question,
                    size=5
                )
            elif search_mode == 'hybrid':
                response = pls_search.search_pls_hybrid(
                    opensearch_client,
                    pls_search.ML_MODEL_ID,
                    question,
                    size=5
                )
            else:
                raise ValueError(f"Mode de recherche inconnu: {search_mode}")
        else:
            raise NotImplementedError(f"Corpus {corpus} non implémenté")

        # Mesurer le temps
        result['response_time'] = time.time() - start_time

        # Récupérer les résultats
        hits = response["hits"]["hits"]
        result['num_results'] = len(hits)

    except Exception as e:
        result['error'] = str(e)

    # Arrêter le monitoring et récupérer les statistiques
    stats = monitor.stop()
    result.update(stats)

    # Enregistrer l'heure de fin
    result['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return result


def benchmark_rag(opensearch_client, ollama_client, question, corpus, search_mode, llm_model, multiquery_enabled):
    """
    Effectue un benchmark RAG complet (recherche + génération)

    Args:
        opensearch_client: Client OpenSearch
        ollama_client: Client Ollama
        question: La question à poser
        corpus: 'faq' ou 'pls'
        search_mode: 'keyword', 'semantic', 'neural', 'hybrid'
        llm_model: Nom du modèle LLM à utiliser
        multiquery_enabled: True pour activer le multi-query

    Returns:
        dict: Résultats avec temps de réponse
    """
    # Démarrer le monitoring des ressources
    monitor = ResourceMonitor()
    monitor.start()

    # Démarrer le chronomètre global
    start_time = time.time()
    start_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    result = {
        'question': question,
        'corpus': corpus,
        'search_mode': search_mode,
        'llm_model': llm_model,
        'multiquery': multiquery_enabled,
        'start_time': start_datetime,
        'end_time': None,
        'response_time': None,
        'search_time': None,
        'generation_time': None,
        'num_results': 0,
        'cpu_avg': None,
        'cpu_max': None,
        'ram_avg': None,
        'ram_max': None,
        'gpu_avg': None,
        'gpu_max': None,
        'error': None
    }

    try:

        # Charger le modèle d'embedding si nécessaire
        embedding_model = None
        if search_mode == 'semantic':
            embedding_model = SentenceTransformer(faq_search.EMBEDDING_MODEL)

        # Configurer le modèle LLM
        ollama_client.model = llm_model

        # Temps de recherche
        search_start = time.time()

        if multiquery_enabled:
            # Mode Multi-Query: générer 3 questions et chercher 2 résultats par question
            alternative_questions = rag_assistant.generate_alternative_questions(ollama_client, question)

            # Chercher avec chaque question (2 résultats par question)
            all_hits = []
            for alt_question in alternative_questions:
                response = rag_assistant.perform_search(
                    opensearch_client,
                    embedding_model,
                    corpus,
                    search_mode,
                    alt_question,
                    num_results=2
                )
                hits = response["hits"]["hits"]
                all_hits.extend(hits)

            result['num_results'] = len(all_hits)

            # Formater le contexte à partir de tous les résultats
            context_parts = []
            for i, hit in enumerate(all_hits, 1):
                source = hit["_source"]
                score = hit["_score"]

                if corpus == 'faq':
                    context_parts.append(
                        f"[Document {i} - Pertinence: {score:.2f}]\n"
                        f"Question: {source['question']}\n"
                        f"Réponse: {source['answer']}\n"
                    )
                else:
                    title = source.get('title', '')
                    title_str = f"Titre: {title}\n" if title else ""
                    context_parts.append(
                        f"[Document {i} - Pertinence: {score:.2f}]\n"
                        f"Source: {source['filename']} (Page {source['page']})\n"
                        f"{title_str}"
                        f"Contenu: {source['text']}\n"
                    )

            context = "\n".join(context_parts) if context_parts else "Aucun résultat trouvé."

        else:
            # Mode simple: recherche classique
            response = rag_assistant.perform_search(
                opensearch_client,
                embedding_model,
                corpus,
                search_mode,
                question,
                num_results=5
            )

            hits = response["hits"]["hits"]
            result['num_results'] = len(hits)

            # Formater le contexte
            if corpus == 'faq':
                context = rag_assistant.format_faq_results_as_context(response)
            else:
                context = rag_assistant.format_pls_results_as_context(response)

        result['search_time'] = time.time() - search_start

        # Temps de génération
        generation_start = time.time()

        # Générer la réponse avec le LLM (sans streaming et sans affichage pour le benchmark)
        llm_response = rag_assistant.generate_rag_answer(ollama_client, question, context, stream=False, display=False)
        result['llm_response'] = llm_response

        result['generation_time'] = time.time() - generation_start

        # Mesurer le temps total
        result['response_time'] = time.time() - start_time

    except Exception as e:
        result['error'] = str(e)

    # Arrêter le monitoring et récupérer les statistiques
    stats = monitor.stop()
    result.update(stats)

    # Enregistrer l'heure de fin
    result['end_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return result


def save_results_to_csv(results, output_file):
    """
    Sauvegarde les résultats dans un fichier CSV

    Args:
        results: Liste de dictionnaires de résultats
        output_file: Chemin du fichier CSV
    """
    if not results:
        print("Aucun résultat à sauvegarder")
        return

    fieldnames = ['question', 'corpus', 'search_mode', 'llm_model', 'multiquery',
                  'start_time', 'end_time', 'response_time', 'num_results',
                  'cpu_avg', 'cpu_max', 'ram_avg', 'ram_max', 'gpu_avg', 'gpu_max',
                  'error']

    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(results)

    print(f"✓ Résultats sauvegardés dans: {output_file}")


def main():
    """Fonction principale"""
    print("=" * 70)
    print("=== Benchmark RAG ===")
    print("=" * 70)

    # Connexion à OpenSearch
    print("\n[1/2] Connexion à OpenSearch...")
    try:
        opensearch_client = faq_search.create_opensearch_client()
        info = opensearch_client.info()
        print(f"✓ Connecté à OpenSearch version {info['version']['number']}")
    except Exception as e:
        print(f"✗ Erreur de connexion : {e}")
        return

    # Dossier contenant les questions
    benchmark_dir = Path(__file__).parent

    # Limite de questions à charger (pour les tests rapides)
    QUESTION_LIMIT = 30

    # Charger les questions FAQ
    print("\n[2/2] Chargement des questions...")
    faq_file = benchmark_dir / "faq_question.txt"
    faq_questions = []

    if faq_file.exists():
        faq_questions = load_questions(faq_file, limit=QUESTION_LIMIT)
        print(f"✓ {len(faq_questions)} questions FAQ chargées (limite: {QUESTION_LIMIT})")

        # Afficher les premières questions
        print("\nExemples de questions FAQ:")
        for i, q in enumerate(faq_questions[:3], 1):
            print(f"  {i}. {q[:80]}...")
    else:
        print("⚠️  Fichier faq_question.txt non trouvé")

    # Charger les questions Pour La Science
    pls_file = benchmark_dir / "pls_question.txt"
    pls_questions = []

    if pls_file.exists():
        pls_questions = load_questions(pls_file, limit=QUESTION_LIMIT)
        print(f"✓ {len(pls_questions)} questions Pour La Science chargées (limite: {QUESTION_LIMIT})")

        # Afficher les premières questions
        print("\nExemples de questions PLS:")
        for i, q in enumerate(pls_questions[:3], 1):
            print(f"  {i}. {q[:80]}...")
    else:
        print("⚠️  Fichier pls_question.txt non trouvé")

    # Modes de recherche à tester
    search_modes = ['keyword', 'semantic', 'neural', 'hybrid']

    # Créer le dossier resultats s'il n'existe pas
    results_dir = benchmark_dir / "resultats"
    results_dir.mkdir(exist_ok=True)
    print(f"\n✓ Dossier de résultats: {results_dir}")

    # Exécuter le benchmark pour chaque mode de recherche
    for search_mode in search_modes:
        # Benchmark FAQ pour ce mode
        if faq_questions:
            print("\n" + "=" * 70)
            print(f"Benchmark FAQ - Mode {search_mode.upper()}")
            print("=" * 70)

            results = []
            total = len(faq_questions)

            for i, question in enumerate(faq_questions, 1):
                print(f"\n[{i}/{total}] Question: {question[:60]}...")

                result = benchmark_search(
                    opensearch_client,
                    question,
                    corpus='faq',
                    search_mode=search_mode
                )

                results.append(result)

                if result['error']:
                    print(f"  ✗ Erreur: {result['error']}")
                else:
                    print(f"  ✓ Temps: {result['response_time']:.3f}s | Résultats: {result['num_results']}")

            # Sauvegarder les résultats
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = results_dir / f"benchmark_faq_{search_mode}_{timestamp}.csv"
            save_results_to_csv(results, output_file)

            # Statistiques
            successful_results = [r for r in results if r['error'] is None]
            if successful_results:
                avg_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
                print(f"\n📊 Statistiques:")
                print(f"  - Questions traitées: {len(successful_results)}/{total}")
                print(f"  - Temps moyen: {avg_time:.3f}s")

            print(f"\n⏸️  Pause de 5 minutes avant la prochaine étape...")
            time.sleep(600)

        # Benchmark PLS pour ce mode
        if pls_questions:
            print("\n" + "=" * 70)
            print(f"Benchmark PLS - Mode {search_mode.upper()}")
            print("=" * 70)

            results = []
            total = len(pls_questions)

            for i, question in enumerate(pls_questions, 1):
                print(f"\n[{i}/{total}] Question: {question[:60]}...")

                result = benchmark_search(
                    opensearch_client,
                    question,
                    corpus='pls',
                    search_mode=search_mode
                )

                results.append(result)

                if result['error']:
                    print(f"  ✗ Erreur: {result['error']}")
                else:
                    print(f"  ✓ Temps: {result['response_time']:.3f}s | Résultats: {result['num_results']}")

            # Sauvegarder les résultats
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = results_dir / f"benchmark_pls_{search_mode}_{timestamp}.csv"
            save_results_to_csv(results, output_file)

            # Statistiques
            successful_results = [r for r in results if r['error'] is None]
            if successful_results:
                avg_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
                print(f"\n📊 Statistiques:")
                print(f"  - Questions traitées: {len(successful_results)}/{total}")
                print(f"  - Temps moyen: {avg_time:.3f}s")

            print(f"\n⏸️  Pause de 5 minutes avant la prochaine étape...")
            time.sleep(600)

    # Résumé
    print("\n" + "=" * 70)
    print(f"Total: {len(faq_questions) + len(pls_questions)} questions chargées")
    print("=" * 70)

    # ========================================================================
    # PARTIE RAG - Benchmark avec LLM
    # ========================================================================

    print("\n" + "=" * 70)
    print("=== Benchmark RAG (Recherche + Génération) ===")
    print("=" * 70)

    # Connexion à Ollama
    print("\nConnexion à Ollama...")
    ollama_client = OllamaClient()

    if not ollama_client.check_connection():
        print("⚠️  Impossible de se connecter à Ollama - Benchmark RAG ignoré")
        print("💡 Assurez-vous qu'Ollama est lancé : ollama serve")
    else:
        print("✓ Connecté à Ollama")

        # Modèles LLM à tester
        llm_models = ['gpt-oss:20b', 'llama3.2']

        # Modes multi-query à tester
        multiquery_modes = [False, True]

        # Exécuter le benchmark RAG pour chaque combinaison
        for search_mode in search_modes:
            for llm_model in llm_models:
                for multiquery_enabled in multiquery_modes:
                    multiquery_str = "multi-query" if multiquery_enabled else "simple"

                    # Benchmark RAG FAQ pour cette combinaison
                    if faq_questions:
                        print("\n" + "=" * 70)
                        print(f"Benchmark RAG FAQ - {search_mode.upper()} + {llm_model} ({multiquery_str})")
                        print("=" * 70)

                        results = []
                        total = len(faq_questions)

                        for i, question in enumerate(faq_questions, 1):
                            print(f"\n[{i}/{total}] Question: {question[:60]}...")

                            result = benchmark_rag(
                                opensearch_client,
                                ollama_client,
                                question,
                                corpus='faq',
                                search_mode=search_mode,
                                llm_model=llm_model,
                                multiquery_enabled=multiquery_enabled
                            )

                            results.append(result)

                            if result['error']:
                                print(f"  ✗ Erreur: {result['error']}")
                            else:
                                print(f"  ✓ Temps: {result['response_time']:.3f}s | Résultats: {result['num_results']}")
                                # Afficher les 100 premiers caractères de la réponse
                                if 'llm_response' in result and result['llm_response']:
                                    response_preview = result['llm_response'][:100].replace('\n', ' ')
                                    print(f"  📝 Réponse: {response_preview}...")

                        # Sauvegarder les résultats
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"benchmark_rag_faq_{search_mode}_{llm_model}_{multiquery_str}_{timestamp}.csv"
                        output_file = results_dir / filename
                        save_results_to_csv(results, output_file)

                        # Statistiques
                        successful_results = [r for r in results if r['error'] is None]
                        if successful_results:
                            avg_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
                            print(f"\n📊 Statistiques:")
                            print(f"  - Questions traitées: {len(successful_results)}/{total}")
                            print(f"  - Temps moyen: {avg_time:.3f}s")

                        print(f"\n⏸️  Pause de 5 minutes avant la prochaine étape...")
                        time.sleep(600)

                    # Benchmark RAG PLS pour cette combinaison
                    if pls_questions:
                        print("\n" + "=" * 70)
                        print(f"Benchmark RAG PLS - {search_mode.upper()} + {llm_model} ({multiquery_str})")
                        print("=" * 70)

                        results = []
                        total = len(pls_questions)

                        for i, question in enumerate(pls_questions, 1):
                            print(f"\n[{i}/{total}] Question: {question[:60]}...")

                            result = benchmark_rag(
                                opensearch_client,
                                ollama_client,
                                question,
                                corpus='pour_la_science',
                                search_mode=search_mode,
                                llm_model=llm_model,
                                multiquery_enabled=multiquery_enabled
                            )

                            results.append(result)

                            if result['error']:
                                print(f"  ✗ Erreur: {result['error']}")
                            else:
                                print(f"  ✓ Temps: {result['response_time']:.3f}s | Résultats: {result['num_results']}")
                                # Afficher les 100 premiers caractères de la réponse
                                if 'llm_response' in result and result['llm_response']:
                                    response_preview = result['llm_response'][:100].replace('\n', ' ')
                                    print(f"  📝 Réponse: {response_preview}...")

                        # Sauvegarder les résultats
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"benchmark_rag_pls_{search_mode}_{llm_model}_{multiquery_str}_{timestamp}.csv"
                        output_file = results_dir / filename
                        save_results_to_csv(results, output_file)

                        # Statistiques
                        successful_results = [r for r in results if r['error'] is None]
                        if successful_results:
                            avg_time = sum(r['response_time'] for r in successful_results) / len(successful_results)
                            print(f"\n📊 Statistiques:")
                            print(f"  - Questions traitées: {len(successful_results)}/{total}")
                            print(f"  - Temps moyen: {avg_time:.3f}s")

                        # Pause de 3 minutes avant la prochaine étape (sauf si c'est la dernière)
                        is_last = (search_mode == search_modes[-1] and
                                   llm_model == llm_models[-1] and
                                   multiquery_enabled == multiquery_modes[-1])
                        if not is_last:
                            print(f"\n⏸️  Pause de 5 minutes avant la prochaine étape...")
                            time.sleep(600)

    print("\n" + "=" * 70)
    print("=== Benchmark terminé ===")
    print("=" * 70)


if __name__ == "__main__":
    main()
