# supervisor.py (Versi dengan Debouncing)

import time
import subprocess
import os
import threading  # <-- Import threading

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
REBUILD_DELAY = 2.0  # Waktu tunggu dalam detik

# --- Variabel Global untuk Kontrol ---
server_process = None
rebuild_timer = None  # Variabel untuk menampung timer

def start_server():
    """Memulai server Uvicorn."""
    global server_process
    if server_process is None:
        print("🚀 Menyalakan server backend...")
        server_process = subprocess.Popen(UVICORN_COMMAND)
        print(f"✅ Server berjalan dengan PID: {server_process.pid}")

def stop_server():
    """Mematikan server Uvicorn."""
    global server_process
    if server_process:
        print(f"🛑 Mematikan server backend dengan PID: {server_process.pid}...")
        server_process.terminate()
        server_process.wait()
        server_process = None
        print("✅ Server berhasil dimatikan.")

def rebuild_database():
    """Menjalankan skrip data_builder.py."""
    print("🛠️ Membangun ulang database vektor...")
    try:
        os.system(f"python {DATA_BUILDER_SCRIPT}")
        print("✅ Database berhasil dibangun ulang.")
    except Exception as e:
        print(f"❌ GAGAL membangun database: {e}")

def trigger_rebuild_sequence():
    """Fungsi yang berisi urutan lengkap untuk mem-build ulang."""
    print("\n--- [AKSI] Memulai proses update otomatis ---")
    stop_server()
    rebuild_database()
    start_server()
    print("--- [AKSI] Proses update selesai, sistem siap. ---")

class MyEventHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        global rebuild_timer
        
        # Abaikan event pada direktori atau file sementara
        if event.is_directory or event.src_path.endswith('~'):
            return

        print(f"👀 Terdeteksi perubahan pada: {os.path.basename(event.src_path)}. Menunggu perubahan lain...")

        # Batalkan timer sebelumnya jika ada (mereset waktu tunggu)
        if rebuild_timer and rebuild_timer.is_alive():
            rebuild_timer.cancel()
        
        # Buat timer baru yang akan memanggil fungsi rebuild setelah delay
        rebuild_timer = threading.Timer(REBUILD_DELAY, trigger_rebuild_sequence)
        rebuild_timer.start()

if __name__ == "__main__":
    rebuild_database()
    start_server()

    event_handler = MyEventHandler()
    observer = Observer()
    observer.schedule(event_handler, PATH_TO_WATCH, recursive=True)
    observer.start()
    
    print(f"\n👀 Memantau perubahan di folder '{PATH_TO_WATCH}'...")
    print("Tekan Ctrl+C untuk menghentikan supervisor.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Menghentikan supervisor dan server...")
        if rebuild_timer:
            rebuild_timer.cancel()
        stop_server()
        observer.stop()
    
    observer.join()
    print("✅ Semua proses telah dihentikan. Sampai jumpa!")