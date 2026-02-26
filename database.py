import os
import shutil
from typing import List
from langchain_community.document_loaders import DirectoryLoader, UnstructuredPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from typing import List, Callable, Optional
import os
from dotenv import load_dotenv
import pytesseract

load_dotenv()

# Configure Tesseract path for Windows
tesseract_path = os.environ.get("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_path

try:
    import unstructured_pytesseract
    unstructured_pytesseract.pytesseract.tesseract_cmd = tesseract_path
except ImportError:
    pass

# Add tesseract directory to OS PATH for 'unstructured' library
tesseract_dir = os.path.dirname(tesseract_path)
if tesseract_dir not in os.environ.get("PATH", ""):
    os.environ["PATH"] = tesseract_dir + os.pathsep + os.environ.get("PATH", "")

def get_embedding_function():
    """
    Returns the embedding function used to vectorize text chunks.
    """
    return OllamaEmbeddings(
        model=os.environ.get("EMBEDDING_MODEL", "mxbai-embed-large"),
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    )

DB_PATH = "chroma_db"
DATA_PATH = "data"

def main(progress_callback: Optional[Callable[[str], None]] = None):
    """
    Main ingestion pipeline:
    1. Load PDFs from the data directory.
    2. Split documents into chunks.
    3. Add chunks to ChromaDB incrementally, preventing duplicates.
    """
    def notify(msg: str):
        print(msg)
        if progress_callback:
            progress_callback(msg)

    # 1. Load documents
    notify("Memulai proses Ingestion...")
    notify("Status: Membaca dokumen (Scanning/OCR)...")
    documents = load_documents()
    notify(f"Berhasil memuat {len(documents)} dokumen PDF.")

    if not documents:
        notify(f"Tidak ada dokumen yang ditemukan di direktori '{DATA_PATH}'.")
        return

    # 2. Split into chunks
    notify("Status: Memecah dokumen menjadi chunks (Text Splitting)...")
    chunks = split_documents(documents)
    notify(f"Dokumen dibagi menjadi {len(chunks)} chunks.")

    # 3. Add to ChromaDB
    notify("Status: Menghitung embeddings dan menyimpan ke ChromaDB...")
    add_to_chroma(chunks, progress_callback=notify)
    notify("Status: Selesai")

def load_documents() -> List[Document]:
    """Loads PDF documents from the specified directory using Unstructured for OCR."""
    document_loader = DirectoryLoader(
        DATA_PATH,
        glob="**/*.pdf",
        loader_cls=UnstructuredPDFLoader,
        loader_kwargs={"strategy": "hi_res"}
    )
    return document_loader.load()

def split_documents(documents: List[Document]) -> List[Document]:
    """Splits documents into smaller text chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        is_separator_regex=False,
    )
    return text_splitter.split_documents(documents)

def calculate_chunk_ids(chunks: List[Document]) -> List[Document]:
    """
    Generates deterministic IDs for each chunk.
    This ensures that when the same document is loaded again, 
    the IDs will be identical, preventing duplication in the vector DB.
    
    Format: source:page:chunk_index
    Example: data/laporan.pdf:2:5 (Document laporan.pdf, page 2, 5th chunk)
    """
    last_page_id = None
    current_chunk_index = 0

    for chunk in chunks:
        # Get metadata from the source document (provided by PyPDF)
        source = chunk.metadata.get("source", "unknown")
        # PyPDF page numbers are often 0-indexed, we can add 1 for readability
        page = chunk.metadata.get("page", 0) + 1
        
        current_page_id = f"{source}:{page}"

        # If it's the same page as the last chunk, increment the index
        if current_page_id == last_page_id:
            current_chunk_index += 1
        else:
            current_chunk_index = 0

        # Construct deterministic ID
        chunk_id = f"{current_page_id}:{current_chunk_index}"
        last_page_id = current_page_id

        # Update metadata to include the generated ID
        chunk.metadata["id"] = chunk_id

    return chunks

def add_to_chroma(chunks: List[Document], progress_callback: Optional[Callable[[str], None]] = None):
    """Adds only new chunks to the vector database."""
    def notify(msg: str):
        if progress_callback:
            progress_callback(msg)
        else:
            print(msg)

    # Ensure chunk IDs are calculated
    chunks_with_ids = calculate_chunk_ids(chunks)

    # Initialize the database
    db = Chroma(
        persist_directory=DB_PATH, 
        embedding_function=get_embedding_function()
    )

    # Fetch existing IDs in the DB
    # Note: Using db.get() fetches all records. For very large DBs, 
    # you might need to query specific IDs or use a different mechanism.
    existing_items = db.get(include=[])  # include=[] to fetch only IDs
    existing_ids = set(existing_items["ids"])
    notify(f"Jumlah dokumen yang sudah ada di DB: {len(existing_ids)}")

    # Filter out chunks that are already in the DB
    new_chunks = []
    for chunk in chunks_with_ids:
        if chunk.metadata["id"] not in existing_ids:
            new_chunks.append(chunk)

    # Add new chunks to DB
    if len(new_chunks) > 0:
        notify(f"⏩ Menambahkan hal baru: {len(new_chunks)} chunks.")
        # Extract IDs parallel to the chunk list
        new_chunk_ids = [chunk.metadata["id"] for chunk in new_chunks]
        db.add_documents(new_chunks, ids=new_chunk_ids)
        notify("✅ Data berhasil disimpan secara inkremental.")
    else:
        notify("✅ Tidak ada data baru untuk ditambahkan.")

def clear_database():
    """Utility to clear the database directory."""
    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Reset database.")
    args = parser.parse_args()
    
    if args.reset:
        print("✨ Membersihkan Database...")
        clear_database()
        
    main()
