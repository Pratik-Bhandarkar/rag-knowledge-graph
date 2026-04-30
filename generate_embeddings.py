from sentence_transformers import SentenceTransformer
from pathlib import Path
import json

CHUNKS_FOLDER = Path(r"D:\Personal\Projects\rag-knowledge-graph\chunks")
EMBEDDINGS_FOLDER = Path(r"D:\Personal\Projects\rag-knowledge-graph\embeddings")

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

print(f"Loading embedding model: {MODEL_NAME}")
model = SentenceTransformer(MODEL_NAME)
print("Model loaded successfully!")

def embed_chunks(chunks):
    """Adds embedding vectors to each chunk."""
    texts = [chunk["content"] for chunk in chunks]
    embeddings = model.encode(texts, show_progress_bar=True)
    
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding.tolist()
    
    return chunks

EMBEDDINGS_FOLDER.mkdir(exist_ok=True)

for chunks_file in CHUNKS_FOLDER.glob("*.json"):
    print(f"\nEmbedding: {chunks_file.name}")
    
    with open(chunks_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    chunks_with_embeddings = embed_chunks(chunks)
    
    output_file = EMBEDDINGS_FOLDER / chunks_file.name
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(chunks_with_embeddings, f, ensure_ascii=False, indent=2)
    
    print(f"Saved: {output_file.name}")