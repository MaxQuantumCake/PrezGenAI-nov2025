"""
Configuration centralisée pour les scripts OpenSearch
"""

# Configuration OpenSearch
OPENSEARCH_HOST = "localhost"
OPENSEARCH_PORT = 9200

# Noms des index
INDEX_NAME = "cielnet_faq"
INDEX_NAME_SEMANTIC = "cielnet_faq_semantic"
INDEX_NAME_PIPELINE = "cielnet_faq_pipeline"

# Pipeline d'ingestion
PIPELINE_NAME = "faq_embedding_pipeline"

# Modèle d'embedding
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ID du modèle ML déployé dans OpenSearch (à remplir après déploiement)
ML_MODEL_ID = "TPaF2JkBUgRyUV6IgF2W"  
