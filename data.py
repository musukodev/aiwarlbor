

import os
from langchain_community.document_loaders import PyPDFLoader, UnstructuredWordDocumentLoader, TextLoader, CSVLoader, UnstructuredExcelLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import Docx2txtLoader
import google.generativeai as genai
from langchain_community.vectorstores.utils import filter_complex_metadata
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

DATA_PATH = r"CompanyData" 
PATH_TO_WATCH = "CompanyData"
CHROMA_PATH = "chroma_db"
GOOGLE_API_KEY = "AIzaSyDZOJJdHiBxIirgIVaDaeb0T3YaxHJl_zM" 



def load_and_chunk_documents():
    all_docs = []
    print("Memulai proses pemuatan dokumen satu per satu...")

    for root, _, files in os.walk(DATA_PATH):
        for file in files:
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

    if not all_docs:
        print("\nTidak ada dokumen yang berhasil dimuat. Periksa folder atau file Anda.")
        return None

    print(f"\nTotal {len(all_docs)} dokumen berhasil dimuat. Sekarang memecah dokumen...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(all_docs)
    print(f"Selesai! Dokumen dipecah menjadi {len(chunks)} chunks.")
    return chunks

def save_to_chroma(chunks: list):
    """
    Fungsi ini mengambil chunks, membuat embeddings, dan menyimpannya ke ChromaDB.
    """

    if os.path.exists(CHROMA_PATH):
        print(f"Menghapus database lama di '{CHROMA_PATH}'...")
        import shutil
        shutil.rmtree(CHROMA_PATH)

    embeddings = GoogleGenerativeAIEmbeddings(
        google_api_key=GOOGLE_API_KEY,
        model="models/embedding-001"
        )

    filtered_chunks = filter_complex_metadata(chunks)
    
    print(f"Membuat embeddings dan menyimpan ke ChromaDB di '{CHROMA_PATH}'...")
    db = Chroma.from_documents(
        filtered_chunks, embeddings, persist_directory=CHROMA_PATH
    )
    print(f"✅ Berhasil! {len(db.get()['documents'])} chunks telah disimpan di ChromaDB.")


class MyEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        # Fungsi ini akan dipicu oleh event apapun (dibuat, dihapus, diubah)
        print(f"\n⚠️ Terdeteksi perubahan pada file: {event.src_path}")
        
        
        
def main():
    os.system(r"rm -r .\chroma_db")
    document_chunks = load_and_chunk_documents()

    if document_chunks:
        save_to_chroma(document_chunks)
        
if __name__ == '__main__':
    # print("Wait 10s")
    # time.sleep (10)
    event_handler = MyEventHandler()
    observer = Observer()
    observer.schedule(event_handler, PATH_TO_WATCH, recursive=True)
    
    print(f"\n👀 Memantau perubahan di folder '{PATH_TO_WATCH}'...")
    print("Tekan Ctrl+C untuk menghentikan supervisor.")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
            print ("a")
            # main()
            observer.stop()
            observer.join()
    except KeyboardInterrupt:
        print("\n🛑 Menghentikan supervisor dan server...")
        observer.stop()
    observer.join()
    print("✅ Semua proses telah dihentikan. Sampai jumpa!")