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
from Model.main1 import chat_with_ai
import markdown
import re
import requests
import json

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


@app.route('/api/user/knowledge/upload', methods=['POST'])
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
        results = search_knowledge_graph(search_query=query, query_embedding=query_embedding, entities=entities, keywords=keywords)
        
        # Prepare context for AI response
        context = {
            "query": query,
            "relevant_documents": results
        }
        
        # Get AI analysis with search role
        ai_response = chat_with_ai(query, context, system_role="search")
        
        # Check for knowledge gaps
        gaps = identify_knowledge_gaps(search_query=query, entities=entities, keywords=keywords)
        has_gaps = len(gaps) > 0

        if has_gaps and slack_client:
            notify_experts_about_gaps(gaps,query)
        
        return jsonify({
            "results": results,
            "ai_response": ai_response,
            "has_gaps": has_gaps,
            "gaps": gaps
        })
    
    except Exception as e:
        print(f"Error during search: {str(e)}")
        return jsonify({"error": "An error occurred during search"}), 500

@app.route('/api/gaps', methods=['GET'])
def get_knowledge_gaps():
    try:
        # Query Neo4j for existing topics
        with driver.session() as session:
            result = session.run("""
                MATCH (d:Document)
                RETURN DISTINCT 
                    d.title as topic,
                    d.keywords as keywords,
                    d.field as field,
                    d.id as id
                ORDER BY d.title
            """)
            
            topics_data = []
            for record in result:
                topics_data.append({
                    "topic": record["topic"],
                    "keywords": record["keywords"] if record["keywords"] else [],
                    "fields": [record["field"]] if record["field"] else [],
                    "id": record["id"]
                })
        
        # Format context for gap analysis
        context = {
            "topics": topics_data
        }
        
        # Use chat_with_ai with gap_analysis role
        analysis_prompt = """Based on the existing knowledge base topics and keywords, identify potential knowledge gaps 
        that should be covered. Consider industry standards, related topics, and prerequisite knowledge.
        For each gap, provide a clear topic and reason why it should be added."""
        
        # Get AI analysis with gap_analysis role
        gap_analysis = chat_with_ai(analysis_prompt, context, system_role="gap_analysis")
        
        try:
            # Parse the response
            gaps = json.loads(gap_analysis) if isinstance(gap_analysis, str) else gap_analysis
            if not isinstance(gaps, list):
                raise ValueError("Expected a list of gaps")
            
            # Validate and format gaps
            formatted_gaps = []
            markdown_content = ""
            for gap in gaps:
                if isinstance(gap, dict) and "topic" in gap and "reason" in gap:
                    formatted_gap = {
                        "topic": str(gap["topic"]),
                        "reason": str(gap["reason"])
                    }
                    formatted_gaps.append(formatted_gap)
                    # Create markdown content
                    markdown_content += f"### {formatted_gap['topic']}\n\n"
                    markdown_content += f"{formatted_gap['reason']}\n\n"
            
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_content, extensions=['extra', 'nl2br'])
            
            # Clean up the HTML
            html_content = re.sub(r'<p>\s*<br\s*/>\s*</p>', '', html_content)
            html_content = re.sub(r'\n+', '\n', html_content)
            
            return jsonify({
                "gaps": formatted_gaps,
                "html_content": html_content
            })
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing gap analysis: {str(e)}")
            error_html = markdown.markdown("### Analysis Error\n\nCould not analyze knowledge gaps. Please try again.")
            return jsonify({
                "gaps": [{"topic": "Analysis Error", "reason": "Could not analyze knowledge gaps. Please try again."}],
                "html_content": error_html
            })
    
    except Exception as e:
        print(f"Error in gap analysis: {str(e)}")
        error_html = markdown.markdown("### Error\n\nAn error occurred while analyzing knowledge gaps.")
        return jsonify({
            "error": "An error occurred while analyzing knowledge gaps",
            "html_content": error_html
        }), 500

