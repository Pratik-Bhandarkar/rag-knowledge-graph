import fitz
import json
import os
from openai import OpenAI
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Neo4j client
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

# Folders
PAYSLIPS_FOLDER = Path(r"D:\Personal\Projects\rag-knowledge-graph\documents\payslips")

load_dotenv()

# OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Neo4j client
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

# Folders
PAYSLIPS_FOLDER = Path(r"D:\Personal\Projects\rag-knowledge-graph\documents\payslips")

def extract_text_from_pdf(pdf_path):
    """Extracts raw text from a PDF file."""
    document = fitz.open(pdf_path)
    full_text = ""
    for page in document:
        full_text += page.get_text()
    document.close()
    return full_text

def extract_entities_from_text(text, filename):
    """Uses GPT-4o-mini to extract entities and relationships from payslip text."""
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """You are an expert at extracting structured information from payslip documents.
Extract entities and relationships from the provided payslip text.
Always respond with valid JSON only — no markdown, no explanation, just the JSON object.

Return this exact structure:
{
    "person": {
        "name": "full name",
        "city": "city name",
        "address": "full address if available"
    },
    "company": {
        "name": "company name",
        "city": "company city if available"
    },
    "bank": {
        "name": "bank name"
    },
    "insurance_provider": {
        "name": "health insurance provider name"
    },
    "document": {
        "month": "month abbreviation e.g. Feb",
        "year": "year as string e.g. 2026",
        "period": "payment period if available",
        "payment_date": "payment date if available",
        "gross_salary": 0.0,
        "net_salary": 0.0,
        "income_tax": 0.0,
        "church_tax": 0.0,
        "solidarity_surcharge": 0.0,
        "health_insurance": 0.0,
        "pension_insurance": 0.0,
        "unemployment_insurance": 0.0,
        "care_insurance": 0.0
    }
}

Use 0.0 for any numeric field not found. Use null for any string field not found."""
            },
            {
                "role": "user",
                "content": f"Extract entities from this payslip:\n\n{text}"
            }
        ]
    )
    
    raw = response.choices[0].message.content
    return json.loads(raw)

def build_graph(entities, filename):
    """Creates nodes and relationships in Neo4j from extracted entities."""
    
    with driver.session() as session:
        # Create Person node
        session.run("""
            MERGE (p:Person {name: $name})
            SET p.city = $city, p.address = $address
        """, name=entities["person"]["name"],
             city=entities["person"]["city"],
             address=entities["person"]["address"])

        # Create Company node
        session.run("""
            MERGE (c:Company {name: $name})
            SET c.city = $city
        """, name=entities["company"]["name"],
             city=entities["company"]["city"])

        # Create Bank node
        session.run("""
            MERGE (b:Bank {name: $name})
        """, name=entities["bank"]["name"])

        # Create Insurance Provider node
        session.run("""
            MERGE (i:InsuranceProvider {name: $name})
        """, name=entities["insurance_provider"]["name"])

        # Create Document node
        doc = entities["document"]
        session.run("""
            MERGE (d:Document {source_file: $source_file})
            SET d.month = $month,
                d.year = $year,
                d.period = $period,
                d.payment_date = $payment_date,
                d.gross_salary = $gross_salary,
                d.net_salary = $net_salary,
                d.income_tax = $income_tax,
                d.church_tax = $church_tax,
                d.solidarity_surcharge = $solidarity_surcharge,
                d.health_insurance = $health_insurance,
                d.pension_insurance = $pension_insurance,
                d.unemployment_insurance = $unemployment_insurance,
                d.care_insurance = $care_insurance
        """, source_file=filename,
             month=doc["month"],
             year=doc["year"],
             period=doc["period"],
             payment_date=doc["payment_date"],
             gross_salary=doc["gross_salary"],
             net_salary=doc["net_salary"],
             income_tax=doc["income_tax"],
             church_tax=doc["church_tax"],
             solidarity_surcharge=doc["solidarity_surcharge"],
             health_insurance=doc["health_insurance"],
             pension_insurance=doc["pension_insurance"],
             unemployment_insurance=doc["unemployment_insurance"],
             care_insurance=doc["care_insurance"])

        # Create relationships
        session.run("""
            MATCH (p:Person {name: $person})
            MATCH (c:Company {name: $company})
            MERGE (p)-[:WORKS_AT]->(c)
        """, person=entities["person"]["name"],
             company=entities["company"]["name"])

        session.run("""
            MATCH (p:Person {name: $person})
            MATCH (b:Bank {name: $bank})
            MERGE (p)-[:BANKS_WITH]->(b)
        """, person=entities["person"]["name"],
             bank=entities["bank"]["name"])

        session.run("""
            MATCH (p:Person {name: $person})
            MATCH (i:InsuranceProvider {name: $insurance})
            MERGE (p)-[:INSURED_BY]->(i)
        """, person=entities["person"]["name"],
             insurance=entities["insurance_provider"]["name"])

        session.run("""
            MATCH (p:Person {name: $person})
            MATCH (d:Document {source_file: $source_file})
            MERGE (p)-[:RECEIVED]->(d)
        """, person=entities["person"]["name"],
             source_file=filename)

        session.run("""
            MATCH (c:Company {name: $company})
            MATCH (d:Document {source_file: $source_file})
            MERGE (c)-[:ISSUED]->(d)
        """, company=entities["company"]["name"],
             source_file=filename)

    print(f"Graph built for: {filename}")

for pdf_file in PAYSLIPS_FOLDER.glob("*.pdf"):
    print(f"\nProcessing: {pdf_file.name}")
    
    text = extract_text_from_pdf(pdf_file)
    
    try:
        entities = extract_entities_from_text(text, pdf_file.name)
        build_graph(entities, pdf_file.name)
        print(f"✓ Done: {pdf_file.name}")
    except Exception as e:
        print(f"✗ Failed: {pdf_file.name} — {e}")

driver.close()
print("\nKnowledge graph construction complete!")