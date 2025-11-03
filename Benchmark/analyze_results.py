#!/usr/bin/env python3
"""
Script d'analyse des résultats de benchmark RAG
Calcule des statistiques sur les temps de réponse
"""

import csv
import pandas as pd
from pathlib import Path
from collections import defaultdict
import statistics


def load_all_results(results_dir):
    """Charge tous les fichiers CSV du dossier résultats"""
    csv_files = list(results_dir.glob("*.csv"))

    if not csv_files:
        print(f"⚠️  Aucun fichier CSV trouvé dans {results_dir}")
        return None

    print(f"\n📂 Chargement de {len(csv_files)} fichiers CSV...")

    # Charger tous les CSV dans un seul DataFrame
    all_data = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            all_data.append(df)
        except Exception as e:
            print(f"⚠️  Erreur lors du chargement de {csv_file.name}: {e}")

    if not all_data:
        return None

    # Concaténer tous les DataFrames
    combined_df = pd.concat(all_data, ignore_index=True)

    # Filtrer les lignes avec erreurs
    errors = combined_df[combined_df['error'].notna()]
    if len(errors) > 0:
        print(f"⚠️  {len(errors)} requêtes avec erreurs (ignorées dans l'analyse)")

    # Ne garder que les résultats valides
    valid_df = combined_df[combined_df['error'].isna()].copy()

    print(f"✓ {len(valid_df)} résultats valides chargés")

    return valid_df


def analyze_by_configuration(df):
    """Analyse les temps moyens par configuration"""

    # Grouper par configuration (corpus, search_mode, llm_model, multiquery)
    grouped = df.groupby(['corpus', 'search_mode', 'llm_model', 'multiquery'], dropna=False)

    results = []
    for (corpus, search_mode, llm_model, multiquery), group in grouped:
        times = group['response_time'].dropna()

        if len(times) == 0:
            continue

        # Convertir llm_model vide en "none"
        llm_display = llm_model if llm_model else "none"
        multiquery_display = str(multiquery) if multiquery != '' else "none"

        # Calculer les stats de ressources
        cpu_avg = group['cpu_avg'].dropna()
        cpu_max = group['cpu_max'].dropna()
        ram_avg = group['ram_avg'].dropna()
        ram_max = group['ram_max'].dropna()
        gpu_avg = group['gpu_avg'].dropna()
        gpu_max = group['gpu_max'].dropna()

        results.append({
            'corpus': corpus,
            'search_mode': search_mode,
            'llm_model': llm_display,
            'multiquery': multiquery_display,
            'count': len(times),
            'mean_time': times.mean(),
            'median_time': times.median(),
            'std_time': times.std(),
            'min_time': times.min(),
            'max_time': times.max(),
            'cpu_avg_mean': cpu_avg.mean() if len(cpu_avg) > 0 else None,
            'cpu_max_mean': cpu_max.mean() if len(cpu_max) > 0 else None,
            'ram_avg_mean': ram_avg.mean() if len(ram_avg) > 0 else None,
            'ram_max_mean': ram_max.mean() if len(ram_max) > 0 else None,
            'gpu_avg_mean': gpu_avg.mean() if len(gpu_avg) > 0 else None,
            'gpu_max_mean': gpu_max.mean() if len(gpu_max) > 0 else None
        })

    return pd.DataFrame(results).sort_values(['corpus', 'search_mode', 'llm_model', 'multiquery'])


def analyze_by_search_mode(df):
    """Analyse les temps moyens par mode de recherche"""
    grouped = df.groupby('search_mode')

    results = []
    for search_mode, group in grouped:
        times = group['response_time'].dropna()

        if len(times) == 0:
            continue

        results.append({
            'search_mode': search_mode,
            'count': len(times),
            'mean_time': times.mean(),
            'median_time': times.median(),
            'std_time': times.std(),
            'min_time': times.min(),
            'max_time': times.max()
        })

    return pd.DataFrame(results).sort_values('search_mode')


