from langchain_core.prompts import ChatPromptTemplate

detect_language_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """
     Detect the language of the message below. Only return the name of the language (e.g. English, French, Spanish, etc).
     """),
    
    ("user", "{text}")
])