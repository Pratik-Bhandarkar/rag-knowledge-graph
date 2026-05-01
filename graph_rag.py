import os
from typing import TypedDict
from openai import OpenAI
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
import chromadb
from pathlib import Path
import json

load_dotenv()

# OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Neo4j client
neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

# Embedding model
embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# ChromaDB client
chroma_client = chromadb.PersistentClient(path=str(Path(r"D:\Personal\Projects\rag-knowledge-graph\chromadb")))
collection = chroma_client.get_or_create_collection(name="payslips")

print("All connections established!")
print(f"ChromaDB chunks: {collection.count()}")

class GraphRAGState(TypedDict):
    question: str
    question_type: str
    cypher_query: str
    graph_results: list
    rag_results: list
    rag_filter: str
    answer: str

def classify_question(state: GraphRAGState) -> GraphRAGState:
    """Classifies the question and extracts RAG filter hints."""
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """You are a question classifier. Analyze the question and return a JSON response.

Classify into:
"graph" — for structured data: salaries, taxes, totals, averages, comparisons, relationships, entities, which company, which bank, who, how many, list all
"rag" — for document content: summarise, explain, describe, what does it say

Also extract any time/employer filters mentioned in the question.

Respond with ONLY valid JSON:
{"type": "graph", "employer": null, "month": null, "year": null}
or
{"type": "rag", "employer": null, "month": null, "year": null}

For month, use three letter abbreviation: Jan, Feb, Mar, Apr, May, Jun, Jul, Aug, Sep, Oct, Nov, Dec
For year, use four digit string: "2023", "2024"
For employer, use: Merck, Aioneers, EFESO

Examples:
"Summarise my February 2023 payslip" → {"type": "rag", "employer": null, "month": "Feb", "year": "2023"}
"What was my total salary in 2024?" → {"type": "graph", "employer": null, "month": null, "year": "2024"}
"Explain my EFESO November payslip" → {"type": "rag", "employer": "EFESO", "month": "Nov", "year": null}"""
            },
            {
                "role": "user",
                "content": state["question"]
            }
        ]
    )
    
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    
    try:
        parsed = json.loads(raw)
        state["question_type"] = parsed.get("type", "rag")
        
        # Build filter string for RAG
        filters = []
        if parsed.get("employer"):
            filters.append(parsed["employer"])
        if parsed.get("month"):
            filters.append(parsed["month"])
        if parsed.get("year"):
            filters.append(parsed["year"])
        state["rag_filter"] = "_".join(filters) if filters else ""
        
    except Exception:
        state["question_type"] = "rag"
        state["rag_filter"] = ""
    
    print(f"Question classified as: {state['question_type']}")
    if state["rag_filter"]:
        print(f"RAG filter: {state['rag_filter']}")
    
    return state

GRAPH_SCHEMA = """
You are an expert Neo4j Cypher query generator.

The knowledge graph has the following schema:

Nodes:
- (:Person {name, city, address}) — there is only ONE Person in this graph
- (:Company {name, city})
- (:Bank {name})
- (:InsuranceProvider {name})
- (:Document {source_file, month, year, period, payment_date, 
               gross_salary, net_salary, income_tax, church_tax,
               solidarity_surcharge, health_insurance, pension_insurance,
               unemployment_insurance, care_insurance})

Relationships:
- (Person)-[:WORKS_AT]->(Company)
- (Person)-[:INSURED_BY]->(InsuranceProvider)
- (Person)-[:BANKS_WITH]->(Bank)
- (Person)-[:RECEIVED]->(Document)
- (Company)-[:ISSUED]->(Document)

CRITICAL RULES:
- There is only ONE Person — NEVER filter Person by name
- Year is stored as a string e.g. "2023"
- Month is three letter abbreviation e.g. "Feb"
- Salary fields are floats
- Only generate read queries — never MERGE, CREATE, DELETE or SET
- Return only the Cypher query with no explanation and no markdown

EXAMPLES:
Question: "Which companies have I worked at?"
Cypher: MATCH (p:Person)-[:WORKS_AT]->(c:Company) RETURN c.name

Question: "What was my total net salary in 2024?"
Cypher: MATCH (p:Person)-[:RECEIVED]->(d:Document) WHERE d.year = "2024" RETURN SUM(d.net_salary) AS total

Question: "What was my total income tax across all years?"
Cypher: MATCH (p:Person)-[:RECEIVED]->(d:Document) RETURN SUM(d.income_tax) AS total_tax
"""