def analyze_by_llm_model(df):
    """Analyse les temps moyens par modèle LLM (seulement pour les requêtes RAG)"""
    # Filtrer seulement les requêtes avec LLM
    rag_df = df[df['llm_model'].notna() & (df['llm_model'] != '')].copy()

    if len(rag_df) == 0:
        return None

    grouped = rag_df.groupby('llm_model')

    results = []
    for llm_model, group in grouped:
        times = group['response_time'].dropna()

        if len(times) == 0:
            continue

        results.append({
            'llm_model': llm_model,
            'count': len(times),
            'mean_time': times.mean(),
            'median_time': times.median(),
            'std_time': times.std(),
            'min_time': times.min(),
            'max_time': times.max()
        })

    return pd.DataFrame(results).sort_values('llm_model')


def analyze_by_corpus(df):
    """Analyse les temps moyens par corpus"""
    grouped = df.groupby('corpus')

    results = []
    for corpus, group in grouped:
        times = group['response_time'].dropna()

        if len(times) == 0:
            continue

        results.append({
            'corpus': corpus,
            'count': len(times),
            'mean_time': times.mean(),
            'median_time': times.median(),
            'std_time': times.std(),
            'min_time': times.min(),
            'max_time': times.max()
        })

    return pd.DataFrame(results).sort_values('corpus')


def analyze_multiquery_impact(df):
    """Analyse l'impact du multi-query sur les temps de réponse"""
    # Filtrer seulement les requêtes RAG (avec LLM)
    rag_df = df[df['llm_model'].notna() & (df['llm_model'] != '')].copy()

    if len(rag_df) == 0:
        return None

    grouped = rag_df.groupby(['llm_model', 'search_mode', 'multiquery'], dropna=False)

    results = []
    for (llm_model, search_mode, multiquery), group in grouped:
        times = group['response_time'].dropna()

        if len(times) == 0:
            continue

        multiquery_display = "True" if multiquery == True else "False" if multiquery == False else "none"

        results.append({
            'llm_model': llm_model,
            'search_mode': search_mode,
            'multiquery': multiquery_display,
            'count': len(times),
            'mean_time': times.mean(),
            'median_time': times.median()
        })

    return pd.DataFrame(results).sort_values(['llm_model', 'search_mode', 'multiquery'])


def analyze_resource_usage(df):
    """Analyse l'utilisation des ressources (CPU, RAM, GPU)"""
    # Vérifier si les colonnes de ressources existent
    resource_cols = ['cpu_avg', 'cpu_max', 'ram_avg', 'ram_max', 'gpu_avg', 'gpu_max']
    available_cols = [col for col in resource_cols if col in df.columns]

    if not available_cols:
        return None

    # Grouper par configuration
    grouped = df.groupby(['corpus', 'search_mode', 'llm_model', 'multiquery'], dropna=False)

    results = []
    for (corpus, search_mode, llm_model, multiquery), group in grouped:
        llm_display = llm_model if llm_model else "none"
        multiquery_display = str(multiquery) if multiquery != '' else "none"

        result = {
            'corpus': corpus,
            'search_mode': search_mode,
            'llm_model': llm_display,
            'multiquery': multiquery_display,
            'count': len(group)
        }

        # Ajouter les stats pour chaque ressource disponible
        for col in available_cols:
            values = group[col].dropna()
            if len(values) > 0:
                result[f'{col}_mean'] = values.mean()
                result[f'{col}_max'] = values.max()

        results.append(result)

    return pd.DataFrame(results).sort_values(['corpus', 'search_mode', 'llm_model', 'multiquery'])


