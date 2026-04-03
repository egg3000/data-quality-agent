from config import settings


def get_chat_model():
    if settings.model_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=settings.model_name)
    elif settings.model_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.model_name)
    else:
        raise ValueError(f"Unsupported MODEL_PROVIDER: {settings.model_provider}")


def get_embeddings_model():
    if settings.embeddings_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings()
    else:  # default: local via fastembed — no API key required
        from langchain_community.embeddings import FastEmbedEmbeddings
        return FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
