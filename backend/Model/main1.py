from transformers import pipeline
import torch
import json

modelPath = "D:\\Projects\\KAI-Project\\KAI-Project\\backend\\Model"

pipe = pipeline(
    "text-generation",
    model=modelPath,
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Predefined system contexts for different use cases
SYSTEM_CONTEXTS = {
    "search": (
        "You are an advanced AI designed to guide users to find the best knowledge from the given text documents. "
        "When responding, focus on the topics and keywords from the relevant documents in our knowledge base. "
        "If relevant documents are found, reference them in your response and explain how they relate to the user's query. "
        "Keep your responses well-structured and use appropriate formatting."
        "If the user asks unrelevant question, just say 'I'm sorry, I can't answer that question.'"
    ),
    "gap_analysis": (
        "You are an AI expert in analyzing knowledge gaps and identifying missing topics in educational content. "
        "Your task is to analyze the existing knowledge base and identify potential gaps that should be addressed. "
        "Consider industry standards, prerequisites, related concepts, and practical applications. "
        "Format your response as a JSON array of objects with 'topic' and 'reason' fields. "
        "Each topic should be specific and actionable, and each reason should explain why this topic is important and how it relates to existing content."
    ),
    "topic_gap_analysis": (
        "You are an AI expert in analyzing specific topics for knowledge gaps. "
        "Your task is to analyze the given topic and identify related concepts or subtopics that should be covered. "
        "Consider prerequisites, practical applications, and industry best practices. "
        "Format your response as a JSON array of objects with 'topic' and 'reason' fields. "
        "Focus on specific, actionable topics that would enhance understanding of the main subject."
    )
}

def format_document_context(context):
    if not context.get("relevant_documents"):
        return "No relevant documents found in the knowledge base."
    
    # Sort documents by score
    sorted_docs = sorted(context["relevant_documents"], key=lambda x: x["score"], reverse=True)
    
    # Create a summary of available topics
    topics = set()
    for doc in sorted_docs:
        if doc["doc_type"] == "document" and doc.get("keywords"):
            topics.update(doc["keywords"])
    
    context_text = "Based on our knowledge base, I can provide information about the following topics:\n"
    
    # Add document summaries
    for i, doc in enumerate(sorted_docs[:3], 1):  # Show top 3 most relevant documents
        context_text += f"\n{i}. {'Document' if doc['doc_type'] == 'document' else 'Summary'}: '{doc['title']}'\n"
        context_text += f"   Field: {doc.get('field', 'N/A')}\n"
        if doc["doc_type"] == "document" and doc.get("keywords"):
            context_text += f"   Keywords: {', '.join(doc['keywords'])}\n"
            if doc.get('matched_keywords'):
                context_text += f"   Matched terms: {', '.join(doc['matched_keywords'])}\n"
        elif doc["doc_type"] == "summary" and doc.get("summary_content"):
            context_text += f"   Type: Chat Summary\n"
    
    return context_text

def chat_with_ai(prompt, context=None, system_role="search"):
    try:
        # Get the appropriate system context
        system_content = SYSTEM_CONTEXTS.get(system_role, SYSTEM_CONTEXTS["search"])
        
        # Add context information if available
        if context:
            if system_role == "search" and "relevant_documents" in context:
                system_content += "\n\nAvailable context from knowledge base:\n" + format_document_context(context)
            elif system_role in ["gap_analysis", "topic_gap_analysis"]:
                # For gap analysis, format the topics data
                if "topics" in context:
                    topics_info = "\n\nExisting topics and their information:\n"
                    for topic in context["topics"]:
                        topics_info += f"\nTopic: {topic['topic']}"
                        if topic.get('keywords'):
                            topics_info += f"\nKeywords: {', '.join(topic['keywords'])}"
                        if topic.get('fields'):
                            topics_info += f"\nFields: {', '.join(topic['fields'])}"
                        topics_info += "\n"
                    system_content += topics_info
                if "topic" in context:  # For specific topic analysis
                    system_content += f"\n\nAnalyzing gaps for specific topic: {context['topic']}"
        
        messages = [
            {
                "role": "system",
                "content": system_content
            },
            {"role": "user", "content": prompt},
        ]

        # Generate response
        response = pipe(
            messages,
            max_new_tokens=500,
            num_return_sequences=1,
            temperature=0.7,
            pad_token_id=pipe.tokenizer.eos_token_id,
            do_sample=True,
            top_p=0.9
        )
        
        # Extract the generated text and clean it
        generated_text = response[0]['generated_text'][-1]['content']
        
        # Clean up duplicate text and format
        cleaned_text = generated_text.strip()
        # Remove any duplicate sentences that might appear
        sentences = cleaned_text.split('. ')
        unique_sentences = []
        for sentence in sentences:
            if sentence not in unique_sentences:
                unique_sentences.append(sentence)
        cleaned_text = '. '.join(unique_sentences)

        # For gap analysis, try to ensure JSON format
        if system_role in ["gap_analysis", "topic_gap_analysis"]:
            try:
                # Try to find JSON array in the response
                start_idx = cleaned_text.find('[')
                end_idx = cleaned_text.rfind(']')
                if start_idx != -1 and end_idx != -1:
                    json_str = cleaned_text[start_idx:end_idx + 1]
                    # Validate JSON format
                    json.loads(json_str)
                    return json_str
                else:
                    # Fallback: Format as JSON array
                    lines = cleaned_text.split('\n')
                    gaps = []
                    current_gap = {}
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('Topic:'):
                            if current_gap and 'topic' in current_gap:
                                gaps.append(current_gap)
                            current_gap = {'topic': line.replace('Topic:', '').strip()}
                        elif line.startswith('Reason:'):
                            if current_gap:
                                current_gap['reason'] = line.replace('Reason:', '').strip()
                    
                    if current_gap and 'topic' in current_gap:
                        gaps.append(current_gap)
                    
                    if not gaps:
                        # If no structured format found, create a single gap entry
                        gaps = [{
                            'topic': 'General Gap',
                            'reason': cleaned_text
                        }]
                    
                    return json.dumps(gaps)
            except json.JSONDecodeError:
                # If JSON parsing fails, create a structured response
                return json.dumps([{
                    'topic': 'Analysis Result',
                    'reason': cleaned_text
                }])
        
        # For search queries, add reference section if we have relevant documents
        if system_role == "search" and context and context.get("relevant_documents"):
            cleaned_text += '\n<div class="references">'
            cleaned_text += '\n<p><strong>Related Documents:</strong></p>'
            cleaned_text += '\n<ul>'
            for doc in sorted(context["relevant_documents"], key=lambda x: x["score"], reverse=True)[:3]:
                cleaned_text += f'\n<li><a href="{doc.get("viewLink", "#")}" target="_blank">{doc["title"]}</a> (Field: {doc["field"]})</li>'
            cleaned_text += '\n</ul></div>'
        
        return cleaned_text if cleaned_text else "I'm sorry, I can't answer that question."
        
    except Exception as e:
        print(f"Error in chat function: {str(e)}")
        return json.dumps([{
            'topic': 'Error',
            'reason': 'An error occurred while analyzing the knowledge base. Please try again.'
        }]) if system_role in ["gap_analysis", "topic_gap_analysis"] else "I apologize, but I encountered an error. Please try again."

# if __name__ == "__main__":
#     while True:
#         user_input = input("You: ")
#         if user_input.lower() in ["exit", "quit"]:
#             break
#         response = chat(user_input)
#         print(f"AI: {response}")

# outputs = pipe(
#     messages,
#     max_new_tokens=256,
# )
# response = outputs[0]["generated_text"][-1]

# print(response)

# with open('output.txt','w',encoding="utf-8") as text_file:
#     text_file.write(response['content'])