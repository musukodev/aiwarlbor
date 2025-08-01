# frontend.py (Versi dengan Input IP Dinamis)

import sys
import requests
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QMouseEvent

# Hapus BACKEND_URL yang statis dari sini

# Kelas Worker (TIDAK ADA PERUBAHAN)
class Worker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, query, backend_url): # Tambahkan backend_url sebagai parameter
        super().__init__()
        self.query = query
        self.backend_url = backend_url

    def run(self):
        try:
            # Gunakan URL yang dinamis
            response = requests.post(self.backend_url, json={"query": self.query})
            if response.status_code == 200:
                answer = response.json().get("answer", "Tidak ada jawaban.")
                self.finished.emit(answer)
            else:
                error_msg = f"Error dari server: {response.status_code}"
                self.error.emit(error_msg)
        except requests.exceptions.RequestException as e:
            error_msg = "Gagal terhubung ke server AI."
            print(f"Connection error: {e}")
            self.error.emit(error_msg)

class WallpaperWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self.initUI()
        self.initial_height = self.height() # Simpan tinggi awal jendela
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
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(300, 300, 800, 180) # Sedikit perbesar tinggi jendela
        
        # --- Layout Utama Vertikal ---
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # --- Layout Horizontal untuk Input Fields ---
        input_layout = QHBoxLayout()

        # 1. Input Field untuk Alamat IP Server
        self.ip_field = QLineEdit(self)
        self.ip_field.setText("http://127.0.0.1:8000") # Nilai default
        self.ip_field.setStyleSheet("""
            QLineEdit {
                color: #B0B0B0; background-color: rgba(20, 20, 20, 0.7);
                border: 1px solid #444; border-radius: 8px;
                font-size: 18px; padding: 12px;
            }
        """)
        
        # 2. Kotak Input untuk Pertanyaan
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Ketik pertanyaan Anda di sini, lalu tekan Enter...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                color: #E0E0E0; background-color: rgba(20, 20, 20, 0.7);
                border: 1px solid #444; border-radius: 8px;
                font-size: 18px; padding: 12px;
            }
            QLineEdit:focus { border: 1px solid #0078d4; }
        """)
        self.input_field.returnPressed.connect(self.start_ai_request)

        # Tambahkan kedua input ke layout horizontal
        input_layout.addWidget(self.ip_field, 1) # Angka 1 adalah stretch factor
        input_layout.addWidget(self.input_field, 2) # Angka 2 membuat input pertanyaan lebih lebar

        # 3. Label untuk menampilkan jawaban AI
        self.result_label = QLabel("Jawaban AI akan muncul di sini.", self)
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("""
            QLabel {
                color: #CCCCCC; background-color: rgba(10, 10, 10, 0.6);
                border-radius: 8px; font-size: 15px; font-family: Arial;
                padding: 12px;
            }
        """)
        
        # Tambahkan layout input dan label hasil ke layout utama
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.result_label)

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
        # Ambil alamat IP dari input field setiap kali request dibuat
        server_ip = self.ip_field.text()
        
        if not user_query or not server_ip:
            self.result_label.setText("Alamat IP dan Pertanyaan tidak boleh kosong.")
            return
        self.resize(self.width(), self.initial_height)
        self.start_loading_animation()
        self.input_field.clear()

        # Bangun URL backend secara dinamis
        backend_url = f"{server_ip.strip()}/ask"

        self.thread = QThread()
        # Berikan URL dinamis ke Worker
        self.worker = Worker(user_query, backend_url)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.update_result)
        self.worker.error.connect(self.update_error)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        self.thread.start()

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
    
    # Fungsi mousePressEvent dan mouseMoveEvent (TIDAK ADA PERUBAHAN)
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.oldPos = event.globalPosition().toPoint()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = WallpaperWidget()
    sys.exit(app.exec())