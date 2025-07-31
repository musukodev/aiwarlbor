# supervisor.py

import time
import subprocess
import os
import signal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# --- Konfigurasi ---
PATH_TO_WATCH = "CompanyData"
DATA_BUILDER_SCRIPT = "data.py"
BACKEND_SCRIPT = "backend.py"
UVICORN_COMMAND = [
    "uvicorn",
    "backend:app",
    "--host", "0.0.0.0",
    "--port", "8000"
]

server_process = None

def start_server():
    """Memulai server Uvicorn."""
    global server_process
    print("🚀 Menyalakan server backend...")
    server_process = subprocess.Popen(UVICORN_COMMAND)
    print(f"✅ Server berjalan dengan PID: {server_process.pid}")

def stop_server():
    """Mematikan server Uvicorn."""
    global server_process
    if server_process:
        print(f"🛑 Mematikan server backend dengan PID: {server_process.pid}...")
        # Mengirim sinyal interupsi (sama seperti Ctrl+C)
        server_process.terminate()
        server_process.wait()
        server_process = None
        print("✅ Server berhasil dimatikan.")

def rebuild_database():
    """Menjalankan skrip data_builder.py."""
    print("🛠️ Membangun ulang database vektor...")
    try:
        # Menjalankan skrip dan menunggu sampai selesai
        os.system(f"python {DATA_BUILDER_SCRIPT}")
        print("✅ Database berhasil dibangun ulang.")
    except subprocess.CalledProcessError as e:
        print(f"❌ GAGAL membangun database: {e}")
    except FileNotFoundError:
        print(f"❌ GAGAL: Skrip '{DATA_BUILDER_SCRIPT}' tidak ditemukan.")

class MyEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        # Fungsi ini akan dipicu oleh event apapun (dibuat, dihapus, diubah)
        print(f"\n⚠️ Terdeteksi perubahan pada file: {event.src_path}")
        print("--- Memulai proses update otomatis ---")
        stop_server()
        rebuild_database()
        start_server()
        print("--- Proses update selesai, sistem siap. ---")

if __name__ == "__main__":
    # Lakukan build awal saat pertama kali dijalankan
    rebuild_database()
    start_server()

    # Siapkan pemantau
    event_handler = MyEventHandler()
    observer = Observer()
    observer.schedule(event_handler, PATH_TO_WATCH, recursive=True)
    
    print(f"\n👀 Memantau perubahan di folder '{PATH_TO_WATCH}'...")
    print("Tekan Ctrl+C untuk menghentikan supervisor.")
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Menghentikan supervisor dan server...")
        stop_server()
        observer.stop()
    observer.join()
    print("✅ Semua proses telah dihentikan. Sampai jumpa!")