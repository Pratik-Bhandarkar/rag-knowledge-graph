# 🧠 GraphRAG Document Assistant

A hybrid GraphRAG system that combines Knowledge Graphs (Neo4j) with Vector Search (ChromaDB) to intelligently query personal financial documents in natural language — supporting both English and German.

Built as a portfolio piece to demonstrate end-to-end AI engineering skills including knowledge graph construction, semantic search, intelligent query routing, and LLM orchestration.

---

## 🎯 Project Overview

This system automatically extracts entities and relationships from payslip documents, builds a knowledge graph in Neo4j, and combines it with vector-based RAG search. An intelligent LangGraph router automatically decides which pipeline to use based on the question type.

**Structured questions → Knowledge Graph:**
- "What was my total net salary in 2024?"
- "Which companies have I worked at?"
- "What was my average gross salary in 2023?"
- "How many payslips do I have from 2024?"

**Content questions → RAG Vector Search:**
- "Summarise my February 2023 payslip"
- "Explain my EFESO February 2026 payslip"
- "What deductions were made in my September 2025 payslip?"

---

## 🏗️ Architecture

```
PDF Documents
     ↓
┌────────────────────────────────┐
│  Two Parallel Pipelines        │
│                                │
│  Pipeline 1: Knowledge Graph   │
│  PyMuPDF → GPT-4o-mini        │
│  → Entity Extraction           │
│  → Neo4j Graph Database        │
│                                │
│  Pipeline 2: Vector RAG        │
│  PyMuPDF → Abbreviation Expand │
│  → Chunking (1000/100 overlap) │
│  → Multilingual Embeddings     │
│  → ChromaDB Vector Storage     │
└────────────────────────────────┘
     ↓
User Question
     ↓
LangGraph Router (GPT-4o-mini Classifier)
     ↓
┌────┴────┐
↓         ↓
Graph     RAG
Path      Path
↓         ↓
Cypher    Vector
Query     Search
↓         ↓
Neo4j     ChromaDB
↓         ↓
└────┬────┘
     ↓
Answer Generator (GPT-4o-mini)
     ↓
Natural Language Answer
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| PDF Extraction | PyMuPDF (fitz) |
| Entity Extraction | GPT-4o-mini (structured JSON output) |
| Knowledge Graph | Neo4j |
| Graph Query Language | Cypher (Text-to-Cypher via LLM) |
| Text Preprocessing | Regex-based abbreviation expansion |
| Chunking | Custom overlap chunking (1000 chars, 100 overlap) |
| Embeddings | paraphrase-multilingual-MiniLM-L12-v2 |
| Vector Database | ChromaDB |
| Query Router | LangGraph with conditional edges |
| LLM Orchestration | LangChain + LangGraph |
| Answer Generation | GPT-4o-mini (temperature=0) |
| UI | Streamlit |
| Language | Python 3.x |

---

## 📁 Project Structure

```
rag-knowledge-graph/
│
├── extract_entities.py       # LLM-based entity extraction → Neo4j
├── clean_graph.py            # Data quality: deduplicate graph nodes
├── chunk_documents.py        # PDF extraction + abbreviation expansion + chunking
├── generate_embeddings.py    # Multilingual embedding generation
├── store_embeddings.py       # ChromaDB storage with metadata
├── query_graph.py            # Text-to-Cypher terminal interface
├── graph_rag.py              # GraphRAG router (terminal version)
├── app.py                    # Streamlit UI with intelligent routing
├── test_neo4j.py             # Neo4j connection test
├── .env                      # API keys and credentials (gitignored)
├── .gitignore
└── README.md
```

---

## ⚙️ Setup Instructions

### Prerequisites
- Python 3.x
- Neo4j Desktop (free download from neo4j.com)
- OpenAI API key

### 1. Clone the repository
```bash
git clone https://github.com/Pratik-Bhandarkar/rag-knowledge-graph.git
cd rag-knowledge-graph
```

### 2. Create and activate virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Install dependencies
```bash
pip install pymupdf sentence-transformers chromadb neo4j openai python-dotenv langgraph langchain langchain-openai streamlit
```

### 4. Set up Neo4j
- Download and install Neo4j Desktop from neo4j.com
- Create a new instance called "RAG Knowledge Graph"
- Start the instance and note the connection URI

### 5. Configure environment variables
Create a `.env` file in the project root:
```
OPENAI_API_KEY=your_openai_api_key
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

### 6. Add your documents
```
documents/
└── payslips/
    └── Employer_Month_Year.pdf
```

### 7. Build the Knowledge Graph
```bash
python extract_entities.py    # Extract entities → Neo4j
python clean_graph.py         # Deduplicate nodes
```

### 8. Build the RAG Pipeline
```bash
python chunk_documents.py     # Extract + chunk documents
python generate_embeddings.py # Generate embeddings
python store_embeddings.py    # Store in ChromaDB
```

