from pydantic_settings import BaseSettings
from functools import lru_cache


class RetrieverSettings(BaseSettings):
    # Configure in .env under RULE_RETRIEVER_* prefix
    llm_model: str = "groq/llama-3.3-70b-versatile"
    llm_api_key: str = ""
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2000

    tree_index_path: str = "./pre_processing_fbr_doc/PageIndex-main/results/fbr_combined_structure.json"
    markdown_path: str = "./pre_processing_fbr_doc/fbr_combined.md"

    max_nodes: int = 7
    max_passes: int = 2

    model_config = {
        "env_prefix": "RULE_RETRIEVER_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> RetrieverSettings:
    return RetrieverSettings()
