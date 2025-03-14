from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import spacy
import numpy as np
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from pymongo import MongoClient
from datetime import datetime, timedelta
import bcrypt
import jwt
from config import Config
from functools import wraps


# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config.from_object(Config)

# MongoDB connection
client = MongoClient(Config.MONGO_URI)
db = client.knowledge_system

# Neo4j connection
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
username = os.getenv("NEO4J_USERNAME", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "password")
driver = GraphDatabase.driver(uri, auth=(username, password))

# Initialize NLP components
nlp = spacy.load("en_core_web_sm")
model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize Slack client for notifications
slack_token = os.getenv("SLACK_TOKEN")
slack_client = WebClient(token=slack_token) if slack_token else None
expert_channel = os.getenv("SLACK_EXPERT_CHANNEL", "#knowledge-experts")



def generate_token(user_id, role):
    expiration = datetime.utcnow() + timedelta(hours=Config.JWT_EXPIRATION_HOURS)
    return jwt.encode(
        {'user_id': str(user_id), 'role': role, 'exp': expiration},
        Config.SECRET_KEY,
        algorithm='HS256'
    )

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            token = token.split('Bearer ')[1]
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            current_user = db.users.find_one({'_id': data['user_id']})
            if not current_user:
                return jsonify({'message': 'Invalid token'}), 401
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'message': 'Invalid token'}), 401
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            token = token.split('Bearer ')[1]
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            if data['role'] != 'admin':
                return jsonify({'message': 'Admin privileges required'}), 403
            current_user = db.users.find_one({'_id': data['user_id']})
            if not current_user:
                return jsonify({'message': 'Invalid token'}), 401
            return f(current_user, *args, **kwargs)
        except Exception as e:
            return jsonify({'message': 'Invalid token'}), 401
    return decorated

