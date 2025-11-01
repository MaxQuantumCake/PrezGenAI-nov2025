#!/usr/bin/env python3
"""
Client pour interagir avec Ollama local
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import requests

# Charger les variables d'environnement depuis .env à la racine du projet
PROJECT_ROOT = Path(__file__).parent.parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(env_path)

# Configuration depuis .env
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.2')


class OllamaClient:
    """Client pour communiquer avec Ollama"""

    def __init__(self, base_url=OLLAMA_URL, model=OLLAMA_MODEL):
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.api_url = f"{self.base_url}/api"

    def check_connection(self):
        """
        Vérifie la connexion à Ollama

        Returns:
            bool: True si la connexion est établie, False sinon
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Erreur de connexion : {e}")
            return False

    def list_models(self):
        """
        Liste les modèles disponibles

        Returns:
            list: Liste des modèles disponibles
        """
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('models', [])
            return []
        except Exception as e:
            print(f"Erreur lors de la récupération des modèles : {e}")
            return []

    def generate(self, prompt, stream=False):
        """
        Génère une réponse à partir d'un prompt

        Args:
            prompt: Le texte du prompt
            stream: Si True, retourne un générateur pour le streaming

        Returns:
            str ou generator: La réponse complète ou un générateur si stream=True
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": stream
        }

        try:
            response = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                stream=stream,
                timeout=300
            )

            if stream:
                return self._stream_response(response)
            else:
                if response.status_code == 200:
                    data = response.json()
                    return data.get('response', '')
                else:
                    return f"Erreur {response.status_code}: {response.text}"

        except Exception as e:
            return f"Erreur lors de la génération : {e}"

    def _stream_response(self, response):
        """
        Générateur pour streamer la réponse

        Args:
            response: Response object de requests

        Yields:
            str: Fragments de la réponse
        """
        try:
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if 'response' in data:
                        yield data['response']
                    if data.get('done', False):
                        break
        except Exception as e:
            yield f"\nErreur lors du streaming : {e}"

    def chat(self, messages, stream=False):
        """
        Envoie une conversation au modèle

        Args:
            messages: Liste de messages [{"role": "user/assistant", "content": "..."}]
            stream: Si True, retourne un générateur pour le streaming

        Returns:
            str ou generator: La réponse du modèle
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }

        try:
            response = requests.post(
                f"{self.api_url}/chat",
                json=payload,
                stream=stream,
                timeout=300
            )

            if stream:
                return self._stream_chat_response(response)
            else:
                if response.status_code == 200:
                    data = response.json()
                    return data.get('message', {}).get('content', '')
                else:
                    return f"Erreur {response.status_code}: {response.text}"

        except Exception as e:
            return f"Erreur lors du chat : {e}"

    def _stream_chat_response(self, response):
        """
        Générateur pour streamer la réponse du chat

        Args:
            response: Response object de requests

        Yields:
            str: Fragments de la réponse
        """
        try:
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    if 'message' in data and 'content' in data['message']:
                        yield data['message']['content']
                    if data.get('done', False):
                        break
        except Exception as e:
            yield f"\nErreur lors du streaming : {e}"


def interactive_mode(client):
    """
    Mode interactif pour discuter avec Ollama

    Args:
        client: Instance de OllamaClient
    """
    print("\n" + "=" * 70)
    print("Mode conversation avec Ollama")
    print("=" * 70)
    print(f"Modèle : {client.model}")
    print("\nCommandes disponibles :")
    print("  - Tapez votre message pour discuter")
    print("  - '/clear' pour effacer l'historique")
    print("  - '/exit' pour quitter")
    print("-" * 70)

    conversation_history = []

    while True:
        user_input = input("\nVous > ").strip()

        if not user_input:
            continue

        if user_input.lower() in ['/exit', '/quit', '/q']:
            print("\nAu revoir!")
            break

        if user_input.lower() == '/clear':
            conversation_history = []
            print("✓ Historique effacé")
            continue

        # Ajouter le message de l'utilisateur à l'historique
        conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # Obtenir la réponse en streaming
        print("\nOllama > ", end="", flush=True)

        full_response = ""
        for chunk in client.chat(conversation_history, stream=True):
            print(chunk, end="", flush=True)
            full_response += chunk

        print()  # Nouvelle ligne après la réponse

        # Ajouter la réponse à l'historique
        conversation_history.append({
            "role": "assistant",
            "content": full_response
        })


def simple_mode(client):
    """
    Mode simple pour envoyer un prompt unique

    Args:
        client: Instance de OllamaClient
    """
    print("\n" + "=" * 70)
    print("Mode prompt simple")
    print("=" * 70)
    print(f"Modèle : {client.model}")
    print("\nCommandes disponibles :")
    print("  - Tapez votre prompt")
    print("  - '/exit' pour quitter")
    print("-" * 70)

    while True:
        user_input = input("\nPrompt > ").strip()

        if not user_input:
            continue

        if user_input.lower() in ['/exit', '/quit', '/q']:
            print("\nAu revoir!")
            break

        print("\nRéponse :\n")
        print("-" * 70)

        # Obtenir la réponse en streaming
        for chunk in client.generate(user_input, stream=True):
            print(chunk, end="", flush=True)

        print("\n" + "-" * 70)


def main():
    """Fonction principale"""
    print("=" * 70)
    print("=== Client Ollama ===")
    print("=" * 70)

    # Créer le client
    client = OllamaClient()

    # Vérifier la connexion
    print(f"\nConnexion à Ollama ({client.base_url})...")
    if not client.check_connection():
        print("✗ Impossible de se connecter à Ollama")
        print("Assurez-vous qu'Ollama est lancé (ollama serve)")
        return

    print("✓ Connecté à Ollama")

    # Lister les modèles disponibles
    print("\nModèles disponibles :")
    models = client.list_models()
    if models:
        for model in models:
            model_name = model.get('name', 'Inconnu')
            marker = " (sélectionné)" if model_name == client.model else ""
            print(f"  - {model_name}{marker}")
    else:
        print("  Aucun modèle trouvé")

    # Vérifier que le modèle sélectionné existe
    model_names = [m.get('name') for m in models]
    if client.model not in model_names:
        print(f"\n⚠️  Attention : Le modèle '{client.model}' n'est pas installé")
        print(f"Vous pouvez l'installer avec : ollama pull {client.model}")

        if models:
            print("\nVoulez-vous utiliser un autre modèle ?")
            for i, model in enumerate(models, 1):
                print(f"{i}. {model.get('name')}")

            choice = input("\nChoisissez un modèle (numéro) ou Entrée pour quitter : ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(models):
                client.model = models[int(choice) - 1].get('name')
                print(f"✓ Modèle sélectionné : {client.model}")
            else:
                return

    # Choisir le mode
    print("\n" + "=" * 70)
    print("Choisissez le mode :")
    print("1. Conversation (chat avec historique)")
    print("2. Prompt simple (sans historique)")
    print("-" * 70)

    while True:
        choice = input("\nVotre choix (1-2) : ").strip()
        if choice == '1':
            interactive_mode(client)
            break
        elif choice == '2':
            simple_mode(client)
            break
        else:
            print("Choix invalide. Veuillez entrer 1 ou 2.")


if __name__ == "__main__":
    main()
