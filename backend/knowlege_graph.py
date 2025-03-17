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
            
    def add_document(self, knowledge):
        """
        Add a document to the knowledge graph
        """
        doc_id = str(uuid.uuid4())
        
        with self.driver.session() as session:
            session.run(
                "CREATE (d:Document {id: $id, title: $title, filename: $filename, original_filename: $original_filename, author_id: $author_id, author_name: $author_name, field: $field, keywords: $keywords, fileLink: $fileLink, meme_type: $meme_type, created_at: datetime()})",
                id=doc_id, title=knowledge['title'], filename=knowledge['filename'], original_filename=knowledge['original_filename'], author_id=knowledge['author_id'], author_name=knowledge['author_name'], field=knowledge['field'], keywords=knowledge['keywords'], fileLink=knowledge['fileLink'], meme_type=knowledge['meme_type']
            )
            
        return doc_id
    
    def add_document_with_summary(self, title, summary, author_id, author_name):
        """
        Add a document with a summary to the knowledge graph
        """
        doc_id = str(uuid.uuid4())
        
        with self.driver.session() as session:
            session.run(
                "CREATE (d:Document {id: $id, title: $title, content: $content, author_id: $author_id, author_name: $author_name, created_at: datetime()})",
                id=doc_id, title=title, content=summary, author_id=author_id, author_name=author_name
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

    def add_chat_summary(self, topic, summary, author_id, author_name):
        """
        Add a chat summary as a separate Summary node in the knowledge graph
        """
        summary_id = str(uuid.uuid4())
        
        with self.driver.session() as session:
            session.run(
                """
                CREATE (s:Summary {
                    id: $id,
                    topic: $topic,
                    content: $summary,
                    author_id: $author_id,
                    author_name: $author_name,
                    type: 'chat_summary',
                    created_at: datetime()
                })
                """,
                id=summary_id,
                topic=topic,
                summary=summary,
                author_id=author_id,
                author_name=author_name
            )
            
        return summary_id
    
    def get_documents_for_field(self, field):
         """
         Retrieve documents from Neo4j that match the user's learning field.
         In this example, we check if the Document's 'field' property
         matches the user's field (case-insensitive).
         """
         with self.driver.session() as session:
            result = session.run(
            """
            MATCH (d:Document)
            WHERE toLower(d.field) = toLower($field)
            OR ANY(kw IN d.keywords WHERE toLower(kw) CONTAINS toLower($field))
            RETURN
                d.id as id,
                d.title as title,
                d.filename as filename,
                d.fileLink as fileLink,
                d.original_filename as original_filename,
                d.author_name as author_name,
                d.field as field,
                d.keywords as keywords,
                d.meme_type as meme_type,
                toString(d.created_at) as created_at
            ORDER BY d.created_at DESC
            LIMIT 10
            """,
            field=field
        )

            docs = []
            for record in result:
                doc = {
                "id": record["id"],
                "title": record["title"],
                "filename": record["filename"],
                "fileLink": record["fileLink"],
                "original_filename": record["original_filename"],
                "author_name": record["author_name"],
                "field": record["field"],
                "keywords": record["keywords"],
                "meme_type": record["meme_type"],
                "created_at": record["created_at"]
            }
            docs.append(doc)
            return docs

