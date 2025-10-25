#!/usr/bin/env python3
"""
Script pour configurer automatiquement OpenSearch avec les modèles ML.
Basé sur le fichier config.es
"""

import requests
import json
import time
import urllib3
import os
from pathlib import Path
from dotenv import load_dotenv

# Supprime l'avertissement SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Charger les variables d'environnement depuis .env à la racine du projet
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

# Configuration depuis .env (obligatoire)
BASE_URL = os.environ['OPENSEARCH_URL']
EMBEDDING_MODEL = os.environ['EMBEDDING_MODEL']
MODEL_VERSION = os.environ['MODEL_VERSION']


def make_request(method: str, endpoint: str, data: dict = None):
    """Effectue une requête HTTP vers OpenSearch."""
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    headers = {'Content-Type': 'application/json'}

    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, json=data, verify=False)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data, verify=False)
        elif method.upper() == 'PUT':
            response = requests.put(url, headers=headers, json=data, verify=False)
        else:
            raise ValueError(f"Méthode HTTP non supportée: {method}")

        response.raise_for_status()
        result = response.json()

        print(f"✓ {method} {endpoint}")
        print(f"  Response: {json.dumps(result, indent=2)}\n")

        return result

    except requests.exceptions.RequestException as e:
        print(f"✗ Erreur lors de {method} {endpoint}")
        print(f"  Error: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}\n")
        raise


def wait_for_task(task_id: str, max_wait_time: int = 300):
    """Attend que la tâche soit terminée."""
    print(f"→ Attente de la fin de la tâche {task_id}...")
    start_time = time.time()

    while time.time() - start_time < max_wait_time:
        result = make_request('GET', f'/_plugins/_ml/tasks/{task_id}')
        state = result.get('state')

        print(f"  État: {state}")

        if state == 'COMPLETED':
            print(f"  ✓ Tâche terminée avec succès!\n")
            return result
        elif state == 'FAILED':
            print(f"  ✗ La tâche a échoué!\n")
            raise RuntimeError(f"La tâche {task_id} a échoué")

        time.sleep(5)

    raise TimeoutError(f"La tâche {task_id} n'a pas été terminée dans le délai imparti")


def step1_configure_cluster():
    """Étape 1: Configure les paramètres du cluster."""
    print("=" * 60)
    print("ÉTAPE 1: Configuration des paramètres du cluster")
    print("=" * 60)

    settings = {
        "persistent": {
            "plugins.ml_commons.only_run_on_ml_node": "false",
            "plugins.ml_commons.model_access_control_enabled": "true",
            "plugins.ml_commons.native_memory_threshold": "99"
        }
    }

    make_request('PUT', '_cluster/settings', settings)


def step2_create_model_group():
    """Étape 2: Crée un groupe de modèles ou utilise celui qui existe."""
    print("=" * 60)
    print("ÉTAPE 2: Vérification/Création du groupe de modèles")
    print("=" * 60)

    group_name = "local_model_group"

    # Vérifier si le groupe existe déjà
    try:
        search_result = make_request('GET', '/_plugins/_ml/model_groups/_search',
                                     {"query": {"match": {"name": group_name}}})

        hits = search_result.get('hits', {}).get('hits', [])

        if hits:
            # Le groupe existe déjà
            model_group_id = hits[0]['_id']
            print(f"→ Groupe de modèles existant trouvé: {group_name}")
            print(f"→ Model Group ID: {model_group_id}\n")
            return model_group_id
    except Exception as e:
        print(f"→ Aucun groupe existant trouvé, création d'un nouveau groupe...")

    # Créer un nouveau groupe si aucun n'existe
    model_group_data = {
        "name": group_name,
        "description": "A model group for local models"
    }

    result = make_request('POST', '/_plugins/_ml/model_groups/_register', model_group_data)
    model_group_id = result.get('model_group_id')

    print(f"→ Nouveau groupe créé: {group_name}")
    print(f"→ Model Group ID: {model_group_id}\n")
    return model_group_id


def step3_register_model(model_group_id: str):
    """Étape 3: Enregistre le modèle Hugging Face."""
    print("=" * 60)
    print("ÉTAPE 3: Enregistrement du modèle")
    print("=" * 60)

    print(f"Modèle à enregistrer : {EMBEDDING_MODEL}\n")

    model_data = {
        "name": f"huggingface/{EMBEDDING_MODEL}",
        "version": MODEL_VERSION,
        "model_group_id": model_group_id,
        "model_format": "TORCH_SCRIPT"
    }

    result = make_request('POST', '/_plugins/_ml/models/_register', model_data)
    task_id = result.get('task_id')

    print(f"→ Register Task ID: {task_id}\n")
    return task_id


def step4_deploy_model(model_id: str):
    """Étape 4: Déploie le modèle."""
    print("=" * 60)
    print("ÉTAPE 4: Déploiement du modèle")
    print("=" * 60)

    result = make_request('POST', f'/_plugins/_ml/models/{model_id}/_deploy')
    task_id = result.get('task_id')

    print(f"→ Deploy Task ID: {task_id}\n")
    return task_id


def save_model_id_to_env(model_id: str):
    """Sauvegarde le MODEL_ID dans le fichier .env."""
    project_root = Path(__file__).parent.parent
    env_path = project_root / '.env'

    # Lire le contenu existant
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []

    # Chercher si MODEL_ID existe déjà
    model_id_found = False
    for i, line in enumerate(lines):
        if line.strip().startswith('MODEL_ID='):
            lines[i] = f'MODEL_ID={model_id}\n'
            model_id_found = True
            break

    # Si MODEL_ID n'existe pas, l'ajouter
    if not model_id_found:
        lines.append(f'MODEL_ID={model_id}\n')

    # Écrire dans le fichier
    with open(env_path, 'w') as f:
        f.writelines(lines)

    print(f"✓ MODEL_ID sauvegardé dans {env_path}\n")


def main():
    """Point d'entrée principal du script."""
    print("\n" + "=" * 60)
    print("CONFIGURATION AUTOMATIQUE D'OPENSEARCH")
    print("=" * 60 + "\n")

    try:
        # Étape 1: Configuration du cluster
        step1_configure_cluster()

        # Étape 2: Création du groupe de modèles
        model_group_id = step2_create_model_group()

        # Étape 3: Enregistrement du modèle
        register_task_id = step3_register_model(model_group_id)

        # Attendre que l'enregistrement soit terminé
        task_result = wait_for_task(register_task_id)
        model_id = task_result.get('model_id')
        print(f"→ Model ID: {model_id}\n")

        # Étape 4: Déploiement du modèle
        deploy_task_id = step4_deploy_model(model_id)

        # Attendre que le déploiement soit terminé
        wait_for_task(deploy_task_id)

        # Sauvegarder le MODEL_ID dans le fichier .env
        save_model_id_to_env(model_id)

        print("\n" + "=" * 60)
        print("CONFIGURATION TERMINÉE !")
        print("=" * 60)
        print(f"\nRésumé des IDs:")
        print(f"  - Model Group ID: {model_group_id}")
        print(f"  - Model ID: {model_id}")
        print(f"  - Register Task ID: {register_task_id}")
        print(f"  - Deploy Task ID: {deploy_task_id}")

    except Exception as e:
        print(f"\n✗ Erreur lors de la configuration: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()