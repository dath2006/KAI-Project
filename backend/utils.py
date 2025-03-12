import logging
import os
import spacy
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# Load environment variables
load_dotenv()

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def extract_keywords(text):
    """
    Extract keywords from text using spaCy
    """
    doc = nlp(text)
    
    # Extract noun phrases, proper nouns, and entities
    keywords = []
    
    # Add named entities
    for ent in doc.ents:
        keywords.append(ent.text)
    
    # Add noun chunks (noun phrases)
    for chunk in doc.noun_chunks:
        keywords.append(chunk.text)
    
    # Add proper nouns and important nouns
    for token in doc:
        if token.pos_ in ["PROPN", "NOUN"] and token.is_alpha and not token.is_stop:
            keywords.append(token.text)
    
    # Remove duplicates and lowercase
    keywords = list(set([k.lower() for k in keywords]))
    
    return keywords

def validate_environment_variables():
    """
    Validate that all necessary environment variables are set
    """
    required_vars = [
        "NEO4J_URI", 
        "NEO4J_USER", 
        "NEO4J_PASSWORD"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

def format_document_content(content, doc_type):
    """
    Format document content based on document type
    """
    if doc_type == "email":
        # Extract email body, removing headers
        lines = content.split('\n')
        start_index = 0
        for i, line in enumerate(lines):
            if line.strip() == '':
                start_index = i + 1
                break
        
        return '\n'.join(lines[start_index:])
    
    # For other document types, return as is
    return content  # Fixed indentation issue here
