import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

def clean_graph():
    with driver.session() as session:

        # Fix 1: Merge Aioneers duplicates
        print("Fixing Aioneers duplicates...")
        session.run("""
            MATCH (old:Company {name: "Aioneers GmbH"})
            MATCH (new:Company {name: "Aioneers Technologies GmbH"})
            WITH old, new
            MATCH (old)<-[r]-(n)
            MERGE (new)<-[:WORKS_AT]-(n)
        """)
        session.run("""
            MATCH (old:Company {name: "Aioneers GmbH"})
            MATCH (new:Company {name: "Aioneers Technologies GmbH"})
            WITH old, new
            MATCH (old)<-[r]-(d:Document)
            MERGE (new)<-[:ISSUED_BY]-(d)
        """)
        session.run("""
            MATCH (old:Company {name: "Aioneers GmbH"})
            DETACH DELETE old
        """)

        # Fix 2: Merge Sparkasse duplicates
        print("Fixing Sparkasse duplicates...")
        session.run("""
            MATCH (old:Bank {name: "Spk Heidelberg"})
            MATCH (new:Bank {name: "Sparkasse Heidelberg"})
            WITH old, new
            MATCH (p:Person)-[:BANKS_WITH]->(old)
            MERGE (p)-[:BANKS_WITH]->(new)
        """)
        session.run("""
            MATCH (old:Bank {name: "Spk Heidelberg"})
            DETACH DELETE old
        """)

        print("Data cleaning complete!")

clean_graph()
driver.close()