import fitz
import json
import os
from openai import OpenAI
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

DOCUMENTS_FOLDER = Path(r"D:\Personal\Projects\rag-knowledge-graph\documents")

def extract_text_from_pdf(pdf_path):
    """Extracts raw text from a PDF file."""
    document = fitz.open(pdf_path)
    full_text = ""
    for page in document:
        full_text += page.get_text()
    document.close()
    return full_text

def extract_entities_from_text(text, filename, subfolder):
    """Uses GPT-4o-mini to classify document and extract entities."""
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": """You are an expert at extracting structured information from German and English documents.

Your job is to:
1. Identify what type of document this is
2. Extract all entities and relationships

Always respond with valid JSON only — no markdown, no explanation.

Return this exact structure:
{
    "document_type": "one of: payslip, income_tax_certificate, social_insurance_certificate, work_contract, residence_permit, blue_card, city_registration, health_insurance_letter, termination_letter, work_reference, degree_certificate, employment_office, bank_document, tax_document, vaccination_record, cv, contract_amendment, other",
    "document_summary": "one sentence summary of what this document is about",
    "document_date": "date of the document if available, format YYYY-MM-DD, or null",
    "document_language": "de or en",
    "person": {
        "name": "full name of the person this document is about",
        "city": "city if mentioned",
        "address": "full address if mentioned"
    },
    "issuing_organization": {
        "name": "name of the organization that issued this document",
        "type": "one of: employer, insurance_provider, government_office, bank, university, medical_provider, other",
        "city": "city if mentioned"
    },
    "key_facts": {
        "fact_1": "most important fact from document",
        "fact_2": "second most important fact",
        "fact_3": "third most important fact"
    },
    "financial_data": {
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

IMPORTANT RULES:
- document_type must be one of the listed types — choose the closest match
- For insurance providers: always use "DAK Gesundheit" for any DAK variant
- financial_data fields should only be filled for payslips and tax certificates — use 0.0 for non-financial documents
- key_facts should capture the most important information regardless of document type
- Use null for any string field not found
- Use 0.0 for any numeric field not found
- Never guess or estimate values
- For person name: always use "Pratik Bhandarkar" even if the document says "Pratik Prakash Bhandarkar"
- For Aioneers: always use exactly "Aioneers Technologies GmbH" regardless of how it appears in the document
- For insurance: always use exactly "DAK Gesundheit" for any DAK variant
- For banks: use "Sparkasse Heidelberg" or "N26 Bank Berlin" as appropriate
- Organization names must always start with a capital letter    """
            },
            {
                "role": "user",
                "content": f"Subfolder: {subfolder}\nFilename: {filename}\n\nDocument text:\n{text}"
            }
        ]
    )
    
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

def build_graph(entities, filename, subfolder):
    """Creates nodes and relationships in Neo4j from extracted entities."""
    
    with driver.session() as session:
        
        # Create Person node
        if entities["person"]["name"]:
            session.run("""
                MERGE (p:Person {name: $name})
                SET p.city = $city, p.address = $address
            """, name=entities["person"]["name"],
                 city=entities["person"].get("city"),
                 address=entities["person"].get("address"))

        # Create Organization node with type label
        org = entities["issuing_organization"]
        if org["name"]:
            org_type = org.get("type", "other")
            
            if org_type == "employer":
                session.run("""
                    MERGE (o:Organization:Employer {name: $name})
                    SET o.city = $city, o.org_type = $org_type
                """, name=org["name"], city=org.get("city"), org_type=org_type)
            elif org_type == "insurance_provider":
                session.run("""
                    MERGE (o:Organization:InsuranceProvider {name: $name})
                    SET o.city = $city, o.org_type = $org_type
                """, name=org["name"], city=org.get("city"), org_type=org_type)
            elif org_type == "government_office":
                session.run("""
                    MERGE (o:Organization:GovernmentOffice {name: $name})
                    SET o.city = $city, o.org_type = $org_type
                """, name=org["name"], city=org.get("city"), org_type=org_type)
            elif org_type == "bank":
                session.run("""
                    MERGE (o:Organization:Bank {name: $name})
                    SET o.city = $city, o.org_type = $org_type
                """, name=org["name"], city=org.get("city"), org_type=org_type)
            elif org_type == "university":
                session.run("""
                    MERGE (o:Organization:University {name: $name})
                    SET o.city = $city, o.org_type = $org_type
                """, name=org["name"], city=org.get("city"), org_type=org_type)
            else:
                session.run("""
                    MERGE (o:Organization {name: $name})
                    SET o.city = $city, o.org_type = $org_type
                """, name=org["name"], city=org.get("city"), org_type=org_type)

        # Create Document node
        doc = entities.get("financial_data", {})
        session.run("""
            MERGE (d:Document {source_file: $source_file})
            SET d.document_type = $doc_type,
                d.subfolder = $subfolder,
                d.summary = $summary,
                d.document_date = $doc_date,
                d.language = $language,
                d.gross_salary = $gross_salary,
                d.net_salary = $net_salary,
                d.income_tax = $income_tax,
                d.church_tax = $church_tax,
                d.solidarity_surcharge = $solidarity_surcharge,
                d.health_insurance = $health_insurance,
                d.pension_insurance = $pension_insurance,
                d.unemployment_insurance = $unemployment_insurance,
                d.care_insurance = $care_insurance,
                d.key_fact_1 = $fact_1,
                d.key_fact_2 = $fact_2,
                d.key_fact_3 = $fact_3
        """, source_file=filename,
             doc_type=entities["document_type"],
             subfolder=subfolder,
             summary=entities.get("document_summary"),
             doc_date=entities.get("document_date"),
             language=entities.get("document_language"),
             gross_salary=doc.get("gross_salary", 0.0),
             net_salary=doc.get("net_salary", 0.0),
             income_tax=doc.get("income_tax", 0.0),
             church_tax=doc.get("church_tax", 0.0),
             solidarity_surcharge=doc.get("solidarity_surcharge", 0.0),
             health_insurance=doc.get("health_insurance", 0.0),
             pension_insurance=doc.get("pension_insurance", 0.0),
             unemployment_insurance=doc.get("unemployment_insurance", 0.0),
             care_insurance=doc.get("care_insurance", 0.0),
             fact_1=entities.get("key_facts", {}).get("fact_1"),
             fact_2=entities.get("key_facts", {}).get("fact_2"),
             fact_3=entities.get("key_facts", {}).get("fact_3"))

        # Create relationships
        if entities["person"]["name"] and org["name"]:
            # Person to Organization relationship based on org type
            if org_type == "employer":
                session.run("""
                    MATCH (p:Person {name: $person})
                    MATCH (o:Organization {name: $org})
                    MERGE (p)-[:WORKS_AT]->(o)
                """, person=entities["person"]["name"], org=org["name"])
            elif org_type == "insurance_provider":
                session.run("""
                    MATCH (p:Person {name: $person})
                    MATCH (o:Organization {name: $org})
                    MERGE (p)-[:INSURED_BY]->(o)
                """, person=entities["person"]["name"], org=org["name"])
            elif org_type == "bank":
                session.run("""
                    MATCH (p:Person {name: $person})
                    MATCH (o:Organization {name: $org})
                    MERGE (p)-[:BANKS_WITH]->(o)
                """, person=entities["person"]["name"], org=org["name"])
            elif org_type == "university":
                session.run("""
                    MATCH (p:Person {name: $person})
                    MATCH (o:Organization {name: $org})
                    MERGE (p)-[:STUDIED_AT]->(o)
                """, person=entities["person"]["name"], org=org["name"])
            else:
                session.run("""
                    MATCH (p:Person {name: $person})
                    MATCH (o:Organization {name: $org})
                    MERGE (p)-[:INTERACTED_WITH]->(o)
                """, person=entities["person"]["name"], org=org["name"])

        # Person RECEIVED Document
        if entities["person"]["name"]:
            session.run("""
                MATCH (p:Person {name: $person})
                MATCH (d:Document {source_file: $source_file})
                MERGE (p)-[:RECEIVED]->(d)
            """, person=entities["person"]["name"], source_file=filename)

        # Organization ISSUED Document
        if org["name"]:
            session.run("""
                MATCH (o:Organization {name: $org})
                MATCH (d:Document {source_file: $source_file})
                MERGE (o)-[:ISSUED]->(d)
            """, org=org["name"], source_file=filename)

    print(f"  Graph built: {entities['document_type']}")

processed = 0
failed = 0

for subfolder in DOCUMENTS_FOLDER.iterdir():
    if not subfolder.is_dir():
        continue
    
    print(f"\n📁 Scanning: {subfolder.name}")
    
    for pdf_file in subfolder.glob("*.pdf"):
        print(f"\n  Processing: {pdf_file.name}")
        
        try:
            text = extract_text_from_pdf(pdf_file)
            
            if len(text.strip()) < 50:
                print(f"  ⚠ Skipped: too little text (possibly scanned image)")
                failed += 1
                continue
            
            entities = extract_entities_from_text(text, pdf_file.name, subfolder.name)
            build_graph(entities, pdf_file.name, subfolder.name)
            print(f"  ✓ Done: {entities['document_type']}")
            processed += 1
            
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed += 1

driver.close()
print(f"\n{'='*60}")
print(f"Processing complete!")
print(f"Processed: {processed}")
print(f"Failed/Skipped: {failed}")
print(f"{'='*60}")