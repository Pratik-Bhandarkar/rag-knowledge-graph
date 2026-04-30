from pathlib import Path
import json
import chromadb

EMBEDDINGS_FOLDER = Path(r"D:\Personal\Projects\rag-knowledge-graph\embeddings")
CHROMA_DB_FOLDER = Path(r"D:\Personal\Projects\rag-knowledge-graph\chromadb")

COLLECTION_NAME = "payslips"

client = chromadb.PersistentClient(path=str(CHROMA_DB_FOLDER))
collection = client.get_or_create_collection(name=COLLECTION_NAME)

print(f"Connected to ChromaDB collection: {COLLECTION_NAME}")

def store_chunks(chunks, filename):
    """Stores chunks with embeddings into ChromaDB."""
    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for chunk in chunks:
        chunk_id = f"{filename}_chunk_{chunk['chunk_number']}"
        
        ids.append(chunk_id)
        embeddings.append(chunk["embedding"])
        documents.append(chunk["content"])
        metadatas.append({
            "source_file": chunk["source_file"],
            "chunk_number": chunk["chunk_number"]
        })

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    print(f"Stored {len(chunks)} chunks from {filename}")

for embeddings_file in EMBEDDINGS_FOLDER.glob("*.json"):
    with open(embeddings_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    
    store_chunks(chunks, embeddings_file.stem)

print("\nAll payslips stored in ChromaDB!")