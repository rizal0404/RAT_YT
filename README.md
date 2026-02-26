# Production-Grade RAG (Retrieval-Augmented Generation) Application

Proyek ini adalah implementasi sistem **Retrieval-Augmented Generation (RAG)** skala produksi menggunakan Python. Aplikasi ini memungkinkan Anda mengunggah dokumen PDF, lalu mengajukan pertanyaan yang jawabannya disintesis berdasarkan dokumen tersebut dengan menggunakan antarmuka bahasa Indonesia. 

Sistem ini mendukung pengelolaan data secara inkremental (hanya menambahkan dokumen/teks baru ke *database*, tanpa menyebabkan duplikasi) dan mendukung penuh instalasi *Local LLMs* (menggunakan Ollama) agar seluruh data privasi tetap aman secara *offline*. Disamping itu, kode secara modular juga mendukung pemanggilan *API-Based LLMs* seperti OpenAI.

---

## 🏗️ 1. Informasi Teknis & Stack

*   **Penyatuan Logika / Orkestrator:** LangChain
*   **Vector Database:** ChromaDB (Persisten di `chroma_db/`)
*   **Pembaca Dokumen & OCR:** `unstructured` via `UnstructuredPDFLoader` (Mampu mengekstrak teks dari PDF hasil *scan* atau gambar dengan `strategy="hi_res"`).
*   **Ketergantungan OCR:** Tesseract OCR & Poppler (wajib diinstal di sistem).
*   **Pemecah Dokumen:** `RecursiveCharacterTextSplitter` (menyediakan konteks sebelum/sesudah teks)
*   **Model Embedding Dasar:** Ollama Embeddings (`mxbai-embed-large`)
*   **Model Penghasil Teks / Generator:** Ollama LLM (`llama3.1:8b`)
*   **Sistem Evaluasi:** LLM-As-A-Judge lewat `pytest`
*   **Lingkungan Bahasa:** Python 3.9+ (disarankan)

---

## ⚙️ 2. Arsitektur Workflow & Skema Data

### A. Alur Ingestion (Mengingesti Konteks / Menyimpan Dokumen)
Skrip referensi: `database.py`
1.  **Loading & OCR:** Memuat seluruh file `.pdf` yang berada di dalam folder `data/` menggunakan `DirectoryLoader` dan `UnstructuredPDFLoader`. Sistem ini mendukung Optical Character Recognition (OCR) pada dokumen hasil scan gambar.
2.  **Splitting:** Memecah dokumen panjang menjadi "chunks" pendek (ukuran `1000` karakter dengan irisan `200` karakter).
3.  **Deterministic ID Generation:** Setiap *chunk* secara matematis diberi Identity-Card (ID) berupa format: `nama_dokumen.pdf:halaman:chunk_index`.
4.  **Incremental Database Addition:** ChromaDB mengecek ID dari dokumen yang akan masuk. Jika ID tersebut sudah ada di vektor database, proses di-*skip*. Jika ID baru, vektor akan dikalkulasi dan di-*insert*. Hal ini mencegah memori bengkak.

### B. Alur RAG & Q/A (Bertanya, Mencari, Menjawab)
Skrip referensi: `app.py`
1.  **User Query:** Pengguna mengetikkan pertanyaan (e.g., "Apa itu XYZ?").
2.  **Vector Search:** Sistem mengubah query tadi menjadi rentetan angka (*vector sequence*). Kemudian mencari 3 *chunks* dokumen di dalam kumpulan PDF (di `chroma_db`) yang nilai kesamaan matematisnya (cosine-similarity) paling berurutan / relevan.
3.  **Context Augmenting:** 3 *chunks* tersebut disisipkan ke dalam Prompt Bahasa Indonesia.
4.  **Generativity Validation:** Prompt tersebut digabung dan diantarkan ke LLM. LLM wajib menjawab berdasarkan konteks itu tanpa mengarang bebas.
5.  **Output Teks + Sumber:** Teks jawaban final akan dirangkum dan ID dari mana jawaban itu diambil akan diekstrak menjadi daftar nama file/halaman.

---

## 🛠️ 3. Instruksi Instalasi

