import os
from openai import OpenAI
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

GRAPH_SCHEMA = """
You are an expert Neo4j Cypher query generator.

The knowledge graph has the following schema:

Nodes:
- (:Person {name, city, address}) — there is only ONE Person in this graph (the user)
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
- There is only ONE Person in the graph — NEVER filter Person by name in WHERE clauses
- When referring to "I", "my", "me" — match the Person node without any WHERE filter
- Year is stored as a string e.g. "2023" not 2023
- Month is stored as three letter abbreviation e.g. "Feb"
- Salary fields are stored as floats
- Always use MATCH and RETURN — never MERGE, CREATE, DELETE or SET
- Return only the Cypher query with no explanation and no markdown

EXAMPLES:

Question: "Which companies have I worked at?"
Cypher: MATCH (p:Person)-[:WORKS_AT]->(c:Company) RETURN c.name

Question: "What was my total net salary in 2024?"
Cypher: MATCH (p:Person)-[:RECEIVED]->(d:Document) WHERE d.year = "2024" RETURN SUM(d.net_salary) AS total

Question: "What was my total income tax across all years?"
Cypher: MATCH (p:Person)-[:RECEIVED]->(d:Document) RETURN SUM(d.income_tax) AS total_tax

Question: "Which bank do I use?"
Cypher: MATCH (p:Person)-[:BANKS_WITH]->(b:Bank) RETURN b.name

Question: "What was my highest net salary?"
Cypher: MATCH (p:Person)-[:RECEIVED]->(d:Document) RETURN MAX(d.net_salary) AS highest

Question: "Who is my health insurance provider?"
Cypher: MATCH (p:Person)-[:INSURED_BY]->(i:InsuranceProvider) RETURN i.name
"""

def question_to_cypher(question):
    """Converts a natural language question into a Cypher query."""
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": GRAPH_SCHEMA},
            {"role": "user", "content": f"Generate a Cypher query for this question: {question}"}
        ]
    )
    
    cypher = response.choices[0].message.content.strip()
    
    # Clean any markdown code blocks the LLM might add
    cypher = cypher.replace("```cypher", "").replace("```", "").strip()
    
    return cypher

def run_cypher_query(cypher):
    """Runs a Cypher query against Neo4j and returns the results."""
    with driver.session() as session:
        result = session.run(cypher)
        records = [record.data() for record in result]
    return records

def results_to_answer(question, cypher, results):
    """Converts query results into a natural language answer."""
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You are a helpful assistant that explains query results in plain English.
Convert the database query results into a clear, conversational answer.
Be precise with numbers and currency amounts.
If the question was in German, respond in German.
If the question was in English, respond in English.
Keep the answer concise and natural."""
            },
            {
                "role": "user",
                "content": f"""Question: {question}

Cypher query used: {cypher}

Results: {results}

Generate a natural language answer based on these results."""
            }
        ]
    )
    
    return response.choices[0].message.content

print("Knowledge Graph Query System")
print("Ask questions about your payslips. Type 'exit' to quit.\n")

while True:
    question = input("Ask: ")
    
    if question.lower() == "exit":
        break
    
    print("\nGenerating Cypher query...")
    cypher = question_to_cypher(question)
    print(f"Cypher:\n{cypher}\n")
    
    try:
        print("Running query against Neo4j...")
        results = run_cypher_query(cypher)
        
        print("Generating answer...\n")
        answer = results_to_answer(question, cypher, results)
        
        print("=" * 60)
        print(f"Answer:\n{answer}")
        print("=" * 60)
    except Exception as e:
        print(f"Error: {e}")

driver.close()