### 9. Run the app
```bash
streamlit run app.py
```

---

## 🔍 Key Features

### Intelligent Query Routing
LangGraph automatically classifies questions and routes them to the optimal pipeline:
- **Graph Route** 🔵 — structured data, aggregations, relationships → Neo4j Cypher
- **RAG Route** 🟢 — document content, summaries, explanations → ChromaDB vector search

### Automated Knowledge Graph Construction
GPT-4o-mini reads raw payslip text and automatically extracts:
- Entities: Person, Company, Bank, InsuranceProvider, Document
- Relationships: WORKS_AT, BANKS_WITH, INSURED_BY, RECEIVED, ISSUED
- Properties: salary figures, tax amounts, insurance contributions

### Data Quality Pipeline
Automated deduplication handles entity resolution challenges:
- Multiple name variants merged into canonical entries
- Insurance provider normalization across documents

### Smart RAG Filtering
The classifier extracts temporal and employer hints from questions to filter ChromaDB:
- "Summarise my February 2023 payslip" → filters to the specific source file only
- Unfiltered questions search across all chunks with dynamic result sizing

### Multilingual Support
- Questions accepted in English and German
- Responses match the question language
- Multilingual embedding model handles German document content

### Deterministic Responses
All LLM calls use temperature=0, ensuring identical questions always produce identical answers — critical for financial document queries.

---

## 🧠 Engineering Decisions

### Why GraphRAG instead of pure RAG?
Pure RAG struggles with aggregation queries ("total salary in 2024") because it retrieves individual chunks, not structured data. The knowledge graph stores salary figures as numeric properties, enabling instant SQL-like aggregations via Cypher.

### Why LangGraph for routing?
Simple if/else routing works but doesn't scale. LangGraph provides stateful workflow management with conditional edges, making the routing logic clean, extensible, and visualizable. It also demonstrates familiarity with a key framework in the AI engineering ecosystem.

### Why LLM-based entity extraction?
Manual knowledge graph construction doesn't scale. Using GPT-4o-mini for structured JSON extraction automates the process — 27 payslips processed in minutes with zero manual work.

### Why temperature=0?
LLMs are non-deterministic by default. For financial document queries where consistency matters, temperature=0 ensures identical inputs always produce identical outputs.

### Why data quality cleaning?
LLM-based extraction produces slight name variations across documents. A post-processing cleanup step merges duplicate entities, ensuring graph integrity for accurate aggregation queries.

### Why metadata filtering in RAG?
Without filtering, vector search returns semantically similar chunks from any document. Metadata filtering narrows the search to specific documents based on employer, month, and year — dramatically improving answer accuracy for targeted questions.

---

## ⚠️ Known Limitations

- **Table structure preservation** — complex German payroll tables (DATEV format) lose column-value relationships during PDF text extraction. This affects some deduction lookups in the RAG pipeline. Production solution: table-aware PDF parsing (e.g. AWS Textract, Azure Document Intelligence).
- **Cross-pipeline queries** — questions requiring both structured data AND document content simultaneously currently route to only one pipeline. A hybrid merge step would improve these responses.
- **Entity extraction accuracy** — LLM-based extraction occasionally misreads values from complex table layouts. The knowledge graph pipeline works best with clearly structured documents.

---

## 🚀 Future Improvements

- [ ] SPARQL query support via Neosemantics (n10s) plugin
- [ ] RDF/OWL knowledge representation layer
- [ ] Hybrid pipeline — merge graph and RAG results for complex questions
- [ ] Table-aware PDF parsing for German DATEV payslip format
- [ ] Semantic entity resolution using embedding similarity
- [ ] Support for additional document types (tax statements, insurance letters)
- [ ] AWS deployment pipeline
- [ ] Query caching for frequently asked questions

---

## 💡 What I Learned

- Knowledge graph design and construction with Neo4j
- Cypher query language for graph traversal and aggregation
- LLM-based structured entity extraction (JSON mode)
- LangGraph for stateful AI workflow orchestration
- Conditional routing between multiple AI pipelines
- Data quality engineering — entity deduplication and normalization
- Text-to-Cypher generation with few-shot prompting
- GraphRAG architecture — combining knowledge graphs with vector search
- ChromaDB metadata filtering for targeted document retrieval
- Prompt engineering for deterministic LLM behavior
- Building production-ready AI applications with Streamlit
- Engineering tradeoffs — knowing when to use graph vs vector search

---

## 📚 Related Project

**[RAG Document Assistant](https://github.com/Pratik-Bhandarkar/rag-document-assistant)** — my first RAG project, a pure vector-search based document assistant with both local LLM (Ollama) and OpenAI API support. This GraphRAG project builds on the concepts learned there.

---

## 👨‍💻 Author

Pratik Bhandarkar

[LinkedIn](https://linkedin.com/in/pratik-bhandarkar) | [GitHub](https://github.com/Pratik-Bhandarkar)