@app.route('/api/detect_gaps', methods=['POST'])
@token_required
def detect_gaps_endpoint(current_user):
    try:
        data = request.get_json()
        specific_topic = data.get('topic', '')
        
        if not specific_topic:
            return jsonify({"error": "No topic specified"}), 400
            
        # Query Neo4j for existing topics related to the specific topic
        with driver.session() as session:
            result = session.run("""
                MATCH (d:Document)
                WHERE toLower(d.title) CONTAINS toLower($topic)
                   OR ANY(kw IN d.keywords WHERE toLower(kw) CONTAINS toLower($topic))
                RETURN DISTINCT 
                    d.title as topic,
                    d.keywords as keywords,
                    d.field as field,
                    d.id as id
                ORDER BY d.title
            """, topic=specific_topic)
            
            topics_data = []
            for record in result:
                topics_data.append({
                    "topic": record["topic"],
                    "keywords": record["keywords"] if record["keywords"] else [],
                    "fields": [record["field"]] if record["field"] else [],
                    "id": record["id"]
                })
        
        # Format context for gap analysis
        context = {
            "topic": specific_topic,
            "topics": topics_data
        }
        
        # Use chat_with_ai with topic_gap_analysis role
        analysis_prompt = f"""Analyze the knowledge base for gaps related to '{specific_topic}'.
        Consider prerequisites, related concepts, and practical applications.
        For each gap, provide a clear topic and reason why it should be added."""
        
        # Get AI analysis with topic_gap_analysis role
        gap_analysis = chat_with_ai(analysis_prompt, context, system_role="topic_gap_analysis")
        
        try:
            # Parse the response
            gaps = json.loads(gap_analysis) if isinstance(gap_analysis, str) else gap_analysis
            if not isinstance(gaps, list):
                raise ValueError("Expected a list of gaps")
            
            # Validate and format gaps
            formatted_gaps = []
            markdown_content = f"## Knowledge Gaps for {specific_topic}\n\n"
            for gap in gaps:
                if isinstance(gap, dict) and "topic" in gap and "reason" in gap:
                    formatted_gap = {
                        "topic": str(gap["topic"]),
                        "reason": str(gap["reason"])
                    }
                    formatted_gaps.append(formatted_gap)
                    # Create markdown content
                    markdown_content += f"### {formatted_gap['topic']}\n\n"
                    markdown_content += f"{formatted_gap['reason']}\n\n"
            
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_content, extensions=['extra', 'nl2br'])
            
            # Clean up the HTML
            html_content = re.sub(r'<p>\s*<br\s*/>\s*</p>', '', html_content)
            html_content = re.sub(r'\n+', '\n', html_content)
            
            return jsonify({
                "gaps": formatted_gaps,
                "html_content": html_content
            })
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error parsing gap analysis: {str(e)}")
            error_html = markdown.markdown(f"### Analysis Error\n\nCould not analyze gaps for {specific_topic}. Please try again.")
            return jsonify({
                "gaps": [{"topic": "Analysis Error", "reason": "Could not analyze gaps. Please try again."}],
                "html_content": error_html
            })
        
    except Exception as e:
        print(f"Error in gap detection: {str(e)}")
        error_html = markdown.markdown("### Error\n\nAn error occurred during gap detection.")
        return jsonify({
            "error": "An error occurred during gap detection",
            "html_content": error_html
        }), 500


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


@app.route('/api/experts', methods=['GET'])
def get_experts():
    from knowlege_graph import KnowledgeGraph
    kg = KnowledgeGraph(uri, username, password)
    experts = kg.get_all_experts()
    kg.close()
    return jsonify(experts)

@app.route('/api/chat', methods=['POST'])
def chat():
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
        
        # Search for relevant documents and summaries
        relevant_docs = search_knowledge_graph(search_query=query, query_embedding=query_embedding, entities=entities, keywords=keywords)
        
        # Format document information for AI context
        flattened_docs = []
        for title, docs in relevant_docs.items():
            for doc in docs:
                doc_info = {
                    "title": doc["title"],
                    "original_filename": doc["original_filename"],
                    "keywords": doc["keywords"] if doc["doc_type"] == "document" else [],
                    "matched_keywords": doc["matched_keywords"] if doc["doc_type"] == "document" else [],
                    "field": doc["field"],
                    "score": doc["score"],
                    "viewLink": doc["viewLink"],
                    "fileLink": doc["fileLink"],
                    "doc_type": doc["doc_type"],
                    "summary_content": doc.get("summary_content") if doc["doc_type"] == "summary" else None
                }
                flattened_docs.append(doc_info)
        
        # Sort documents by score
        flattened_docs.sort(key=lambda x: x["score"], reverse=True)
        
        # Prepare context for AI
        context = {
            "query": query,
            "relevant_documents": flattened_docs
        }
        
        # Get AI response with search role
        response = chat_with_ai(query, context, system_role="search")
        
        # Convert markdown to HTML
        html_response = markdown.markdown(response, extensions=['extra', 'nl2br'])
        
        # Clean up the HTML to ensure proper formatting
        html_response = re.sub(r'<p>\s*<br\s*/>\s*</p>', '', html_response)  # Remove empty paragraphs
        html_response = re.sub(r'\n+', '\n', html_response)  # Remove multiple newlines
        
        
        return jsonify({
            "response": html_response,
            "context": {
                "documents_found": len(flattened_docs),
                "relevant_topics": list(set(kw for doc in flattened_docs for kw in (doc["keywords"] if doc["doc_type"] == "document" else []))),
                "documents": flattened_docs
            },
            
        })
    
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({"error": "An error occurred during chat processing"}), 500
    

