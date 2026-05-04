# 🧠 GraphRAG Document Assistant

A hybrid system combining Knowledge Graphs (Neo4j) with Vector Search (ChromaDB) to query personal documents in natural language — supporting English and German.

---

## 🎯 What It Does

Drop any PDF into the system — payslips, contracts, tax certificates, insurance letters — and it automatically:
1. Classifies the document type using GPT-4o-mini
2. Extracts entities and relationships into a Neo4j knowledge graph
3. Chunks and embeds text into ChromaDB for semantic search
4. Routes questions intelligently between Graph and RAG pipelines

**Graph Route** 🔵 → "What was my total salary in 2024?" → Neo4j Cypher → instant aggregation

**RAG Route** 🟢 → "Summarise my February 2023 payslip" → ChromaDB → detailed content answer

---

## 🏗️ Architecture

```
PDF Document → PyMuPDF → GPT-4o-mini
                              ↓
              ┌───────────────┴───────────────┐
              ↓                               ↓
    Knowledge Graph (Neo4j)         Vector RAG (ChromaDB)
    Entities, relationships,        Chunks, embeddings,
    structured data                 semantic search
              ↓                               ↓
              └───────────────┬───────────────┘
                              ↓
                   LangGraph Router
                   (auto-classifies question)
                              ↓
                   GPT-4o-mini Answer Generator
                   (temperature=0, deterministic)
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Knowledge Graph | Neo4j + Cypher |
| Vector Database | ChromaDB + paraphrase-multilingual-MiniLM-L12-v2 |
| Document Intelligence | GPT-4o-mini (classification + entity extraction) |
| Query Router | LangGraph + LangChain |
| PDF Extraction | PyMuPDF |
| UI | Streamlit |

---

## 📄 Auto-Classified Document Types

| Type | Count |
|---|---|
| Payslip | 42 |
| Income Tax Certificate | 4 |
| Social Insurance Certificate | 4 |
| Work Contract | 3 |
| Contract Amendment | 3 |
| Work Reference | 2 |
| Termination Letter, Insurance Letter, CV, Other | 1 each |

62 documents processed, 26 scanned documents auto-detected and skipped.

---

## ⚙️ Quick Start

```bash
# Setup
git clone https://github.com/Pratik-Bhandarkar/rag-knowledge-graph.git
cd rag-knowledge-graph
python -m venv venv && venv\Scripts\activate
pip install pymupdf sentence-transformers chromadb neo4j openai python-dotenv langgraph langchain langchain-openai streamlit

# Configure .env with: OPENAI_API_KEY, NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

# Build knowledge graph
python extract_all_documents.py
python clean_graph.py

# Build RAG pipeline
python chunk_documents.py
python generate_embeddings.py
python store_embeddings.py

# Run
streamlit run app.py
```

---

## 🔍 Key Features

- **Auto-classification** — GPT-4o-mini classifies any document into 18 categories automatically
- **Intelligent routing** — LangGraph routes questions to Graph or RAG pipeline
- **Text-to-Cypher** — natural language → Cypher queries with few-shot prompting
- **Smart RAG filtering** — extracts date/employer hints to filter ChromaDB before search
- **Data quality** — automated entity deduplication and normalization
- **Multilingual** — questions and documents in English or German
- **Deterministic** — temperature=0 ensures consistent answers
- **Scanned doc detection** — automatically skips PDFs without embedded text

---

## ⚠️ Known Limitations

- Scanned PDFs without OCR are skipped (production fix: AWS Textract)
- Complex German payroll tables lose structure during extraction
- Cross-pipeline queries route to only one pipeline currently

---

## 🚀 Future Improvements

- [ ] OCR for scanned documents
- [ ] Hybrid pipeline merging Graph + RAG results
- [ ] Multi-agent system with CrewAI
---

## 📚 Related Project

**[RAG Document Assistant](https://github.com/Pratik-Bhandarkar/rag-document-assistant)** — Pure vector-search RAG with local LLM (Ollama) and OpenAI API support.

---

## 👨‍💻 Author

Pratik Bhandarkar — Data Engineer

[LinkedIn](https://linkedin.com/in/pratik-bhandarkar) | [GitHub](https://github.com/Pratik-Bhandarkar)