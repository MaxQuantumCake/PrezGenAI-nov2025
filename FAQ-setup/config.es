# Allow ML to run on any node
PUT _cluster/settings
{
  "persistent": {
    "plugins.ml_commons.only_run_on_ml_node": "false",
    "plugins.ml_commons.model_access_control_enabled": "true",
    "plugins.ml_commons.native_memory_threshold": "99"
  }
}

# Create a model group
POST /_plugins/_ml/model_groups/_register
{
  "name": "local_model_group",
  "description": "A model group for local models"
}

# Register a provided model
POST /_plugins/_ml/models/_register
{
  "name": "huggingface/sentence-transformers/msmarco-distilbert-base-tas-b",
  "version": "1.0.3",
  "model_group_id": "RfaE2JkBUgRyUV6Ifl0o",
  "model_format": "TORCH_SCRIPT"
}

GET /_plugins/_ml/tasks/SPaF2JkBUgRyUV6Iel3T

POST /_plugins/_ml/models/TPaF2JkBUgRyUV6IgF2W/_deploy

GET /_plugins/_ml/tasks/Ufb62JkBUgRyUV6IxF2S