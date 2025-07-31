# frontend.py (Versi Final dengan Threading untuk Anti-Lag)
import uvicorn
import threading
import sys
import requests
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QLineEdit
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QMouseEvent

BACKEND_URL = "http://localhost:8000/ask"

# LANGKAH 1: Buat kelas "Pekerja" untuk tugas berat
class Worker(QObject):
    # Definisikan sinyal untuk berkomunikasi kembali ke thread utama
    finished = pyqtSignal(str)  # Sinyal saat berhasil, membawa jawaban (string)
    error = pyqtSignal(str)     # Sinyal saat gagal, membawa pesan error (string)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        """Metode ini akan dijalankan di thread terpisah."""
        try:
            response = requests.post(BACKEND_URL, json={"query": self.query})
            if response.status_code == 200:
                answer = response.json().get("answer", "Tidak ada jawaban.")
                self.finished.emit(answer) # Kirim sinyal berhasil
            else:
                error_msg = f"Error dari server: {response.status_code}"
                self.error.emit(error_msg) # Kirim sinyal error
        except requests.exceptions.RequestException as e:
            error_msg = "Gagal terhubung ke server AI."
            print(f"Connection error: {e}")
            self.error.emit(error_msg) # Kirim sinyal error koneksi

class WallpaperWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.thread = None # Inisialisasi variabel thread
        self.worker = None # Inisialisasi variabel worker
        # ... (sisa __init__ Anda)
        self.initUI()
        # --- LANGKAH 1: Setup Timer dan Animasi ---
        self.loading_timer = QTimer(self)
        self.loading_timer.timeout.connect(self.update_loading_text)
        self.loading_frames = ["AI is thinking.", "AI is thinking..", "AI is thinking..."]
        self.current_frame = 0
        # -- PENAMBAHAN UNTUK ANIMASI MENGETIK --
        self.typing_timer = QTimer(self)
        self.typing_timer.timeout.connect(self.update_typing_text)
        self.full_answer_text = ""
        self.current_char_index = 0
        # ---------------------------------------
        
    def initUI(self):
        # ... (seluruh kode initUI Anda tetap sama, tidak perlu diubah)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(300, 300, 800, 150)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Please type your question here, then press enter.")
        self.result_label = QLabel("The AI's answer will appear here.", self)
        self.result_label.setWordWrap(True)
        self.input_field.setStyleSheet("""
            QLineEdit {
                color: #E0E0E0; background-color: rgba(20, 20, 20, 0.7);
                border: 1px solid #444; border-radius: 8px;
                font-size: 18px; font-family: Arial; padding: 12px;
            }
            QLineEdit:focus { border: 1px solid #0078d4; }
        """)
        self.result_label.setStyleSheet("""
            QLabel {
                color: #CCCCCC; background-color: rgba(10, 10, 10, 0.6);
                border-radius: 8px; font-size: 15px; font-family: Arial;
                padding: 12px;
            }
        """) # Style Anda
        self.input_field.returnPressed.connect(self.start_ai_request)
        layout.addWidget(self.input_field)
        layout.addWidget(self.result_label)
        self.show()
    def start_loading_animation(self):
        """Memulai timer dan animasi teks."""
        self.loading_frame_index = 0
        self.result_label.setText(self.loading_frames[0])
        self.loading_timer.start(300)

    def update_loading_text(self):
        """Mengubah teks ke frame animasi berikutnya."""
        self.loading_frame_index = (self.loading_frame_index + 1) % len(self.loading_frames)
        self.result_label.setText(self.loading_frames[self.loading_frame_index])

    def stop_loading_animation(self):
        """Menghentikan timer."""
        self.loading_timer.stop()
        
    def start_typing_animation(self, text):
        """Memulai animasi mengetik untuk teks yang diberikan."""
        self.full_answer_text = text
        self.current_char_index = 0
        self.result_label.setText("") # Kosongkan label sebelum mulai
        self.typing_timer.start(30) # Atur kecepatan mengetik (ms)
        
    def update_typing_text(self):
        """Menambahkan satu karakter ke label."""
        if self.current_char_index < len(self.full_answer_text):
            current_text = self.result_label.text()
            next_char = self.full_answer_text[self.current_char_index]
            self.result_label.setText(current_text + next_char)
            self.current_char_index += 1
        else:
            # Jika sudah selesai, hentikan timer
            self.typing_timer.stop()
    # Ganti nama fungsi get_ai_response menjadi start_ai_request
    def start_ai_request(self):
        user_query = self.input_field.text()
        if not user_query:
            return
        
        self.start_loading_animation()
        self.input_field.clear()
        # Pekerja utama langsung melakukan tugas ringan ini
        # self.result_label.setText("AI sedang berpikir...")
        # self.input_field.clear()

        # LANGKAH 2: Siapkan dan jalankan thread baru
        self.thread = QThread()
        self.worker = Worker(user_query)
        self.worker.moveToThread(self.thread)

        # Hubungkan sinyal dari worker ke fungsi di thread utama
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.update_result)
        self.worker.error.connect(self.update_error)

        # Hubungkan sinyal finished dari thread untuk bersih-bersih
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        # Mulai thread!
        self.thread.start()

    # LANGKAH 3: Buat fungsi untuk menerima hasil dari worker
    def update_result(self, answer):
        """Fungsi ini dipanggil saat sinyal 'finished' diterima."""
        self.stop_loading_animation()
        # self.result_label.setText(answer)
        self.start_typing_animation(answer) 

    def update_error(self, error_msg):
        """Fungsi ini dipanggil saat sinyal 'error' diterima."""
        self.stop_loading_animation()
        # self.result_label.setText(error_msg)
        self.start_typing_animation(error_msg)
    
    # Fungsi ini dipanggil saat Anda menekan tombol mouse.
    # Ia akan menyimpan posisi awal klik Anda.
    def mousePressEvent(self, event):
        self.oldPos = event.globalPosition().toPoint()

# Fungsi ini dipanggil saat Anda menggerakkan mouse sambil menahan tombol.
# Ia menghitung perbedaan antara posisi baru dan posisi lama,
# lalu memindahkan jendela sesuai perbedaan tersebut.
    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPosition().toPoint()
    
# def run_backend():
#     """Fungsi untuk menjalankan server FastAPI di thread terpisah."""
#     uvicorn.run("backend:app", host="127.0.0.1", port=8000)

if __name__ == '__main__':
    # backend_thread = threading.Thread(target=run_backend, daemon=True)
    # backend_thread.start()
    app = QApplication(sys.argv)
    ex = WallpaperWidget()
    sys.exit(app.exec())