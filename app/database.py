import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load variables from .env
load_dotenv()

# Global variable to hold the client instance
client = None

# CONFIGURATION
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
MODEL_NAME = os.getenv("EMBED_MODEL")
CLIENT_MODEL_NAME = os.getenv("EMBED_MODEL_NAME")

def get_client():
    """
    Returns a single instance of the Qdrant client. 
    Initialization happens only when this function is called.
    """
    global client
    if client is None:
        db_host = os.getenv("QDRANT_HOST", "./qdrant_db")
        
        # Check if we are using Local Path or Docker Host
        if db_host.startswith("./") or "/" in db_host or "\\" in db_host:
            client = QdrantClient(path=db_host)
        else:
            client = QdrantClient(host=db_host, port=int(os.getenv("QDRANT_PORT", 6333)))
        
        client.set_model(MODEL_NAME)
    return client

def init_db():
    """Ensures the collection exists and is compatible"""
    # Get the client instance safely
    q_client = get_client()
    
    if q_client.collection_exists(COLLECTION_NAME):
        info = q_client.get_collection(COLLECTION_NAME)
        
        # Check for size mismatch (BGE-Small is 384, BGE-Large is 1024)
        # Note: Added a check to ensure CLIENT_MODEL_NAME exists in the vector config
        vector_info = info.config.params.vectors
        if CLIENT_MODEL_NAME in vector_info:
            current_size = vector_info[CLIENT_MODEL_NAME].size
            # Adjust the expected size based on your model (Small=384, Large=1024)
            expected_size = 384 if "small" in MODEL_NAME.lower() else 1024
            
            if current_size != expected_size:
                print(f"⚠️ Mismatch found (Current: {current_size}, Expected: {expected_size}). Recreating...")
                q_client.delete_collection(COLLECTION_NAME)

    if not q_client.collection_exists(COLLECTION_NAME):
        q_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=q_client.get_fastembed_vector_params() 
        )
        print("✅ Qdrant Collection Ready.")