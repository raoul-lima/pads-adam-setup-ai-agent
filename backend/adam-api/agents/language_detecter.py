from config.configs import llm_gemini_lite
from agents.prompts.language_prompt import detect_language_prompt

def detect_user_language(text: str) -> str:
    """
    Fixed by passing the llm as a parameter and using the proper invocation pattern
    """
    chain = detect_language_prompt | llm_gemini_lite
    return chain.invoke({"text": text})