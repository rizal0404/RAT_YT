import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from database import get_embedding_function, DB_PATH

# Load environment variable
load_dotenv()

def view_database():
    print(f"Membuka database Chroma dari '{DB_PATH}'...\n")
    
    # Inisialisasi koneksi ke DB Chroma
    db = Chroma(
        persist_directory=DB_PATH,
        embedding_function=get_embedding_function()
    )
    
    # Memanggil isi dari database
    results = db.get(include=["metadatas", "documents"])
    
    ids = results.get("ids", [])
    metadatas = results.get("metadatas", [])
    documents = results.get("documents", [])
    
    total_docs = len(ids)
    print(f"Total baris/chunks di ChromaDB: {total_docs}\n")
    
    if total_docs == 0:
        print("Database kosong.")
        return

    print("=== Preview Data (Maksimal 5 data pertama) ===")
    limit = min(5, total_docs)
    for i in range(limit):
        print(f"\n--- Item {i+1} ---")
        print(f"ID      : {ids[i]}")
        
        # Mengecek metadata yang berisi path dan page sumber
        source = metadatas[i].get("source", "N/A")
        page = metadatas[i].get("page", 0)
        # Seringkali metadata di PyPDF berupa index 0 untuk halaman 1,
        # dan index halaman real jika pakai loader lain
        print(f"Source  : {source} (Page {page})")
        
        # Menampilkan snippet dari dokumen text untuk mengecek
        content_snippet = documents[i].replace('\n', ' ')[:150]
        print(f"Content : {content_snippet}...")

if __name__ == "__main__":
    view_database()
