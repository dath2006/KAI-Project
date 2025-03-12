import unittest
import json
import sys
import os

# Add the parent directory to the path so we can import our app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from knowlege_graph import KnowledgeGraph  # Ensure this import is correct
from search import SemanticSearch
from chatbot import Chatbot

class TestKAIApp(unittest.TestCase):
    def setUp(self):
        """
        Set up test client and test database
        """
        app.config['TESTING'] = True
        self.client = app.test_client()
        
    def tearDown(self):
        """
        Clean up after tests
        """
        pass
        
    def test_document_endpoints(self):
        """
        Test document creation and retrieval
        """
        response = self.client.post('/api/documents', 
                                    data=json.dumps({
                                        'title': 'Test Document',
                                        'content': 'This is a test document content',
                                        'type': 'pdf'
                                    }),
                                    content_type='application/json')
        
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('document_id', data)
        
        response = self.client.get('/api/documents')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(data, list)
        
    def test_expert_endpoints(self):
        """
        Test expert creation and retrieval
        """
        response = self.client.post('/api/experts', 
                                    data=json.dumps({
                                        'name': 'Jane Doe',
                                        'email': 'jane@example.com',
                                        'expertise_areas': ['Python', 'Data Science', 'Machine Learning']
                                    }),
                                    content_type='application/json')
        
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('expert_id', data)
        
        response = self.client.get('/api/experts')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(data, list)
        
    def test_tip_creation(self):
        """
        Test creating a tip
        """
        doc_response = self.client.post('/api/documents', 
                                   data=json.dumps({
                                       'title': 'Document for Tip Test',
                                       'content': 'This is a test document for tips',
                                       'type': 'pdf'
                                   }),
                                   content_type='application/json')
        doc_data = json.loads(doc_response.data)
        doc_id = doc_data['document_id']
        
        expert_response = self.client.post('/api/experts', 
                                     data=json.dumps({
                                         'name': 'John Expert',
                                         'email': 'john@example.com',
                                         'expertise_areas': ['Testing', 'Documentation']
                                     }),
                                     content_type='application/json')
        expert_data = json.loads(expert_response.data)
        expert_id = expert_data['expert_id']
        
        response = self.client.post('/api/tips', 
                               data=json.dumps({
                                   'text': 'This is a test tip from an expert',
                                   'document_id': doc_id,
                                   'expert_id': expert_id
                               }),
                               content_type='application/json')
        
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('tip_id', data)
        
    def test_search(self):
        """
        Test search functionality
        """
        self.client.post('/api/documents', 
                      data=json.dumps({
                          'title': 'Search Test Document',
                          'content': 'This is a document about search technology',
                          'type': 'pdf'
                      }),
                      content_type='application/json')
        
        response = self.client.post('/api/search', 
                                data=json.dumps({
                                    'query': 'search technology'
                                }),
                                content_type='application/json')
        
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', data)
        
    def test_gap_detection(self):
        """
        Test knowledge gap detection
        """
        self.client.post('/api/documents', 
                      data=json.dumps({
                          'title': 'Gap Test Document',
                          'content': 'This document has no tips yet',
                          'type': 'pdf'
                      }),
                      content_type='application/json')
        
        response = self.client.get('/api/gaps')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)
        
        response = self.client.post('/api/detect_gaps')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])

if __name__ == '__main__':
    unittest.main()
