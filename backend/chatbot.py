import requests
import logging
import os
from dotenv import load_dotenv
import random
import string

# Load environment variables
load_dotenv()

class Chatbot:
    def __init__(self, knowledge_graph):  # Fixed constructor name
        """
        Initialize the chatbot with the knowledge graph
        """
        self.knowledge_graph = knowledge_graph
        logging.info("Chatbot initialized")
        
    def generate_message_id(self):
        """Generate a random message ID"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        
    def request_expert_input(self, query, gaps):
        """
        Request input from experts when knowledge gaps are detected
        
        In a real system, this would connect to Slack/Discord/Email APIs
        For the hackathon prototype, we'll simulate this
        """
        logging.info(f"Requesting expert input for query: {query}")
        
        # Simulate outreach
        message_id = self.generate_message_id()
        
        with self.knowledge_graph.driver.session() as session:
            session.run(
                """
                CREATE (o:Outreach {
                    id: $id,
                    query: $query,
                    status: 'pending',
                    created_at: datetime()
                })
                """,
                id=message_id,
                query=query
            )
            
            # Link outreach to gap documents
            for gap in gaps:
                session.run(
                    """
                    MATCH (o:Outreach), (d:Document)
                    WHERE o.id = $outreach_id AND d.id = $doc_id
                    CREATE (o)-[:CONCERNS]->(d)
                    """,
                    outreach_id=message_id,
                    doc_id=gap["id"]
                )
                
        return {
            "message_id": message_id,
            "status": "expert_input_requested"
        }
        
    def proactively_detect_gaps(self):
        """
        Proactively detect knowledge gaps and request expert input
        
        This would be run on a schedule (e.g., daily)
        """
        # Find all documents without tips
        gaps = self.knowledge_graph.find_knowledge_gaps()
        
        if not gaps:
            logging.info("No knowledge gaps detected")
            return []
            
        outreach_ids = []
        for gap in gaps:
            experts = self.knowledge_graph.find_experts_for_topic(gap["title"])
            
            if not experts:
                logging.warning(f"No experts found for topic: {gap['title']}")
                continue
                
            message_id = self.generate_message_id()
            outreach_ids.append(message_id)
            
            with self.knowledge_graph.driver.session() as session:
                session.run(
                    """
                    CREATE (o:Outreach {
                        id: $id,
                        topic: $topic,
                        status: 'pending',
                        created_at: datetime()
                    })
                    """,
                    id=message_id,
                    topic=gap["title"]
                )
                
                # Link outreach to document
                session.run(
                    """
                    MATCH (o:Outreach), (d:Document)
                    WHERE o.id = $outreach_id AND d.id = $doc_id
                    CREATE (o)-[:CONCERNS]->(d)
                    """,
                    outreach_id=message_id,
                    doc_id=gap["id"]
                )
                
                # Link outreach to experts
                for expert in experts:
                    session.run(
                        """
                        MATCH (o:Outreach), (e:Expert)
                        WHERE o.id = $outreach_id AND e.id = $expert_id
                        CREATE (o)-[:ASSIGNED_TO]->(e)
                        """,
                        outreach_id=message_id,
                        expert_id=expert["id"]
                    )
            
            logging.info(f"Created outreach {message_id} for document: {gap['title']}")
            
        return outreach_ids  # Fixed indentation and removed hidden characters