@app.route('/api/ai/generate-questions', methods=['POST'])
@token_required
def generate_questions(current_user):
    data = request.get_json()
    topic = data.get('topic')
    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({"error": "API key not configured"}), 500
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [{
            "parts": [{
                "text": f"Generate 10 important questions about {topic}. Format the response as a JSON array of strings, with each question as a separate string in the array. Do not include any other text or formatting."
            }]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Parse the response
        response_data = response.json()
        if 'candidates' in response_data and response_data['candidates']:
            generated_text = response_data['candidates'][0]['content']['parts'][0]['text']
            
            # Clean up the text to ensure it's valid JSON
            # Remove any markdown formatting or extra text
            json_str = generated_text.strip()
            if not json_str.startswith('['):
                # Try to find the JSON array in the text
                start_idx = json_str.find('[')
                end_idx = json_str.rfind(']')
                if start_idx != -1 and end_idx != -1:
                    json_str = json_str[start_idx:end_idx + 1]
            
            try:
                questions = json.loads(json_str)
                if isinstance(questions, list):
                    return jsonify({"questions": questions})
                else:
                    return jsonify({"questions": [str(questions)]})
            except json.JSONDecodeError as je:
                print(f"JSON decode error: {je}")
                # If JSON parsing fails, split by newlines and clean up
                questions = [q.strip().strip('*-').strip() for q in generated_text.split('\n') if q.strip()]
                return jsonify({"questions": questions})
        
        return jsonify({"error": "No questions generated"}), 500
    except Exception as e:
        print(f"Error generating questions: {e}")
        return jsonify({"error": "Failed to generate questions"}), 500

@app.route('/api/ai/summarize-chat', methods=['POST'])
@token_required
def summarize_chat(current_user):
    data = request.get_json()
    conversation = data.get('conversation')
    topic = data.get('topic')
    
    if not conversation or not topic:
        return jsonify({"error": "Conversation and topic are required"}), 400

    # Format conversation for the prompt
    conversation_text = "\n".join(
        [f"Q: {item['question']}\nA: {item['answer']}" for item in conversation]
    )

    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return jsonify({"error": "API key not configured"}), 500

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    
    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "contents": [{
            "parts": [{
                "text": f"""Please provide a comprehensive summary of this conversation about {topic}.
                Focus on the key points discussed and insights shared. If any questions were skipped,
                provide a summary of the conversation.

                Conversation:
                {conversation_text}

                Please format the summary in clear paragraphs with proper spacing."""
            }]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Parse the response
        response_data = response.json()
        if 'candidates' in response_data and response_data['candidates']:
            summary = response_data['candidates'][0]['content']['parts'][0]['text']
            
            # Store the summary as a Summary node
            try:
                from knowlege_graph import KnowledgeGraph
                kg = KnowledgeGraph(uri, username, password)
                summary_id = kg.add_chat_summary(
                    topic=topic,
                    summary=summary,
                    author_id=str(current_user['_id']),
                    author_name=current_user['name']
                )
                kg.close()
            except Exception as e:
                print(f"Error storing summary in knowledge graph: {e}")
                # Continue even if storage fails
                summary_id = None

            return jsonify({
                "summary": summary,
                "summary_id": summary_id
            })
        
        return jsonify({"error": "No summary generated"}), 500
        
    except requests.exceptions.RequestException as e:
        print(f"Error calling Gemini API: {e}")
        return jsonify({"error": "Failed to generate summary"}), 500
    except Exception as e:
        print(f"Unexpected error during summarization: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@app.route('/api/recommendations', methods=['GET'])
@token_required
def get_recommendations(current_user):
    """
    Fetch recommended documents from Neo4j based on the user's learning field.
    """
    try:
        user_field = current_user.get('field')
        if not user_field:
            return jsonify({"message": "User does not have a learning field set"}), 400

        from knowlege_graph import KnowledgeGraph
        kg = KnowledgeGraph(uri, username, password)
        recommended_docs = kg.get_documents_for_field(user_field)
        kg.close()

        return jsonify({"recommendations": recommended_docs}), 200
    except Exception as e:
        print(f"Error fetching recommendations: {e}")
        return jsonify({"error": "Failed to fetch recommendations"}), 500



# Helper functions
def search_knowledge_graph(search_query, query_embedding, entities, keywords):
    try:
        with driver.session() as session:
            # Create Cypher query to match documents and summaries
            cypher_query = """
            // First match documents
            MATCH (d:Document)
            WHERE 
                toLower(d.title) CONTAINS toLower($search_query)
                OR
                toLower(d.original_filename) CONTAINS toLower($search_query)
                OR
                ANY(keyword IN d.keywords 
                    WHERE ANY(search_term IN $search_terms 
                        WHERE toLower(keyword) CONTAINS toLower(search_term)))
            WITH d, 
                CASE 
                    WHEN toLower(d.title) CONTAINS toLower($search_query) THEN 2
                    WHEN toLower(d.original_filename) CONTAINS toLower($search_query) THEN 1.5
                    ELSE 0
                END +
                size([keyword IN d.keywords 
                    WHERE ANY(search_term IN $search_terms 
                        WHERE toLower(keyword) CONTAINS toLower(search_term))]) as matching_count,
                'document' as type
            RETURN 
                d.id as id,
                d.title as title,
                d.fileLink as fileLink,
                d.keywords as keywords,
                d.field as field,
                d.meme_type as meme_type,
                d.filename as filename,
                d.original_filename as original_filename,
                d.fileLink as viewLink,
                d.keywords as matched_keywords,
                toFloat(matching_count) / (2 + size($search_terms)) as relevance_score,
                d.author_name as author,
                toString(d.created_at) as created_at,
                type as doc_type,
                null as summary_content

            UNION ALL

            // Match summaries
            MATCH (s:Summary)
            WHERE 
                toLower(s.topic) CONTAINS toLower($search_query)
                OR
                toLower(s.content) CONTAINS toLower($search_query)
            WITH s, 
                CASE 
                    WHEN toLower(s.topic) CONTAINS toLower($search_query) THEN 2
                    WHEN toLower(s.content) CONTAINS toLower($search_query) THEN 1
                    ELSE 0
                END as matching_count,
                'summary' as type
            RETURN 
                s.id as id,
                s.topic as title,
                null as fileLink,
                [] as keywords,
                s.field as field,
                'text/plain' as meme_type,
                null as filename,
                'Chat Summary' as original_filename,
                null as viewLink,
                [] as matched_keywords,
                toFloat(matching_count) / (2 + size($search_terms)) as relevance_score,
                s.author_name as author,
                toString(s.created_at) as created_at,
                type as doc_type,
                s.content as summary_content

            ORDER BY relevance_score DESC
            """
            
            # Combine all search terms
            search_terms = set([search_query] + keywords + entities)
            
            # Execute the query
            result = session.run(cypher_query, {
                'search_query': search_query,
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
                        "viewLink": record["viewLink"],
                        "keywords": record["keywords"],
                        "matched_keywords": record["matched_keywords"],
                        "field": record["field"],
                        "meme_type": record["meme_type"],
                        "filename": record["filename"],
                        "original_filename": record["original_filename"],
                        "score": record["relevance_score"],
                        "author": record["author"],
                        "created_at": record["created_at"],
                        "doc_type": record["doc_type"],
                        "summary_content": record["summary_content"]
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

def identify_knowledge_gaps(search_query, entities, keywords):
    try:
        with driver.session() as session:
            # Find documents related to the query
            cypher_query = """
            MATCH (d:Document)
            WHERE 
                toLower(d.title) CONTAINS toLower($search_query)
                OR
                ANY(keyword IN d.keywords 
                    WHERE ANY(search_term IN $search_terms 
                        WHERE toLower(keyword) CONTAINS toLower(search_term)))
            RETURN DISTINCT d.title as topic, d.id as id
            LIMIT 5
            """
            
            # Combine all search terms
            search_terms = set([search_query] + keywords + entities)
            
            result = session.run(cypher_query, {
                'search_query': search_query,
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