def create_markdown_report(df, analysis_dir):
    """Crée un rapport résumé en markdown avec tableaux"""
    report_file = analysis_dir / "summary_report.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("# Rapport d'analyse - Benchmark RAG\n\n")

        # Statistiques générales
        f.write("## 📊 Statistiques générales\n\n")
        f.write("| Métrique | Valeur |\n")
        f.write("|----------|--------|\n")
        f.write(f"| Total de requêtes | {len(df)} |\n")
        f.write(f"| Temps moyen | {df['response_time'].mean():.3f}s |\n")
        f.write(f"| Temps médian | {df['response_time'].median():.3f}s |\n")
        f.write(f"| Écart-type | {df['response_time'].std():.3f}s |\n")
        f.write(f"| Min | {df['response_time'].min():.3f}s |\n")
        f.write(f"| Max | {df['response_time'].max():.3f}s |\n\n")

        # Répartition par corpus
        f.write("## 📚 Répartition par corpus\n\n")
        f.write("| Corpus | Requêtes | Temps moyen |\n")
        f.write("|--------|----------|-------------|\n")
        corpus_counts = df['corpus'].value_counts()
        for corpus in sorted(corpus_counts.index):
            count = corpus_counts[corpus]
            corpus_df = df[df['corpus'] == corpus]
            mean_time = corpus_df['response_time'].mean()
            f.write(f"| {corpus} | {count} | {mean_time:.3f}s |\n")
        f.write("\n")

        # Répartition par mode de recherche
        f.write("## 🔍 Répartition par mode de recherche\n\n")
        f.write("| Mode | Requêtes | Temps moyen |\n")
        f.write("|------|----------|-------------|\n")
        mode_counts = df['search_mode'].value_counts()
        for mode in sorted(mode_counts.index):
            count = mode_counts[mode]
            mode_df = df[df['search_mode'] == mode]
            mean_time = mode_df['response_time'].mean()
            f.write(f"| {mode} | {count} | {mean_time:.3f}s |\n")
        f.write("\n")

        # Répartition par LLM (si applicable)
        rag_df = df[df['llm_model'].notna() & (df['llm_model'] != '')]
        if len(rag_df) > 0:
            f.write("## 🤖 Répartition par modèle LLM\n\n")
            f.write("| Modèle | Requêtes | Temps moyen |\n")
            f.write("|--------|----------|-------------|\n")
            llm_counts = rag_df['llm_model'].value_counts()
            for llm in sorted(llm_counts.index):
                count = llm_counts[llm]
                llm_df = rag_df[rag_df['llm_model'] == llm]
                mean_time = llm_df['response_time'].mean()
                f.write(f"| {llm} | {count} | {mean_time:.3f}s |\n")
            f.write("\n")

        # Top 5 des configurations les plus rapides
        f.write("## ⚡ Top 5 configurations les plus rapides\n\n")
        config_stats = analyze_by_configuration(df)
        top_5_fast = config_stats.nsmallest(5, 'mean_time')
        f.write("| Corpus | Mode | LLM | Multi-query | Temps | N |\n")
        f.write("|--------|------|-----|-------------|-------|---|\n")
        for idx, row in top_5_fast.iterrows():
            f.write(f"| {row['corpus']} | {row['search_mode']} | {row['llm_model']} | "
                   f"{row['multiquery']} | {row['mean_time']:.3f}s | {int(row['count'])} |\n")
        f.write("\n")

        # Top 5 des configurations les plus lentes
        f.write("## 🐌 Top 5 configurations les plus lentes\n\n")
        top_5_slow = config_stats.nlargest(5, 'mean_time')
        f.write("| Corpus | Mode | LLM | Multi-query | Temps | N |\n")
        f.write("|--------|------|-----|-------------|-------|---|\n")
        for idx, row in top_5_slow.iterrows():
            f.write(f"| {row['corpus']} | {row['search_mode']} | {row['llm_model']} | "
                   f"{row['multiquery']} | {row['mean_time']:.3f}s | {int(row['count'])} |\n")
        f.write("\n")

        # Stats de ressources (si disponible)
        resource_cols = ['cpu_avg', 'cpu_max', 'ram_avg', 'ram_max', 'gpu_avg', 'gpu_max']
        available_cols = [col for col in resource_cols if col in df.columns]

        if available_cols:
            f.write("## 💻 Utilisation des ressources (moyennes globales)\n\n")
            f.write("| Ressource | Valeur |\n")
            f.write("|-----------|--------|\n")

            if 'cpu_avg' in df.columns:
                cpu_avg_vals = df['cpu_avg'].dropna()
                if len(cpu_avg_vals) > 0:
                    f.write(f"| CPU moyen | {cpu_avg_vals.mean():.1f}% |\n")

            if 'cpu_max' in df.columns:
                cpu_max_vals = df['cpu_max'].dropna()
                if len(cpu_max_vals) > 0:
                    f.write(f"| CPU max | {cpu_max_vals.mean():.1f}% |\n")

            if 'ram_avg' in df.columns:
                ram_avg_vals = df['ram_avg'].dropna()
                if len(ram_avg_vals) > 0:
                    f.write(f"| RAM moyenne | {ram_avg_vals.mean():.1f}% |\n")

            if 'ram_max' in df.columns:
                ram_max_vals = df['ram_max'].dropna()
                if len(ram_max_vals) > 0:
                    f.write(f"| RAM max | {ram_max_vals.mean():.1f}% |\n")

            if 'gpu_avg' in df.columns:
                gpu_avg_vals = df['gpu_avg'].dropna()
                if len(gpu_avg_vals) > 0:
                    f.write(f"| GPU moyen | {gpu_avg_vals.mean():.1f}% |\n")

            if 'gpu_max' in df.columns:
                gpu_max_vals = df['gpu_max'].dropna()
                if len(gpu_max_vals) > 0:
                    f.write(f"| GPU max | {gpu_max_vals.mean():.1f}% |\n")

            f.write("\n")

        # Tableau détaillé par configuration (toutes les configurations)
        f.write("## 📊 Détails par configuration\n\n")
        if available_cols:
            f.write("| Corpus | Mode | LLM | Multi-query | Temps (moy) | Temps (méd) | Min | Max | Écart-type | CPU avg | CPU max | RAM avg | RAM max | N |\n")
            f.write("|--------|------|-----|-------------|-------------|-------------|-----|-----|------------|---------|---------|---------|---------|---|\n")

            for idx, row in config_stats.iterrows():
                cpu_avg = f"{row['cpu_avg_mean']:.1f}%" if pd.notna(row.get('cpu_avg_mean')) else "N/A"
                cpu_max = f"{row['cpu_max_mean']:.1f}%" if pd.notna(row.get('cpu_max_mean')) else "N/A"
                ram_avg = f"{row['ram_avg_mean']:.1f}%" if pd.notna(row.get('ram_avg_mean')) else "N/A"
                ram_max = f"{row['ram_max_mean']:.1f}%" if pd.notna(row.get('ram_max_mean')) else "N/A"

                f.write(f"| {row['corpus']} | {row['search_mode']} | {row['llm_model']} | "
                       f"{row['multiquery']} | {row['mean_time']:.3f}s | {row['median_time']:.3f}s | "
                       f"{row['min_time']:.3f}s | {row['max_time']:.3f}s | {row['std_time']:.3f}s | "
                       f"{cpu_avg} | {cpu_max} | {ram_avg} | {ram_max} | {int(row['count'])} |\n")
        else:
            f.write("| Corpus | Mode | LLM | Multi-query | Temps (moy) | Temps (méd) | Min | Max | Écart-type | N |\n")
            f.write("|--------|------|-----|-------------|-------------|-------------|-----|-----|------------|---|\n")

            for idx, row in config_stats.iterrows():
                f.write(f"| {row['corpus']} | {row['search_mode']} | {row['llm_model']} | "
                       f"{row['multiquery']} | {row['mean_time']:.3f}s | {row['median_time']:.3f}s | "
                       f"{row['min_time']:.3f}s | {row['max_time']:.3f}s | {row['std_time']:.3f}s | "
                       f"{int(row['count'])} |\n")
        f.write("\n")

    print(f"✓ Rapport markdown sauvegardé : {report_file}")


