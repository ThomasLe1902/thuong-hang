from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_genai.embeddings import GoogleGenerativeAIEmbeddings
from src.utils.logger import logger
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


# Default model instances
llm_2_0 = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=1)
llm_2_5_flash_preview = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-05-20", temperature=1
)
llm_2_0_flash_lite = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite", temperature=1
)
# Default embeddings model
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")


def get_llm_provider(
    model_name: str, base_url: str, api_key: str = None
) -> BaseChatModel:
    if model_name and base_url and api_key:
        return ChatOpenAI(
            model=model_name, temperature=1, base_url=base_url, openai_api_key=api_key
        )
    else:
        raise ValueError(
            "Model name, base URL, and API key must be provided for LLM provider."
        )


def get_llm(
    model_name: str = "gemini-2.0-flash",
    api_key: str = None,
    include_thoughts: bool = False,
    reasoning: bool = False,
) -> BaseChatModel:
    """
    Get LLM instance based on model name and optional API key.

    Args:
        model_name: Name of the model to use
        api_key: Optional API key for authentication

    Returns:
        Configured ChatGoogleGenerativeAI instance

    Raises:
        ValueError: If model name is not supported
    """
    if api_key:
        logger.warning("Using custom API key")
        if model_name == "gemini-2.0-flash":
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=1,
                google_api_key=api_key,
            )
        elif model_name == "gemini-2.5-flash-preview-05-20":
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=1,
                google_api_key=api_key,
                include_thoughts=include_thoughts,
                thinking_budget=None if reasoning else 0,
            )
        elif model_name == "gemini-2.0-flash-lite":
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=1,
                google_api_key=api_key,
            )

    if model_name == "gemini-2.0-flash":
        return llm_2_0
    elif model_name == "gemini-2.5-flash-preview-05-20":
        return llm_2_5_flash_preview
    elif model_name == "gemini-2.0-flash-lite":
        return llm_2_0_flash_lite

    raise ValueError(f"Unknown model: {model_name}")
