from neo4j import GraphDatabase
import uuid
import logging

class KnowledgeGraph:
    def __init__(self, uri, user, password):  # Fixed __init__ method name
        """
        Initialize connection to Neo4j database
        """
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logging.info(f"Connected to Neo4j at {uri}")
        
    def close(self):
        """
        Close the driver connection
        """
        self.driver.close()
        
    def init_db(self):
        """
        Initialize database schema with constraints
        """
        with self.driver.session() as session:
            # Create constraints for unique IDs
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (t:Tip) REQUIRE t.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Expert) REQUIRE e.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.title IS UNIQUE")
            
            logging.info("Database schema initialized")
            
    def add_document(self, title, content, doc_type="pdf"):
        """
        Add a document to the knowledge graph
        """
        doc_id = str(uuid.uuid4())
        
        with self.driver.session() as session:
            session.run(
                "CREATE (d:Document {id: $id, title: $title, content: $content, type: $type, created_at: datetime()})",
                id=doc_id, title=title, content=content, type=doc_type
            )
            
        return doc_id
        
    def add_expert(self, name, email, expertise_areas):
        """
        Add an expert to the knowledge graph
        """
        expert_id = str(uuid.uuid4())
        
        with self.driver.session() as session:
            session.run(
                "CREATE (e:Expert {id: $id, name: $name, email: $email, expertise_areas: $areas, created_at: datetime()})",
                id=expert_id, name=name, email=email, areas=expertise_areas
            )
            
        return expert_id
        
    def add_tip(self, text, document_id, expert_id):
        """
        Add an expert tip related to a document
        """
        tip_id = str(uuid.uuid4())
        
        with self.driver.session() as session:
            # Create the tip
            session.run(
                "CREATE (t:Tip {id: $id, text: $text, created_at: datetime()})",
                id=tip_id, text=text
            )
            
            # Link tip to document
            session.run(
                """
                MATCH (d:Document), (t:Tip)
                WHERE d.id = $doc_id AND t.id = $tip_id
                CREATE (d)-[:HAS_TIP]->(t)
                """,
                doc_id=document_id, tip_id=tip_id
            )
            
            # Link tip to expert
            session.run(
                """
                MATCH (e:Expert), (t:Tip)
                WHERE e.id = $expert_id AND t.id = $tip_id
                CREATE (e)-[:PROVIDED]->(t)
                """,
                expert_id=expert_id, tip_id=tip_id
            )
            
        return tip_id
        
    def get_document_with_tips(self, doc_id):
        """
        Get a document and all its associated tips
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (d:Document {id: $id})
                OPTIONAL MATCH (d)-[:HAS_TIP]->(t:Tip)<-[:PROVIDED]-(e:Expert)
                RETURN d.id as doc_id, d.title as title, d.content as content, 
                       collect({tip_id: t.id, text: t.text, expert: e.name}) as tips
                """,
                id=doc_id
            )
            
            record = result.single()
            if not record:
                return None
                
            return {
                "id": record["doc_id"],
                "title": record["title"],
                "content": record["content"],
                "tips": [tip for tip in record["tips"] if tip["tip_id"] is not None]
            }
            
    def get_all_documents(self):
        """
        Get all documents with their associated tips
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (d:Document)
                OPTIONAL MATCH (d)-[:HAS_TIP]->(t:Tip)<-[:PROVIDED]-(e:Expert)
                RETURN d.id as doc_id, d.title as title, d.type as type,
                       collect({tip_id: t.id, text: t.text, expert_name: e.name}) as tips
                """
            )
            
            documents = []
            for record in result:
                # Filter out None values from tips
                tips = [tip for tip in record["tips"] if tip["tip_id"] is not None]
                
                documents.append({
                    "id": record["doc_id"],
                    "title": record["title"],
                    "type": record["type"],
                    "tips_count": len(tips),
                    "tips": tips
                })
                
            return documents
    
    def get_all_experts(self):
        """
        Get all experts from the knowledge graph
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Expert)
                OPTIONAL MATCH (e)-[:PROVIDED]->(t:Tip)-[:HAS_TIP]-(d:Document)
                RETURN e.id as id, e.name as name, e.email as email, e.expertise_areas as areas,
                       count(DISTINCT t) as tips_count
                """
            )
            
            experts = []
            for record in result:
                experts.append({
                    "id": record["id"],
                    "name": record["name"],
                    "email": record["email"],
                    "expertise_areas": record["areas"],
                    "tips_count": record["tips_count"]
                })
                
            return experts
            
    def find_knowledge_gaps(self):
        """
        Find documents that have no associated tips (knowledge gaps)
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (d:Document)
                WHERE NOT (d)-[:HAS_TIP]->()
                RETURN d.id as id, d.title as title, d.type as type
                """
            )
            
            gaps = [{"id": record["id"], "title": record["title"], "type": record["type"]} 
                   for record in result]
            
            return gaps
            
    def find_experts_for_topic(self, topic):
        """
        Find experts based on their expertise areas
        """
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (e:Expert)
                WHERE any(area IN e.expertise_areas WHERE toLower(area) CONTAINS toLower($topic))
                RETURN e.id as id, e.name as name, e.email as email, e.expertise_areas as areas
                """,
                topic=topic
            )
            
            experts = [{"id": record["id"], "name": record["name"], "email": record["email"], "areas": record["areas"]}
                     for record in result]
            
            return experts  # Fixed indentation issue at line 211
