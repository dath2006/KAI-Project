from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import spacy
import numpy as np
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from datetime import datetime, timedelta
import bcrypt
import jwt
from config import Config
from functools import wraps
from bson import ObjectId
from pdf_processor import process_pdf
import asyncio

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

# File upload configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'md', 'ppt', 'pptx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

async def file_process(file_path):
    metadata_result = await process_pdf(file_path)
    return metadata_result

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            # Extract token from "Bearer <token>"
            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
            
            # Decode token
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            
            # Convert string ID to ObjectId for MongoDB query
            user_id = ObjectId(payload['user_id'])
            current_user = db.users.find_one({'_id': user_id})
            
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
                
            # Convert ObjectId to string for JSON serialization
            current_user['_id'] = str(current_user['_id'])
            return f(current_user, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'message': str(e)}), 401
            
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            # Extract token from "Bearer <token>"
            token = auth_header.split(' ')[1] if auth_header.startswith('Bearer ') else auth_header
            
            # Decode token
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
            
            if payload['role'] != 'admin':
                return jsonify({'message': 'Admin privileges required'}), 403
                
            # Convert string ID to ObjectId for MongoDB query
            user_id = ObjectId(payload['user_id'])
            current_user = db.users.find_one({'_id': user_id})
            
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
                
            # Convert ObjectId to string for JSON serialization
            current_user['_id'] = str(current_user['_id'])
            return f(current_user, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401
        except Exception as e:
            return jsonify({'message': str(e)}), 401
            
    return decorated

# API Routes
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    data = request.get_json()
    
    if db.users.find_one({'email': data['email']}):
        return jsonify({'message': 'Email already registered'}), 400
    
    hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
    
    user = {
        '_id': ObjectId(),
        'email': data['email'],
        'password': hashed_password,
        'name': data['name'],
        'role': data['role'],
        'created_at': datetime.utcnow()
    }
    
    if data['role'] == 'user' and 'field' in data:
        user['field'] = data['field']
    
    db.users.insert_one(user)
    
    # Generate token
    token = generate_token(user['_id'], data['role'])
    
    # Convert ObjectId to string for response
    user['_id'] = str(user['_id'])
    del user['password']  # Remove password from response
    
    return jsonify({
        'token': token,
        'user': user
    }), 201


@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = db.users.find_one({'email': data['email']})
    
    if not user or not bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
    
    # Generate token
    token = generate_token(user['_id'], user['role'])
    
    # Convert ObjectId to string and remove password for response
    user_response = {
        'id': str(user['_id']),
        'email': user['email'],
        'name': user['name'],
        'role': user['role'],
        'field': user.get('field')
    }
    
    return jsonify({
        'token': token,
        'user': user_response
    })


@app.route('/api/knowledge/upload', methods=['POST'])
@token_required
def upload_knowledge(current_user):     
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided'}), 400
    
    file = request.files['file']
    topic = request.form.get('topic')
    
    if not file or not topic:
        return jsonify({'message': 'File and topic are required'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'message': 'File type not allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Process the file
        try:
            metadata_result = asyncio.run(file_process(file_path))
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            metadata_result = {
                'keywords': [],
                'fileLink': file_path,
                'meme_type': file.content_type
            }

        knowledge = {
            'title': topic,
            'filename': unique_filename,
            'original_filename': filename,
            'author_id': str(current_user['_id']),
            'author_name': current_user['name'],
            'field': current_user.get('field'),
            'keywords': metadata_result.get('keywords', []),
            'fileLink': metadata_result.get('fileLink', file_path),
            'meme_type': metadata_result.get('meme_type', file.content_type),
            'created_at': datetime.utcnow()
        }
        
        # Add to knowledge graph
        try:
            from knowlege_graph import KnowledgeGraph
            kg = KnowledgeGraph(uri, username, password)
            doc_id = kg.add_document(knowledge)
            kg.close()
        except Exception as e:
            print(f"Error adding to knowledge graph: {str(e)}")
            return jsonify({'message': 'Error adding to knowledge graph', 'error': str(e)}), 500
        
        return jsonify({
            'message': 'File uploaded successfully',
            'document_id': doc_id,
            'metadata': metadata_result
        }), 201
        
    except Exception as e:
        print(f"Error in file upload: {str(e)}")
        return jsonify({'message': 'Error uploading file', 'error': str(e)}), 500

@app.route('/api/admin/knowledge/upload', methods=['POST'])
@admin_required
def admin_upload_knowledge(current_user):
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided'}), 400
    
    file = request.files['file']
    topic = request.form.get('topic')
    
    if not file or not topic:
        return jsonify({'message': 'File and topic are required'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'message': 'File type not allowed'}), 400
    
    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(file_path)
        
        # Process the file
        try:
            metadata_result = asyncio.run(file_process(file_path))
        except Exception as e:
            print(f"Error processing file: {str(e)}")
            metadata_result = {
                'keywords': [],
                'fileLink': file_path,
                'meme_type': file.content_type
            }

        knowledge = {
            'title': topic,
            'filename': unique_filename,
            'original_filename': filename,
            'author_id': str(current_user['_id']),
            'author_name': current_user['name'],
            'field': current_user.get('field'),
            'keywords': metadata_result.get('keywords', []),
            'fileLink': metadata_result.get('fileLink', file_path),
            'meme_type': metadata_result.get('meme_type', file.content_type),
            'is_admin_content': True,
            'created_at': datetime.utcnow()
        }
        
        # Add to knowledge graph
        try:
            from knowlege_graph import KnowledgeGraph
            kg = KnowledgeGraph(uri, username, password)
            doc_id = kg.add_document(knowledge)
            kg.close()
        except Exception as e:
            print(f"Error adding to knowledge graph: {str(e)}")
            return jsonify({'message': 'Error adding to knowledge graph', 'error': str(e)}), 500
        
        return jsonify({
            'message': 'File uploaded successfully',
            'document_id': doc_id,
            'metadata': metadata_result
        }), 201
        
    except Exception as e:
        print(f"Error in file upload: {str(e)}")
        return jsonify({'message': 'Error uploading file', 'error': str(e)}), 500


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

@app.route('/api/uploads/<filename>')
@token_required
def get_file(current_user, filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


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
        # if has_gaps and slack_client:
        #     notify_experts_about_gaps(gaps, query)
        
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

@app.route('/api/ai/generate-questions', methods=['POST'])
@token_required  # Only authenticated users can generate questions
def generate_questions(current_user):
    data = request.get_json()
    topic = data.get('topic')
    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    # Call Gemini AI API to generate questions
    # Replace the URL and parameters with the actual Gemini API endpoint details
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={os.getenv('GEMINI_API_KEY')}"  # Example URL; update as needed
    headers = {
        "Authorization": f"Bearer {os.getenv('GEMINI_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": f"Generate 10 important questions about {topic}.",
        "max_tokens": 200  # Adjust as needed
    }
    try:
        response = requests.post(gemini_url, headers=headers, json=payload)
        response.raise_for_status()
        questions = response.json().get("questions")
        if not questions:
            return jsonify({"error": "No questions generated"}), 500
        return jsonify({"questions": questions})
    except Exception as e:
        print(f"Error generating questions: {e}")
        return jsonify({"error": "Failed to generate questions"}), 500
    
@app.route('/api/ai/summarize-chat', methods=['POST'])
@token_required  # Only authenticated users can summarize chat
def summarize_chat(current_user):
    data = request.get_json()
    conversation = data.get('conversation')  # Expecting an array of Q&A objects
    topic = data.get('topic')
    if not conversation or not topic:
        return jsonify({"error": "Conversation and topic are required"}), 400

    # Prepare prompt for summarization
    # For example, "Summarize the following conversation on [topic]: ..."
    conversation_text = "\n".join(
        [f"Q: {item['question']}\nA: {item['answer']}" for item in conversation]
    )
    prompt = f"Summarize the following conversation on {topic} into a detailed summary:\n{conversation_text}"

    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={os.getenv('GEMINI_API_KEY')}"  # Example URL; update as needed
    headers = {
        "Authorization": f"Bearer {os.getenv('GEMINI_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "max_tokens": 300  # Adjust as needed for a detailed summary
    }
    try:
        response = requests.post(gemini_url, headers=headers, json=payload)
        response.raise_for_status()
        summary = response.json().get("summary")
        if not summary:
            return jsonify({"error": "No summary generated"}), 500

        # Store the summary in Neo4j as a ChatSummary document
        from knowledge_graph import KnowledgeGraph
        kg = KnowledgeGraph(uri, username, password)
        summary_doc_id = kg.add_document(
            title=f"Chat Summary for {topic}",
            content=summary,
            doc_type="ChatSummary"
        )
        kg.close()

        return jsonify({"summary": summary, "document_id": summary_doc_id})
    except Exception as e:
        print(f"Error summarizing chat: {e}")
        return jsonify({"error": "Failed to summarize chat"}), 500




# Helper functions
def search_knowledge_graph(query, query_embedding, entities, keywords):
    try:
        with driver.session() as session:
            # Create Cypher query to match documents
            cypher_query = """
            MATCH (d:Document)
            WHERE 
                // First check if query matches title (case-insensitive)
                toLower(d.title) CONTAINS toLower($query)
                OR
                // Then check if query matches original filename (case-insensitive)
                toLower(d.original_filename) CONTAINS toLower($query)
                OR
                // Then check if any of the search terms match with keywords array
                ANY(keyword IN d.keywords 
                    WHERE ANY(search_term IN $search_terms 
                        WHERE toLower(keyword) CONTAINS toLower(search_term)))
            WITH d, 
                // Calculate relevance score based on matches
                CASE 
                    WHEN toLower(d.title) CONTAINS toLower($query) THEN 2  // Title match gets higher score
                    WHEN toLower(d.original_filename) CONTAINS toLower($query) THEN 1.5  // Filename match gets medium score
                    ELSE 0
                END +
                size([keyword IN d.keywords 
                    WHERE ANY(search_term IN $search_terms 
                        WHERE toLower(keyword) CONTAINS toLower(search_term))]) as matching_count
            RETURN 
                d.id as id,
                d.title as title,
                d.fileLink as fileLink,
                d.keywords as keywords,
                d.field as field,
                d.meme_type as meme_type,
                d.filename as filename,
                d.original_filename as original_filename,
                [keyword IN d.keywords 
                    WHERE ANY(search_term IN $search_terms 
                        WHERE toLower(keyword) CONTAINS toLower(search_term))] as matched_keywords,
                toFloat(matching_count) / (2 + size($search_terms)) as relevance_score,
                d.author_name as author,
                toString(d.created_at) as created_at
            ORDER BY relevance_score DESC
            """
            
            # Combine all search terms
            search_terms = set([query] + keywords + entities)
            
            # Execute the query
            result = session.run(cypher_query, {
                'query': query,
                'search_terms': list(search_terms)
            })
            
            # Process results and group by title
            grouped_documents = {}
            for record in result:
                try:
                    doc = {
                        "id": record["id"],
                        "title": record["title"],
                        "fileLink": record["fileLink"],
                        "keywords": record["keywords"],
                        "matched_keywords": record["matched_keywords"],
                        "field": record["field"],
                        "meme_type": record["meme_type"],
                        "filename": record["filename"],
                        "original_filename": record["original_filename"],
                        "score": record["relevance_score"],
                        "author": record["author"],
                        "created_at": record["created_at"]
                    }
                    
                    if doc["title"] not in grouped_documents:
                        grouped_documents[doc["title"]] = []
                    grouped_documents[doc["title"]].append(doc)
                    
                except Exception as e:
                    print(f"Error processing record: {str(e)}")
                    continue
            
            return grouped_documents
            
    except Exception as e:
        print(f"Error in search_knowledge_graph: {str(e)}")
        return {}

def identify_knowledge_gaps(query, entities, keywords):
    try:
        with driver.session() as session:
            # Find documents related to the query
            cypher_query = """
            MATCH (d:Document)
            WHERE 
                toLower(d.title) CONTAINS toLower($query)
                OR
                ANY(keyword IN d.keywords 
                    WHERE ANY(search_term IN $search_terms 
                        WHERE toLower(keyword) CONTAINS toLower(search_term)))
            RETURN DISTINCT d.title as topic, d.id as id
            LIMIT 5
            """
            
            # Combine all search terms
            search_terms = set([query] + keywords + entities)
            
            result = session.run(cypher_query, {
                'query': query,
                'search_terms': list(search_terms)
            })
            
            gaps = []
            for record in result:
                if not any(gap["id"] == record["id"] for gap in gaps):
                    gaps.append({
                        "topic": record["topic"],
                        "id": record["id"]
                    })
            
            return gaps
            
    except Exception as e:
        print(f"Error in identify_knowledge_gaps: {str(e)}")
        return []

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