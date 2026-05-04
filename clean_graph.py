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

        # Fix 1: Merge Person duplicates
        print("Fixing Person duplicates...")
        session.run("""
            MATCH (old:Person {name: "Pratik Prakash Bhandarkar"})
            MATCH (new:Person {name: "Pratik Bhandarkar"})
            WITH old, new
            MATCH (old)-[:RECEIVED]->(d:Document)
            MERGE (new)-[:RECEIVED]->(d)
        """)
        session.run("""
            MATCH (old:Person {name: "Pratik Prakash Bhandarkar"})
            MATCH (new:Person {name: "Pratik Bhandarkar"})
            WITH old, new
            MATCH (old)-[:WORKS_AT]->(o:Organization)
            MERGE (new)-[:WORKS_AT]->(o)
        """)
        session.run("""
            MATCH (old:Person {name: "Pratik Prakash Bhandarkar"})
            MATCH (new:Person {name: "Pratik Bhandarkar"})
            WITH old, new
            MATCH (old)-[:INSURED_BY]->(o:Organization)
            MERGE (new)-[:INSURED_BY]->(o)
        """)
        session.run("""
            MATCH (old:Person {name: "Pratik Prakash Bhandarkar"})
            MATCH (new:Person {name: "Pratik Bhandarkar"})
            WITH old, new
            MATCH (old)-[:BANKS_WITH]->(o:Organization)
            MERGE (new)-[:BANKS_WITH]->(o)
        """)
        session.run("""
            MATCH (old:Person {name: "Pratik Prakash Bhandarkar"})
            MATCH (new:Person {name: "Pratik Bhandarkar"})
            WITH old, new
            MATCH (old)-[:INTERACTED_WITH]->(o:Organization)
            MERGE (new)-[:INTERACTED_WITH]->(o)
        """)
        session.run("""
            MATCH (old:Person {name: "Pratik Prakash Bhandarkar"})
            DETACH DELETE old
        """)

        # Fix 2: Merge all Aioneers variants into one
        print("Fixing Aioneers duplicates...")
        canonical = "Aioneers Technologies GmbH"
        variants = ["aioneers GmbH", "aioneers Technologies GmbH", "Aioneers GmbH"]
        
        for variant in variants:
            session.run("""
                MATCH (old:Organization {name: $variant})
                MATCH (new:Organization {name: $canonical})
                WITH old, new
                OPTIONAL MATCH (old)<-[r1:WORKS_AT]-(p)
                FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (new)<-[:WORKS_AT]-(p)
                )
            """, variant=variant, canonical=canonical)
            session.run("""
                MATCH (old:Organization {name: $variant})
                MATCH (new:Organization {name: $canonical})
                WITH old, new
                OPTIONAL MATCH (old)-[r2:ISSUED]->(d)
                FOREACH (_ IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (new)-[:ISSUED]->(d)
                )
            """, variant=variant, canonical=canonical)
            session.run("""
                MATCH (old:Organization {name: $variant})
                WHERE old.name <> $canonical
                DETACH DELETE old
            """, variant=variant, canonical=canonical)

        # Fix 3: Merge DAK variants
        print("Fixing DAK duplicates...")
        session.run("""
            MATCH (old:Organization {name: "DAK-Gesundheit"})
            MATCH (new:Organization {name: "DAK Gesundheit"})
            WITH old, new
            OPTIONAL MATCH (p)-[:INSURED_BY]->(old)
            FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
                MERGE (p)-[:INSURED_BY]->(new)
            )
        """)
        session.run("""
            MATCH (old:Organization {name: "DAK-Gesundheit"})
            MATCH (new:Organization {name: "DAK Gesundheit"})
            WITH old, new
            OPTIONAL MATCH (old)-[:ISSUED]->(d)
            FOREACH (_ IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
                MERGE (new)-[:ISSUED]->(d)
            )
        """)
        session.run("""
            MATCH (old:Organization {name: "DAK-Gesundheit"})
            DETACH DELETE old
        """)

        print("\nData cleaning complete!")

        # Verify
        result = session.run("MATCH (p:Person) RETURN p.name")
        print("\nPersons:", [r["p.name"] for r in result])
        
        result = session.run("MATCH (o:Organization) RETURN o.name, o.org_type")
        print("Organizations:")
        for r in result:
            print(f"  {r['o.name']} ({r['o.org_type']})")

clean_graph()
driver.close()