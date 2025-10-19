from langchain_core.prompts import ChatPromptTemplate
from src.config.llm import get_llm

template_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "{prompt}"),
        ("placeholder", "{messages}"),
    ]
)