# API Routes
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()

    if db.users.find_one({'email': data['email']}):
        return jsonify({'message': 'Email already registered'}), 400

    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())

    user = {
        'email': data['email'],
        'password': hashed_password,
        'name': data['name'],
        'role': data['role'],
        'created_at': datetime.utcnow()
    }

    if data['role'] == 'user' and 'field' in data:
        user['field'] = data['field']

    result = db.users.insert_one(user)
    token = generate_token(str(result.inserted_id), data['role'])

    return jsonify({
        'token': token,
        'user': {
            'id': str(result.inserted_id),
            'email': data['email'],
            'name': data['name'],
            'role': data['role'],
            'field': data.get('field')
        }
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = db.users.find_one({'email': data['email']})

    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    token = generate_token(str(user['_id']), user['role'])

    return jsonify({
        'token': token,
        'user': {
            'id': str(user['_id']),
            'email': user['email'],
            'name': user['name'],
            'role': user['role'],
            'field': user.get('field')
        }
    })


@app.route('/api/knowledge', methods=['POST'])
@token_required
def create_knowledge(current_user):
    data = request.get_json()
    knowledge = {
        'title': data['title'],
        'content': data['content'],
        'field': data['field'],
        'author_id': str(current_user['_id']),
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    result = db.knowledge.insert_one(knowledge)
    return jsonify({'message': 'Knowledge created', 'id': str(result.inserted_id)}), 201


@app.route('/api/knowledge', methods=['GET'])
@token_required
def search_knowledge(current_user):
    query = request.args.get('q', '')
    field = request.args.get('field', '')

    filter_query = {}
    if query:
        filter_query['$text'] = {'$search': query}
    if field:
        filter_query['field'] = field

    knowledge_items = list(db.knowledge.find(filter_query).sort('created_at', -1))
    for item in knowledge_items:
        item['_id'] = str(item['_id'])

    return jsonify(knowledge_items)


# @app.route('/api/knowledge/gaps', methods=['GET'])
# @admin_required
# def get_knowledge_gaps(current_user):
#     pipeline = [
#         {'$group': {
#             '_id': '$field',
#             'count': {'$sum': 1}
#         }},
#         {'$sort': {'count': 1}}
#     ]
#     gaps = list(db.knowledge.aggregate(pipeline))
#     return jsonify(gaps)
#



@app.route('/api/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query', '')
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
    try:
        # Generate embedding for the query
        query_embedding = model.encode(query)
        
        # Extract key entities from the query
        doc = nlp(query)
        entities = [ent.text.lower() for ent in doc.ents]
        keywords = [token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct]
        
        # Search for documents and tips in Neo4j
        results = search_knowledge_graph(query, query_embedding, entities, keywords)
        
        # Check for knowledge gaps
        gaps = identify_knowledge_gaps(query, entities, keywords)
        has_gaps = len(gaps) > 0
        
        # If gaps found, notify experts
        if has_gaps and slack_client:
            notify_experts_about_gaps(gaps, query)
        
        return jsonify({
            "results": results,
            "has_gaps": has_gaps,
            "gaps": gaps
        })
    
    except Exception as e:
        print(f"Error during search: {str(e)}")
        return jsonify({"error": "An error occurred during search"}), 500

@app.route('/api/gaps', methods=['GET'])
def get_knowledge_gaps():
    try:
        # Query Neo4j for documents without tips
        with driver.session() as session:
            result = session.run("""
                MATCH (d:Document) 
                WHERE NOT (d)-[:HAS_TIP]->() 
                RETURN d.title as topic, d.id as id
                LIMIT 10
            """)
            
            gaps = [{"topic": record["topic"], "id": record["id"]} for record in result]
            
        return jsonify(gaps)
    
    except Exception as e:
        print(f"Error fetching knowledge gaps: {str(e)}")
        return jsonify({"error": "An error occurred while fetching knowledge gaps"}), 500

@app.route('/api/tips', methods=['POST'])
def add_expert_tip():
    data = request.json
    document_id = data.get('document_id')
    tip_content = data.get('content')
    expert_id = data.get('expert_id')
    
    if not all([document_id, tip_content, expert_id]):
        return jsonify({"error": "Missing required fields"}), 400
    
    try:
        # Add tip to the knowledge graph
        with driver.session() as session:
            result = session.run("""
                MATCH (d:Document {id: $document_id})
                MATCH (e:Expert {id: $expert_id})
                CREATE (t:Tip {id: randomUUID(), content: $content, timestamp: datetime()})
                CREATE (d)-[:HAS_TIP]->(t)
                CREATE (e)-[:PROVIDED]->(t)
                RETURN t.id
            """, document_id=document_id, content=tip_content, expert_id=expert_id)
        tip_record = result.single()
        tip_id = tip_record["tip_id"] if tip_record else None
        return jsonify({"success": True, "tip_id":tip_id, "message": "Tip added successfully"})
    
    except Exception as e:
        print(f"Error adding expert tip: {str(e)}")
        return jsonify({"error": "An error occurred while adding the tip"}), 500
    
@app.route('/api/documents', methods=['POST'])
def add_document_endpoint():
    data = request.json
    title = data.get('title')
    content = data.get('content')
    doc_type = data.get('type')
    if not title or not content or not doc_type:
        return jsonify({"success": False, "error": "Missing required fields"}), 400
    
    # Create a KnowledgeGraph instance and add the document
    from knowlege_graph import KnowledgeGraph
    kg = KnowledgeGraph(uri, username, password)
    doc_id = kg.add_document(title, content, doc_type)
    kg.close()
    return jsonify({"success": True, "document_id": doc_id})

@app.route('/api/experts', methods=['POST'])
def add_expert_endpoint():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    expertise_areas = data.get('expertise_areas')
    if not name or not email or not expertise_areas:
        return jsonify({"success": False, "error": "Missing required fields"}), 400

    from knowlege_graph import KnowledgeGraph
    kg = KnowledgeGraph(uri, username, password)
    expert_id = kg.add_expert(name, email, expertise_areas)
    kg.close()
    return jsonify({"success": True, "expert_id": expert_id})


@app.route('/api/documents', methods=['GET'])
def get_documents():
    from knowlege_graph import KnowledgeGraph  # Make sure the spelling is correct!
    kg = KnowledgeGraph(uri, username, password)
    docs = kg.get_all_documents()
    kg.close()
    return jsonify(docs)

@app.route('/api/experts', methods=['GET'])
def get_experts():
    from knowlege_graph import KnowledgeGraph
    kg = KnowledgeGraph(uri, username, password)
    experts = kg.get_all_experts()
    kg.close()
    return jsonify(experts)

@app.route('/api/detect_gaps', methods=['POST'])
def detect_gaps_endpoint():
    try:
        # Here you can call your proactive gap detection function.
        # For now, we'll simulate a successful response.
        return jsonify({"success": True, "message": "Gap detection triggered"})
    except Exception as e:
        print(f"Error detecting gaps: {str(e)}")
        return jsonify({"error": "An error occurred during gap detection"}), 500


# Helper functions
def search_knowledge_graph(query, query_embedding, entities, keywords):
    # This is a simplified version - in a real implementation, you would:
    # 1. Use the embedding for semantic search
    # 2. Use entities and keywords for more targeted retrieval
    # 3. Combine results based on relevance scores
    
    with driver.session() as session:
        # Find documents relevant to the query
        result = session.run("""
            MATCH (d:Document)
            WHERE d.title CONTAINS $keyword OR d.content CONTAINS $keyword
            OPTIONAL MATCH (d)-[:HAS_TIP]->(t)<-[:PROVIDED]-(e:Expert)
            RETURN d.id as id, d.title as title, d.content as content, d.source as source,
                   collect({content: t.content, expert: e.name}) as tips
            ORDER BY size(tips) DESC
            LIMIT 10
        """, keyword=query.lower())
        
        docs = []
        for record in result:
            # In a real implementation, you would calculate actual semantic similarity scores
            # between query_embedding and document embeddings stored in Neo4j
            similarity_score = 0.7  # Placeholder score
            
            docs.append({
                "id": record["id"],
                "title": record["title"],
                "content": record["content"][:200] + "..." if len(record["content"]) > 200 else record["content"],
                "source": record["source"],
                "type": "Document",
                "score": similarity_score,
                "tips": [tip for tip in record["tips"] if tip["content"] is not None]
            })
    
    return docs

def identify_knowledge_gaps(query, entities, keywords):
    gaps = []
    
    with driver.session() as session:
        # Find documents related to the query that don't have expert tips
        for keyword in keywords:
            result = session.run("""
                MATCH (d:Document)
                WHERE (d.title CONTAINS $keyword OR d.content CONTAINS $keyword)
                AND NOT (d)-[:HAS_TIP]->()
                RETURN d.title as topic, d.id as id
                LIMIT 5
            """, keyword=keyword)
            
            for record in result:
                # Avoid duplicates
                if not any(gap["id"] == record["id"] for gap in gaps):
                    gaps.append({"topic": record["topic"], "id": record["id"]})
    
    return gaps

def notify_experts_about_gaps(gaps, query):
    if not slack_client:
        return
    
    try:
        # Create a message with the gaps
        gap_list = "\n".join([f"• {gap['topic']}" for gap in gaps[:5]])
        message = f"Knowledge Gaps Detected\nA user searched for: \"{query}\"\n\nThe following topics need expert input:\n{gap_list}"
        
        # Send message to the expert channel
        slack_client.chat_postMessage(
            channel=expert_channel,
            text=message,
            blocks=[
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": message}
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Add Expertise"},
                            "value": "add_tip",
                            "url": f"http://localhost:3000/expert?query={query}"  # Frontend expert page
                        }
                    ]
                }
            ]
        )
    except SlackApiError as e:
        print(f"Error sending Slack notification: {e.response['error']}")




if __name__ == '__main__':
    # Create text index for search
    db.knowledge.create_index([('title', 'text'), ('content', 'text')])
    app.run(debug=True,port=8080)