def query_knowledge_graph(state: GraphRAGState) -> GraphRAGState:
    """Generates Cypher query and runs it against Neo4j."""
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": GRAPH_SCHEMA},
            {"role": "user", "content": f"Generate a Cypher query for: {state['question']}"}
        ]
    )
    
    cypher = response.choices[0].message.content.strip()
    cypher = cypher.replace("```cypher", "").replace("```", "").strip()
    
    print(f"Cypher: {cypher}")
    state["cypher_query"] = cypher
    
    try:
        with neo4j_driver.session() as session:
            result = session.run(cypher)
            records = [record.data() for record in result]
        state["graph_results"] = records
        print(f"Graph results: {records}")
    except Exception as e:
        print(f"Graph query error: {e}")
        state["graph_results"] = []
    
    return state

def query_rag(state: GraphRAGState) -> GraphRAGState:
    """Searches ChromaDB for relevant document chunks with optional filtering."""
    
    query_embedding = embedding_model.encode(state["question"]).tolist()
    
    rag_filter = state.get("rag_filter", "")
    
    if rag_filter:
        # Get all matching chunks first, then search within them
        all_results = collection.get(
            where=None,
            include=["metadatas"]
        )
        
        # Find source files that match the filter
        matching_files = set()
        for meta in all_results["metadatas"]:
            source = meta.get("source_file", "")
            if all(part.lower() in source.lower() for part in rag_filter.split("_")):
                matching_files.add(source)
        
        if matching_files:
            print(f"Filtered to files: {matching_files}")
            
            if len(matching_files) == 1:
                where_filter = {"source_file": {"$eq": list(matching_files)[0]}}
            else:
                where_filter = {"source_file": {"$in": list(matching_files)}}
            
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5,
                where=where_filter
            )
        else:
            print("No matching files found — searching all chunks")
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=5
            )
    else:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=10
        )
    
    chunks = results["documents"][0] if results["documents"][0] else []
    
    print(f"RAG results: {len(chunks)} chunks found")
    state["rag_results"] = chunks
    
    return state

def generate_answer(state: GraphRAGState) -> GraphRAGState:
    """Generates a natural language answer from graph or RAG results."""
    
    if state["question_type"] == "graph":
        context = f"Cypher query: {state['cypher_query']}\nResults: {state['graph_results']}"
    else:
        context = "\n\n".join(state["rag_results"])
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """You are a helpful assistant that answers questions about payslips and salary documents.

CRITICAL LANGUAGE RULE: Detect the language of the Question and respond in that EXACT language.

- The language of the context is IRRELEVANT
- If the question is in English, respond entirely in English
- If the question is in German, respond entirely in German

Important rules:
- Use ONLY the provided context to answer the question
- Be precise with numbers — always use EUR for currency
- If the context is empty or doesn't contain the answer, say so
- Keep answers concise and clear"""
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {state['question']}"
            }
        ]
    )
    
    state["answer"] = response.choices[0].message.content
    return state

def route_question(state: GraphRAGState) -> str:
    """Routes to the correct pipeline based on question classification."""
    return state["question_type"]

# Build the workflow
workflow = StateGraph(GraphRAGState)

# Add nodes
workflow.add_node("classify", classify_question)
workflow.add_node("graph", query_knowledge_graph)
workflow.add_node("rag", query_rag)
workflow.add_node("answer", generate_answer)

# Set entry point
workflow.set_entry_point("classify")

# Add conditional routing — this is the magic
workflow.add_conditional_edges(
    "classify",
    route_question,
    {
        "graph": "graph",
        "rag": "rag"
    }
)

# Both paths lead to answer generation
workflow.add_edge("graph", "answer")
workflow.add_edge("rag", "answer")

# Answer leads to end
workflow.add_edge("answer", END)

# Compile the workflow
app = workflow.compile()

print("GraphRAG workflow compiled successfully!\n")

while True:
    question = input("Ask anything about your payslips (or type 'exit' to quit): ")
    
    if question.lower() == "exit":
        break
    
    initial_state = {
        "question": question,
        "question_type": "",
        "cypher_query": "",
        "graph_results": [],
        "rag_results": [],
        "rag_filter": "",
        "answer": ""
    }
    
    print("\nProcessing...\n")
    result = app.invoke(initial_state)
    
    print("=" * 60)
    print(f"Route: {result['question_type'].upper()}")
    print(f"\nAnswer:\n{result['answer']}")
    print("=" * 60)
    print()

neo4j_driver.close()