1. **Pastikan Anda Menginstal Prasyarat Ini di Sistem Utama Anda:**
   *  Python versi 3.9 atau lebih baru.
   *  **[Penting]** **Tesseract OCR**: Anda wajib mengunduh dan menginstal [Tesseract OCR untuk Windows](https://github.com/UB-Mannheim/tesseract/wiki). Simpan Tesseract di lokasi bawaannya (misal: `C:\Program Files\Tesseract-OCR\tesseract.exe`). Skrip `database.py` secara khusus akan memanggil path ini.
   *  **[Penting]** **Poppler** (opsional tapi dianjurkan untuk konversi PDF ke gambar): Download binary poppler untuk Windows, dan tambahkan ke `PATH` Environment Variables.
   *  [Ollama](https://ollama.com/) terinstal dalam sistem/komputer Anda.
   *  Download model Ollama untuk *Text Embedding*: 
      ```bash
      ollama run mxbai-embed-large
      ```
   *  Download model Ollama untuk *LLM Text Generation*:
      ```bash
      ollama run llama3.1:8b
      ```

2. **Klon Repositori Ini dari GitHub:**
   Anda dapat melakukan *Fork* repositori ini di GitHub jika ingin ikut berkontribusi, atau dapat langsung melakukan *clone*:
   ```bash
   git clone https://github.com/rizal0404/RAT_YT.git
   cd RAT_YT
   ```

3. **Membuat dan Mengaktifkan Virtual Environment:**
   * **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```

4. **Instalasi Dependencies Pustaka Python:**
   ```bash
   pip install -r requirements.txt
   pip install fastapi uvicorn python-multipart
   ```

5. **Konfigurasi Variabel Lingkungan (.env):**
   * Pastikan Anda memiliki file `.env` di direktori utama (sama degan `app.py`). Anda dapat menyalin file template dengan cara mengubah nama `cp .env.example .env`.
   * File `.env` minimal berisi:
     ```env
     EMBEDDING_MODEL="mxbai-embed-large"
     OLLAMA_BASE_URL="http://localhost:11434"
     OLLAMA_LLM_MODEL="llama3.1:8b"
     
     # [PENTING UNTUK WINDOWS] Gunakan Forward Slash (/) BUKAN Backslash (\)
     # Backslash (\t) akan terbaca sebagai tombol TAB dan membuat error "Tesseract Not Found".
     TESSERACT_PATH="C:/Program Files/Tesseract-OCR/tesseract.exe"
     ```

---

## 🚀 4. Instruksi Penggunaan (Web Dashboard Interaktif)

Aplikasi ini sekarang memiliki antarmuka Web UI/UX modern bergaya *Glassmorphism* dan bernuansa *Dark Mode*. Tidak perlu lagi mengetik terminal secara manual!

### Langkah Menjalankan Web Server:
Jalankan server aplikasi (FastAPI) menggunakan perintah berikut:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000
```
*(Tambahkan `--reload` jika ingin mode pengembangan).*

Setelah itu, silakan buka peramban (*browser*) Anda ke **[http://localhost:8000](http://localhost:8000)**.

### Menggunakan Aplikasi Web:
1. **Upload Dokumen:** Di bilah sisi (Sidebar) bagian bawah, *drag & drop* atau klik untuk unggah file PDF manual / operasi Anda.
2. **Memproses Data (Ingestion):** Klik tombol **Proses Pemahaman**. Kotak terminal kecil di layar (*logs bar*) akan menampilkan laporan status secara langsung (misal: "Memecah teks chunks", "Scanning OCR", atau "Siap ke ChromaDB").
3. **Mulai Chat:** Ketik pertanyaan operasional/prosedur yang ada pada dokumen tersebut di kolom *chat box*. Anda juga bisa menyetel pengatur (Top-K) di sidebar untuk menentukan seberapa dalam agen membaca referensi halaman yang mirip.

---

## 💻 Opsional: Mode Terminal (CLI) Tradisional

### Langkah 1: Memproses File Dokumen (Ingestion)
1. Letakkan seluruh file PDF dokumen petunjuk, manual, atau buku referensi Anda ke dalam folder `data/` *(Contoh: `data/Buku_SOP.pdf`)*.
2. Jalankan perintah di bawah ini lewat terminal untuk membuat *embeddings* (mengajarkan AI):
   ```bash
   python database.py
   ```
   > **Note:** Bila Anda menambahkan file baru atau halaman baru di masa depan ke dalam direktori `data/`, jalankan ulang perintah `python database.py`. Skrip ini cukup cerdas untuk hanya **menambah file baru saja** *(incremental generation)*.
   
3. **(Opsional)** Jika Anda ingin membersihkan ulang seluruh pangkalan data, gunakan *flag*:
   ```bash
   python database.py --reset
   ```

### Langkah 2: Mulai Bertanya ke LLM
Setelah berhasil menjalankan Langkah 1, ajukan pertanyaan dari dokumen-dokumen tadi menggunakan terminal:
```bash
python app.py "Tuliskan pertanyaan Anda di sini" --local
```
**Perhatikan flag `--local`**. Flag ini memberitahu kode program untuk menghiraukan OpenAI ChatGPT dan wajib menggunakan infrastruktur Ollama `llama3.1:8b` luring/offline sistem yang ditulis di dalam `.env`.

**Contoh Kasus Eksekusi:**
```bash
python app.py "Bagaimana cara melakukan absensi di mesin pabrik 02?" --local

🔍 Mencari jawaban untuk: 'Bagaimana cara melakukan absensi di mesin pabrik 02?'...

==================================================
Untuk absen di mesin pabrik 02, Anda dapat mengikuti langkah berikut ini:
1. Tempelkan kartu ID Card ke scanner inframerah yang ada di dinding depan pagar.
2. Tunggu warna lampu indikator berubah menjadi hijau.
3. Tekan angka shift operasional sesuai hari tersebut (misal, shift 1).

Sumber:
- Manual Absensi Pekerja 2024.pdf (Halaman 5)
==================================================
```

---

## 🧪 5. Menjalankan Modul Evaluasi (LLM as a Judge)
Proyek ini memuat unit-testing otomatis untuk mencegah LLM melakukan halusinasi dan memvalidasi apakah jawaban yang akan diciptakannya konsisten secara harfiah *(Semantic Equivalence)*. 

Untuk menjalankan serangkaian tes (*Positive Testing* & *Negative Testing*):
```bash
# Pastikan Anda mengaturnya menggunakan OpenAI kunci API pada .env sebelum testing bila testing difokuskan untuk kualitas tinggi
pytest test_rag.py -v -s
```
