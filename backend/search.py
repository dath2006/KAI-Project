from sentence_transformers import SentenceTransformer, util
import torch
import logging

class SemanticSearch:
    def __init__(self):  # Fixed the constructor name
        """
        Initialize the semantic search with a pre-trained model
        """
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logging.info("Semantic search model loaded")

    def search(self, query, knowledge_graph, top_k=5):
        """
        Perform semantic search on documents and tips
        
        Args:
            query: The search query string
            knowledge_graph: KnowledgeGraph instance
            top_k: Number of top results to return
            
        Returns:
            dict with search results and gap information
        """
        # Get all documents with tips
        documents = knowledge_graph.get_all_documents()

        # Create a list of all content to search through
        search_items = []
        for doc in documents:
            # Add document title and its ID
            search_items.append({
                "id": doc["id"],
                "type": "document",
                "text": doc["title"],
                "doc_id": doc["id"]
            })
            
            # Add tips and their IDs
            for tip in doc["tips"]:
                search_items.append({
                    "id": tip["tip_id"],
                    "type": "tip",
                    "text": tip["text"],
                    "doc_id": doc["id"],
                    "expert": tip["expert_name"]
                })
                
        # If there's nothing to search, return empty results
        if not search_items:
            return {"results": [], "has_gaps": False, "gaps": []}

        # Encode the query and all search items
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        corpus_embeddings = self.model.encode([item["text"] for item in search_items], convert_to_tensor=True)

        # Compute similarity scores
        cos_scores = util.cos_sim(query_embedding, corpus_embeddings)[0]

        # Get top-k results
        top_results_indices = torch.topk(cos_scores, min(top_k, len(search_items))).indices.tolist()

        # Check if we have any low-scoring results (potential knowledge gaps)
        threshold = 0.3  # Similarity threshold
        has_gaps = any(cos_scores[i].item() < threshold for i in top_results_indices)

        # Prepare results
        results = []
        for idx in top_results_indices:
            item = search_items[idx]
            score = cos_scores[idx].item()

            results.append({
                "id": item["id"],
                "type": item["type"],
                "text": item["text"],
                "doc_id": item["doc_id"],
                "score": score,
                "expert": item.get("expert", None) if item["type"] == "tip" else None
            })

        # Find documents without tips (knowledge gaps)
        gap_docs = knowledge_graph.find_knowledge_gaps()

        return {
            "results": results,
            "has_gaps": has_gaps or len(gap_docs) > 0,
            "gaps": gap_docs
        }  # Fixed indentation and removed invalid characters