def main():
    """Fonction principale"""
    print("=" * 70)
    print("=== Analyse des résultats de benchmark RAG ===")
    print("=" * 70)

    # Dossiers
    benchmark_dir = Path(__file__).parent
    results_dir = benchmark_dir / "resultats"
    analysis_dir = benchmark_dir / "analyse"

    # Créer le dossier d'analyse
    analysis_dir.mkdir(exist_ok=True)
    print(f"\n✓ Dossier d'analyse : {analysis_dir}")

    # Charger les résultats
    df = load_all_results(results_dir)
    if df is None or len(df) == 0:
        print("\n⚠️  Aucune donnée à analyser")
        return

    print("\n" + "=" * 70)
    print("Génération des analyses...")
    print("=" * 70)

    # Analyse par configuration complète
    print("\n1️⃣  Analyse par configuration...")
    config_stats = analyze_by_configuration(df)
    output_file = analysis_dir / "stats_by_configuration.csv"
    config_stats.to_csv(output_file, index=False, float_format='%.4f')
    print(f"   ✓ {output_file.name}")

    # Analyse par mode de recherche
    print("\n2️⃣  Analyse par mode de recherche...")
    mode_stats = analyze_by_search_mode(df)
    output_file = analysis_dir / "stats_by_search_mode.csv"
    mode_stats.to_csv(output_file, index=False, float_format='%.4f')
    print(f"   ✓ {output_file.name}")

    # Analyse par modèle LLM
    print("\n3️⃣  Analyse par modèle LLM...")
    llm_stats = analyze_by_llm_model(df)
    if llm_stats is not None:
        output_file = analysis_dir / "stats_by_llm_model.csv"
        llm_stats.to_csv(output_file, index=False, float_format='%.4f')
        print(f"   ✓ {output_file.name}")
    else:
        print("   ⚠️  Aucune donnée RAG trouvée")

    # Analyse par corpus
    print("\n4️⃣  Analyse par corpus...")
    corpus_stats = analyze_by_corpus(df)
    output_file = analysis_dir / "stats_by_corpus.csv"
    corpus_stats.to_csv(output_file, index=False, float_format='%.4f')
    print(f"   ✓ {output_file.name}")

    # Analyse impact multi-query
    print("\n5️⃣  Analyse de l'impact multi-query...")
    multiquery_stats = analyze_multiquery_impact(df)
    if multiquery_stats is not None:
        output_file = analysis_dir / "stats_multiquery_impact.csv"
        multiquery_stats.to_csv(output_file, index=False, float_format='%.4f')
        print(f"   ✓ {output_file.name}")
    else:
        print("   ⚠️  Aucune donnée RAG trouvée")

    # Analyse des ressources
    print("\n6️⃣  Analyse de l'utilisation des ressources...")
    resource_stats = analyze_resource_usage(df)
    if resource_stats is not None:
        output_file = analysis_dir / "stats_resource_usage.csv"
        resource_stats.to_csv(output_file, index=False, float_format='%.4f')
        print(f"   ✓ {output_file.name}")
    else:
        print("   ⚠️  Aucune donnée de ressources trouvée")

    # Créer le rapport markdown
    print("\n7️⃣  Génération du rapport markdown...")
    create_markdown_report(df, analysis_dir)

    print("\n" + "=" * 70)
    print("✅ Analyse terminée !")
    print("=" * 70)
    print(f"\n📁 Tous les fichiers d'analyse sont disponibles dans : {analysis_dir}")

    # Afficher un aperçu des stats LLM
    if llm_stats is not None and len(llm_stats) > 0:
        print("\n" + "=" * 70)
        print("📊 TEMPS MOYEN PAR MODÈLE LLM")
        print("=" * 70)
        for idx, row in llm_stats.iterrows():
            print(f"{row['llm_model']:15} : {row['mean_time']:.3f}s (n={int(row['count'])})")


if __name__ == "__main__":
    main()
