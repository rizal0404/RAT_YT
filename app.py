import argparse
import os
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama, OllamaEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

# Constants
DB_PATH = "chroma_db"

PROMPT_TEMPLATE = """
Gunakan konteks di bawah ini untuk menjawab pertanyaan. 
Jika kamu tidak tahu jawabannya berdasarkan konteks ini, katakan saja bahwa kamu tidak tahu, jangan mencoba mengarang jawaban.
Jawablah dengan bahasa Indonesia yang natural dan jelas.

Konteks:
{context}

---
Pertanyaan: {question}

Jawaban:
"""

def get_embedding_function():
    """
    Returns the embedding function. 
    Must match the embedding function used during data ingestion.
    """
    return OllamaEmbeddings(
        model=os.environ.get("EMBEDDING_MODEL", "mxbai-embed-large"),
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    )

def get_llm(use_local=False):
    """
    Returns the LLM instance to be used for generation.
    - use_local: if True, returns an Ollama instance (local).
    - otherwise, returns an OpenAI model.
    """
    if use_local:
        return ChatOllama(
            model=os.environ.get("OLLAMA_LLM_MODEL", "llama3.1:8b"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0
        )
    else:
        # Require OPENAI_API_KEY environment variable
        return ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)

def query_rag(query_text: str, k: int = 3, use_local_llm: bool = False):
    """
    Queries the RAG system and returns a combined answer and sources.
    """
    embedding_function = get_embedding_function()
    
    # Initialize connection to DB
    db = Chroma(persist_directory=DB_PATH, embedding_function=embedding_function)

    # Retrieval: Get the top k relevant chunks
    results = db.similarity_search_with_score(query_text, k=k)

    if len(results) == 0:
        return "Tidak ada dokumen yang relevan di temukan di database.", []

    # Combine context
    context_text = "\n\n---\n\n".join([doc.page_content for doc, _score in results])

    # Construct prompt
    prompt = PromptTemplate(
        template=PROMPT_TEMPLATE,
        input_variables=["context", "question"]
    )
    formatted_prompt = prompt.format(context=context_text, question=query_text)

    # Generation
    llm = get_llm(use_local=use_local_llm)
    response = llm.invoke(formatted_prompt)

    # For newer versions of langchain-openai/chat, response is an AIMessage object.
    answer_text = response.content

    # Extract sources
    sources = []
    for doc, _score in results:
        source_id = doc.metadata.get("id", "Unknown")
        # Extract File Name and Page Number from the ID formatted as "file.pdf:page:chunk"
        # Or from metadata directly
        file_path = doc.metadata.get("source", "Sistem")
        file_name = os.path.basename(file_path)
        page_num = doc.metadata.get("page", 0) + 1  # 0-indexed adjustment
        sources.append(f"{file_name} (Halaman {page_num})")

    # Format final output
    formatted_sources = "\n".join([f"- {s}" for s in set(sources)]) # Use set to remove duplicate sources

    final_response = f"{answer_text}\n\nSumber:\n{formatted_sources}"

    return final_response, sources

def main():
    parser = argparse.ArgumentParser(description="Tanya RAG (Retrieval-Augmented Generation)")
    parser.add_argument("query", type=str, help="Pertanyaan yang ingin ditanyakan.")
    parser.add_argument("--local", action="store_true", help="Gunakan LLM lokal (Ollama).")
    parser.add_argument("-k", type=int, default=3, help="Jumlah top-K dokumen yang diambil.")
    
    args = parser.parse_args()
    
    query_text = args.query
    print(f"\n🔍 Mencari jawaban untuk: '{query_text}'...")

    try:
        response, sources = query_rag(query_text, k=args.k, use_local_llm=args.local)
        print("\n" + "="*50)
        print(response)
        print("="*50 + "\n")
    except Exception as e:
        print(f"\n❌ Terjadi kesalahan: {e}\nPastikan environment variable sudah disetel (misal OPENAI_API_KEY) jika tidak menggunakan model lokal.")

if __name__ == "__main__":
    main()
