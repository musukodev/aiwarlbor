import os
import shutil
import time
from threading import Thread, Event

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, TextLoader, CSVLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.vectorstores.utils import filter_complex_metadata

# --- Konfigurasi (tidak berubah) ---
DATA_PATH = r"CompanyData"
CHROMA_PATH = "chroma_db"
# Ganti dengan API Key Anda yang valid
GOOGLE_API_KEY = "AIzaSyDZOJJdHiBxIirgIVaDaeb0T3YaxHJl_zM" 

# --- Variabel Global (tidak berubah) ---
RESTART_EVENT = Event()

# --- Kelas dan Fungsi Monitoring (tidak berubah) ---
class FileChangeHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            print(f"\n\n[PERHATIAN] File baru terdeteksi: {event.src_path}")
            print("--> Menghentikan proses saat ini dan memulai ulang dari awal...")
            RESTART_EVENT.set()

def start_file_monitoring(path):
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print(f"[*] Memulai monitoring pada folder: '{path}'")
    try:
        while not RESTART_EVENT.is_set():
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
        print("[*] Monitoring dihentikan.")

# --- Fungsi load_and_chunk_documents (tidak berubah) ---
def load_and_chunk_documents():
    all_docs = []
    print("\nMemulai proses pemuatan dokumen satu per satu...")
    if not os.path.exists(DATA_PATH):
        print(f"[ERROR] Folder '{DATA_PATH}' tidak ditemukan. Membuat folder...")
        os.makedirs(DATA_PATH)
    for root, _, files in os.walk(DATA_PATH):
        for file in files:
            if RESTART_EVENT.is_set():
                return None
            file_path = os.path.join(root, file)
            print(f"--> Mencoba memproses file: {file_path}")
            try:
                if file.lower().endswith(".pdf"):
                    loader = PyPDFLoader(file_path)
                    all_docs.extend(loader.load())
                elif file.lower().endswith((".docx", ".doc")):
                    loader = UnstructuredWordDocumentLoader(file_path, mode="elements")
                    all_docs.extend(loader.load())
                elif file.lower().endswith(".txt"):
                    loader = TextLoader(file_path, encoding='utf-8')
                    all_docs.extend(loader.load())
                elif file.lower().endswith(".csv"):
                    loader = CSVLoader(file_path=file_path)
                    all_docs.extend(loader.load())
                elif file.lower().endswith(".xlsx"):
                    loader = UnstructuredExcelLoader(file_path, mode="elements")
                    all_docs.extend(loader.load())
                else:
                    print(f"    -> Melewati file dengan format tidak didukung: {file}")
                    continue
                print(f"    [OK] Berhasil memuat: {file}")
            except Exception as e:
                print(f"    [ERROR] Gagal memuat {file}: {e}")
                continue
    if RESTART_EVENT.is_set():
        return None
    if not all_docs:
        print("\nTidak ada dokumen yang berhasil dimuat. Menunggu file baru...")
        return []
    print(f"\nTotal {len(all_docs)} dokumen berhasil dimuat. Sekarang memecah dokumen...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(all_docs)
    print(f"Selesai! Dokumen dipecah menjadi {len(chunks)} chunks.")
    return chunks

# --- FUNGSI save_to_chroma YANG DIPERBARUI ---
def save_to_chroma(db: Chroma, chunks: list):
    """Membersihkan database yang ada dan menambahkan chunks baru."""
    if RESTART_EVENT.is_set():
        return False

    # 1. Membersihkan data lama dari koleksi (lebih aman daripada menghapus folder)
    try:
        # Dapatkan semua ID yang ada di koleksi
        existing_ids = db.get()['ids']
        if existing_ids:
            print(f"Menghapus {len(existing_ids)} dokumen lama dari database...")
            db._collection.delete(ids=existing_ids)
            print("Pembersihan selesai.")
    except Exception as e:
        print(f"[ERROR] Gagal membersihkan koleksi lama: {e}")
        # Tetap lanjutkan, upsert mungkin akan menimpa data lama
        pass
    
    if RESTART_EVENT.is_set():
        return False

    # 2. Menambahkan dokumen baru
    if not chunks:
        print("Tidak ada chunks baru untuk disimpan.")
        return True

    print(f"Menambahkan {len(chunks)} chunks baru ke ChromaDB...")
    filtered_chunks = filter_complex_metadata(chunks)
    db.add_documents(filtered_chunks)
    
    if RESTART_EVENT.is_set():
        return False

    print(f"✅ Berhasil! Database telah diperbarui.")
    return True

# --- LOGIKA UTAMA YANG DIPERBARUI ---
if __name__ == '__main__':
    # Hapus DB hanya sekali di awal untuk memastikan start yang bersih
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    # Buat objek embedding dan database sekali saja di luar loop
    embeddings = GoogleGenerativeAIEmbeddings(
        google_api_key=GOOGLE_API_KEY,
        model="models/embedding-001"
    )
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embeddings
    )
    
    while True:
        RESTART_EVENT.clear()

        monitor_thread = Thread(target=start_file_monitoring, args=(DATA_PATH,), daemon=True)
        monitor_thread.start()
        
        document_chunks = load_and_chunk_documents()

        if RESTART_EVENT.is_set():
            print("Sinyal restart diterima, memulai ulang loop utama...")
            while monitor_thread.is_alive(): time.sleep(0.1)
            continue

        # Kirim objek 'db' yang sudah ada ke dalam fungsi
        success = save_to_chroma(db, document_chunks)

        if not success or RESTART_EVENT.is_set():
            print("Sinyal restart diterima saat menyimpan, memulai ulang loop utama...")
            while monitor_thread.is_alive(): time.sleep(0.1)
            continue

        if not RESTART_EVENT.is_set():
            print("\n\nProses selesai tanpa interupsi. Skrip akan berhenti.")
            RESTART_EVENT.set()
            break
    
    while monitor_thread.is_alive(): time.sleep(0.1)
    
    print("Skrip selesai sepenuhnya.")
    
# 
# 