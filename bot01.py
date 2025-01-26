import os
import torch
import faiss
import numpy as np
from flask import Flask, request, jsonify
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

app = Flask(__name__)

# Folder containing the documents
DOCUMENTS_FOLDER = "scraped_data/"  # Replace with the path to your folder

# Base URL for IHEC Carthage (no longer used for file paths)
# BASE_URL = "https://ihec.rnu.tn/"  # This can be removed if not needed elsewhere

# 1) Load embeddings model (Sentence Transformers)
embed_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

# 2) Prepare data from the folder
doc_texts = []
# Removed pdf_links_array as PDF links are not applicable anymore
# Removed urls_array as URLs are not applicable anymore

# Read all files in the folder
for filename in os.listdir(DOCUMENTS_FOLDER):
    file_path = os.path.join(DOCUMENTS_FOLDER, filename)
    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            doc_texts.append(content)
            # Removed pdf_links_array and urls_array append operations

# 3) Compute embeddings for each doc
doc_embeddings = embed_model.encode(doc_texts, convert_to_numpy=True)

# 4) Build FAISS index
dimension = doc_embeddings.shape[1]
faiss_index = faiss.IndexFlatL2(dimension)
faiss_index.add(doc_embeddings)

# 5) Load local LLM for generating final answers
model_name = "google/flan-t5-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
gen_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

def get_top_k_docs(query, k=3):
    """Return top-k relevant documents from the FAISS index."""
    query_vec = embed_model.encode([query], convert_to_numpy=True)
    distances, indices = faiss_index.search(query_vec, k)
    top_docs = []
    for idx in indices[0]:
        top_docs.append({
            "content": doc_texts[idx],
            # Removed pdf_links and url since they're not used
        })
    return top_docs

def generate_answer(query, context):
    """Use the local LLM to generate an answer based on the retrieved context."""
    # Add IHEC Carthage-specific context to the prompt
    prompt = (
        f"You are an assistant for IHEC Carthage, a university in Tunisia. "
        f"Answer the following question based on the provided context and ensure the response is relevant to IHEC Carthage:\n\n"
        f"Question: {query}\n\n"
        f"Context: {context}\n\n"
        f"Answer:"
    )
    inputs = tokenizer([prompt], return_tensors="pt", truncation=True)
    outputs = gen_model.generate(**inputs, max_new_tokens=150)  # Increased max tokens for more detailed answers
    answer = tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
    return answer

@app.route("/chat", methods=["POST"])
def chat():
    """
    Expects a JSON payload:
    {
      "question": "What documents are required for registration?"
    }
    """
    data = request.get_json()
    user_query = data.get("question", "")
    if not user_query.strip():
        return jsonify({"error": "Empty question"}), 400

    # 1) Semantic search to get top docs
    top_docs = get_top_k_docs(user_query, k=3)

    # 2) Prepare context from top docs (up to 1000 chars each to pass to LLM)
    combined_context = "\n\n".join([doc["content"][:1000] for doc in top_docs])

    # 3) Generate LLM answer
    answer = generate_answer(user_query, combined_context)

    # 4) Prepare text snippets as sources
    sources = [doc["content"][:500] for doc in top_docs]  # Up to 500 chars each

    # Return the answer + text snippets rather than file paths
    response = {
        "answer": answer,
        "sources": sources
    }

    return jsonify(response), 200

@app.route("/")
def home():
    return "LLM Chatbot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
