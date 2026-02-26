import streamlit as st
import pandas as pd
from langchain_chroma import Chroma
from database import get_embedding_function, DB_PATH
import os

st.set_page_config(page_title="ChromaDB Viewer", layout="wide")

st.title("🗄️ ChromaDB Viewer")
st.markdown("Visualisasi isi database vector Chroma seperti aplikasi MySQL/DBeaver.")

# Fungsi untuk load db
@st.cache_resource
def load_db():
    if not os.path.exists(DB_PATH):
        return None
    return Chroma(
        persist_directory=DB_PATH,
        embedding_function=get_embedding_function()
    )

db = load_db()

if db is None:
    st.error(f"⚠️ Database tidak ditemukan di lokasi: `{DB_PATH}`")
else:
    # Mengambil semua data
    try:
        results = db.get(include=["metadatas", "documents", "embeddings"])
        ids = results.get("ids", [])
        metadatas = results.get("metadatas", [])
        documents = results.get("documents", [])
        embeddings = results.get("embeddings", [])
        
        total_docs = len(ids)
        st.success(f"Berhasil terhubung ke `{DB_PATH}`. Total Dokumen/Chunks: **{total_docs}**")
        
        if total_docs > 0:
            # Ubah data ke dalam format list of dictionaries untuk Pandas
            data = []
            for i in range(total_docs):
                meta = metadatas[i] or {}
                source = meta.get("source", "Unknown")
                page = meta.get("page", 0)
                
                # Menggabungkan semua metadata lain jika ada
                other_meta = {k: v for k, v in meta.items() if k not in ["source", "page"]}
                
                # Format vector/embedding
                emb = embeddings[i] if (embeddings is not None and len(embeddings) > i) else None
                if emb is not None and len(emb) > 0:
                    emb_preview = f"[{', '.join(f'{x:.4f}' for x in emb[:5])}, ...] (Dim: {len(emb)})"
                else:
                    emb_preview = "N/A"
                
                data.append({
                    "ID": ids[i],
                    "Source File": source,
                    "Page": page,
                    "Document Content": documents[i],
                    "Vector/Embedding": emb_preview,
                    "Other Metadata": str(other_meta)
                })
            
            df = pd.DataFrame(data)
            
            # Tampilkan Filter
            st.subheader("🔍 Filter Data")
            col1, col2 = st.columns(2)
            
            with col1:
                search_text = st.text_input("Cari kata dalam konten dokumen:")
            
            with col2:
                sources = ["Semua"] + list(df["Source File"].unique())
                filter_source = st.selectbox("Filter berdasarkan file sumber:", sources)
            
            # Terapkan Filter
            filtered_df = df.copy()
            if search_text:
                filtered_df = filtered_df[filtered_df["Document Content"].str.contains(search_text, case=False, na=False)]
            
            if filter_source != "Semua":
                filtered_df = filtered_df[filtered_df["Source File"] == filter_source]
            
            st.markdown(f"**Menampilkan {len(filtered_df)} baris**")
            
            # Tampilkan Tabel
            st.dataframe(filtered_df, use_container_width=True, height=600)
            
        else:
            st.info("Database saat ini kosong.")
            
    except Exception as e:
        st.error(f"Gagal membaca data dari ChromaDB. Error: {str(e)}")
