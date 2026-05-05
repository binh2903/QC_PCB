import sys
import os
import winsound
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QMainWindow, QListWidgetItem, QTableWidgetItem
from PyQt6.QtGui import QPixmap, QColor, QPalette
from PyQt6 import QtCore
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from ui_main import Ui_MainWindow
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ====================================================================== #
#  CHE DO SCHEDULER AN TOAN - CHI DOC ANH KHI FILE DA GHI XONG         #
# ====================================================================== #
class ImageHandler(FileSystemEventHandler):
    def __init__(self, signal):
        self.signal = signal

    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.signal.emit(file_path)

    def on_modified(self, event):
        if not event.is_directory:
            file_path = event.src_path
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                self.signal.emit(file_path)


class WatcherThread(QThread):
    image_created = pyqtSignal(str)
    log_message = pyqtSignal(str, str)  # message, type

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self._running = True

    def run(self):
        event_handler = ImageHandler(self.image_created)
        observer = Observer()
        try:
            observer.schedule(event_handler, self.folder_path, recursive=False)
            observer.start()
            self.log_message.emit(
                f"Watchdog da khoi tai thu muc: {self.folder_path}", "info"
            )
            while self._running:
                self.msleep(500)
        except Exception as e:
            self.log_message.emit(f"Watchdog loi: {str(e)}", "error")
        finally:
            observer.stop()
            observer.join()

    def stop(self):
        self._running = False


# ====================================================================== #
#  LOP GIAO DIEN CHINH - RESPONSIVE + BUTTON FEEDBACK                   #
# ====================================================================== #
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.uic = Ui_MainWindow()
        self.uic.setupUi(self)

        # ---- Tu cho phep resize ----
        self.setMinimumSize(900, 600)
        self.setSizePolicy(
            __import__("PyQt6.QtWidgets", fromlist=["QSizePolicy"]).QSizePolicy.Policy.Expanding,
            __import__("PyQt6.QtWidgets", fromlist=["QSizePolicy"]).QSizePolicy.Policy.Expanding,
        )

        # ---- Delay doc anh an toan ----
        self.image_load_delay_ms = 800

        # ---- Bien dem ----
        self.defect_counter = 0
        self.is_running = False

        # ---- Dong ho ----
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

        # ---- Thu muc anh (DUONG DAN TUYET DOI) ----
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.watch_folder = os.path.join(self.base_dir, "images\images_input")
        if not os.path.exists(self.watch_folder):
            os.makedirs(self.watch_folder)

        # ---- Watchdog ----
        self.worker = WatcherThread(self.watch_folder)
        self.worker.image_created.connect(self.on_image_detected)
        self.worker.log_message.connect(self.update_log)
        self.worker.start()

        # ---- Ket noi nut bam + feedback ----
        self.uic.btn_start.clicked.connect(self._on_start_clicked)
        self.uic.btn_stop.clicked.connect(self._on_stop_clicked)
        self.uic.btn_reset.clicked.connect(self._on_reset_clicked)

        self.update_log(f"Dang giam sat: {self.watch_folder}", "info")

        # ---- Responsive: thiet lap layout lan dau ----
        QTimer.singleShot(50, self._do_responsive_layout)

    # ================================================================== #
    #  RESPONSIVE LAYOUT - Tinh kich thuoc theo kich thuoc window        #
    # ================================================================== #
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._do_responsive_layout()

    def _do_responsive_layout(self):
        """Tinh toan va dat kich thuoc tat ca widget theo kich thuoc window."""
        w = self.width()
        h = self.height()

        # ---- TITLE BAR (fixed height = 80px) ----
        title_h = 80
        self.uic.title_bar.setGeometry(0, 0, w, title_h)

        # Logo
        logo_size = 50
        self.uic.logo_frame.setGeometry(15, (title_h - logo_size) // 2, logo_size, logo_size)
        self.uic.lbl_logo.setGeometry(0, 0, logo_size, logo_size)

        # Title text
        self.uic.lbl_title.setGeometry(80, 5, w // 2 - 100, 35)
        self.uic.lbl_subtitle.setGeometry(80, 42, w // 2 - 100, 25)

        # University info (phai)
        info_w = min(400, w // 3)
        self.uic.lbl_university.setGeometry(w - info_w - 20, 5, info_w, 25)
        self.uic.lbl_faculty.setGeometry(w - info_w - 20, 32, info_w, 25)
        self.uic.lbl_clock.setGeometry(w - info_w - 20, 55, info_w, 20)

        # ---- MAIN AREA (duoi title bar) ----
        main_top = title_h + 5
        main_h = h - main_top - 10
        margin = 15

        # Left panel (camera + buttons): 65% width
        left_w = int((w - margin * 3) * 0.65)
        right_w = w - left_w - margin * 3

        # ---- INSPECTOR (left panel) ----
        self.uic.INSPECTOR.setGeometry(margin, main_top, left_w, main_h)

        # CAM_VIEW: chiem het INSPECTOR tru 70px cho nut
        btn_area_h = 70
        cam_h = main_h - btn_area_h - 10
        self.uic.CAM_VIEW.setGeometry(0, 0, left_w, cam_h)

        # lbl_monitor (fill CAM_VIEW)
        self.uic.lbl_monitor.setGeometry(5, 5, left_w - 10, cam_h - 10)

        # 3 NUT BAM (chia deu)
        btn_y = cam_h + 8
        btn_h = btn_area_h - 18
        btn_gap = 8
        btn_w = (left_w - btn_gap * 2) // 3
        self.uic.btn_start.setGeometry(0, btn_y, btn_w, btn_h)
        self.uic.btn_reset.setGeometry(btn_w + btn_gap, btn_y, btn_w, btn_h)
        self.uic.btn_stop.setGeometry((btn_w + btn_gap) * 2, btn_y, btn_w, btn_h)

        # ---- RIGHT PANEL ----
        right_x = margin * 2 + left_w
        self.uic.right_panel.setGeometry(right_x, main_top, right_w, main_h)

        # Tracking log group: 58% of right panel height
        log_h = int(main_h * 0.58)
        self.uic.tracking_log_group.setGeometry(0, 0, right_w, log_h)
        self.uic.lbl_tracking_title.setGeometry(0, 0, right_w, 28)
        self.uic.table_tracking_log.setGeometry(0, 30, right_w, log_h - 65)
        self.uic.btn_add_log.setGeometry(right_w - 180, log_h - 30, 80, 26)
        self.uic.btn_delete_log.setGeometry(right_w - 90, log_h - 30, 80, 26)

        # Counter group: phan con lai
        counter_y = log_h + 5
        counter_h = main_h - log_h - 5
        self.uic.counter_group.setGeometry(0, counter_y, right_w, counter_h)
        self.uic.lbl_counter_title.setGeometry(0, 0, right_w, 28)

        # LCD row: chia 4 cot
        lcd_y = 35
        lcd_label_h = 22
        lcd_h = max(40, min(55, counter_h // 5))
        lcd_w = (right_w - 40) // 4
        lcd_gap = 10

        positions = [
            ("lbl_total", "lcd_total_unit", 0),
            ("lbl_ok_count", "lcd_pass", 1),
            ("lbl_ng_count", "lcd_ng", 2),
            ("lbl_yield", "lcd_yield", 3),
        ]
        for lbl_name, lcd_name, col in positions:
            x = col * (lcd_w + lcd_gap) + 5
            getattr(self.uic, lbl_name).setGeometry(x, lcd_y, lcd_w, lcd_label_h)
            getattr(self.uic, lcd_name).setGeometry(x, lcd_y + lcd_label_h + 2, lcd_w, lcd_h)

        # Elapsed + Result
        bottom_y = lcd_y + lcd_label_h + lcd_h + 15
        elapsed_w = right_w // 2 - 10
        result_w = right_w - elapsed_w - 20
        self.uic.lbl_eslaped_count.setGeometry(5, bottom_y, elapsed_w, 22)
        self.uic.lcd_elapsed.setGeometry(5, bottom_y + 24, elapsed_w, max(40, counter_h - bottom_y - 70))
        self.uic.lbl_result.setGeometry(elapsed_w + 15, bottom_y, result_w, 22)
        self.uic.lbl_result.setGeometry(
            elapsed_w + 15, bottom_y, result_w,
            max(50, counter_h - bottom_y - 30)
        )

    # ================================================================== #
    #  DONG HO                                                            #
    # ================================================================== #
    def _update_clock(self):
        now = datetime.now().strftime("%H:%M:%S  %d/%m/%Y")
        self.uic.lbl_clock.setText(now)

    # ================================================================== #
    #  BUTTON FEEDBACK - Am thanh + Hieu ung                             #
    # ================================================================== #
    def _play_beep(self, freq=800, duration=150):
        """Phat am thanh beep (Windows)."""
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass

    def _flash_button(self, button, color_normal, color_active, duration=300):
        """Lam nut sang len roi tat."""
        original_style = button.styleSheet()
        button.setStyleSheet(
            f"QPushButton {{ background-color: {color_active}; color: white; "
            f"border-radius: 4px; border: 2px solid white; }}"
        )
        QTimer.singleShot(duration, lambda: button.setStyleSheet(original_style))

    def _on_start_clicked(self):
        self.is_running = True
        self._play_beep(800, 150)  # Beep cao
        self._flash_button(self.uic.btn_start, "#00c853", "#69f0ae")
        self.uic.lbl_result.setText("RUNNING")
        self.uic.lbl_result.setStyleSheet(
            "color: #00e676; background-color: #1a1a2e; "
            "border: 2px solid #00e676; border-radius: 6px; font-size: 22px; font-weight: bold;"
        )
        self.update_log("Nguoi dung nhan START - He thong bat dau hoat dong", "info")

    def _on_stop_clicked(self):
        self.is_running = False
        self._play_beep(400, 300)  # Beep thap, lau hon
        self._flash_button(self.uic.btn_stop, "#e53935", "#ff8a80")
        self.uic.lbl_result.setText("STOPPED")
        self.uic.lbl_result.setStyleSheet(
            "color: #e53935; background-color: #1a1a2e; "
            "border: 2px solid #e53935; border-radius: 6px; font-size: 22px; font-weight: bold;"
        )
        self.update_log("Nguoi dung nhan EMERGENCY STOP", "error")

    def _on_reset_clicked(self):
        self.is_running = False
        self._play_beep(600, 100)  # Beep ngan
        self._flash_button(self.uic.btn_reset, "#fdd835", "#fff176")
        # Reset counters
        self.uic.lcd_total_unit.display(0)
        self.uic.lcd_pass.display(0)
        self.uic.lcd_ng.display(0)
        self.uic.lcd_yield.display(0)
        self.uic.lcd_elapsed.display(0)
        self.defect_counter = 0
        # Clear table
        self.uic.table_tracking_log.setRowCount(0)
        # Clear monitor
        self.uic.lbl_monitor.clear()
        self.uic.lbl_monitor.setText("")
        # Reset result
        self.uic.lbl_result.setText("WAITING...")
        self.uic.lbl_result.setStyleSheet(
            "color: #888888; background-color: #1a1a2e; "
            "border: 2px solid #444; border-radius: 6px; font-size: 22px; font-weight: bold;"
        )
        self.update_log("Nguoi dung nhan RESET - Da xoa du lieu", "info")

    # ================================================================== #
    #  GHI LOG MAU SAC + TIMESTAMP + TABLE                               #
    # ================================================================== #
    def update_log(self, message, type="info", defect_id=None,
                   error_type="", component="", location=""):
        timestamp = datetime.now().strftime("%H:%M:%S")

        # QListWidget (hidden)
        display_text = f"[{timestamp}] {message}"
        item = QListWidgetItem(display_text)
        if type == "error":
            item.setForeground(QColor("red"))
        else:
            item.setForeground(QColor("black"))
        self.uic.list_tracking_log.addItem(item)
        self.uic.list_tracking_log.scrollToBottom()

        # QTableWidget (hien thi tren giao dien)
        if defect_id is not None:
            row = self.uic.table_tracking_log.rowCount()
            self.uic.table_tracking_log.insertRow(row)

            id_item = QTableWidgetItem(str(defect_id))
            id_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            if type == "error":
                id_item.setForeground(QColor("red"))
            self.uic.table_tracking_log.setItem(row, 0, id_item)

            et_item = QTableWidgetItem(error_type)
            if type == "error":
                et_item.setForeground(QColor("red"))
            self.uic.table_tracking_log.setItem(row, 1, et_item)
            self.uic.table_tracking_log.setItem(row, 2, QTableWidgetItem(component))
            self.uic.table_tracking_log.setItem(row, 3, QTableWidgetItem(location))

            time_item = QTableWidgetItem(timestamp)
            time_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.uic.table_tracking_log.setItem(row, 4, time_item)
            self.uic.table_tracking_log.scrollToBottom()

    # ================================================================== #
    #  WATCHDOG - DOC ANH AN TOAN VOI QTimer DELAY                      #
    # ================================================================== #
    def on_image_detected(self, file_path):
        self.update_log(
            f"Phat hien file: {os.path.basename(file_path)} — "
            f"cho {self.image_load_delay_ms}ms...",
            "info",
        )
        QTimer.singleShot(
            self.image_load_delay_ms,
            lambda fp=file_path: self._load_image(fp),
        )

    def _load_image(self, file_path):
        if not os.path.exists(file_path):
            self.update_log(
                f"File khong ton tai: {os.path.basename(file_path)}", "error"
            )
            return

        # Kiem tra file co dang bi ghi khong (size = 0 hoac khong thay doi)
        try:
            size1 = os.path.getsize(file_path)
            if size1 == 0:
                # Cho them 500ms nua
                QTimer.singleShot(500, lambda fp=file_path: self._load_image(fp))
                return
        except OSError:
            return

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.update_log(
                f"Khong the doc anh: {os.path.basename(file_path)}", "error"
            )
            return

        # Scale anh vua voi lbl_monitor
        label_size = self.uic.lbl_monitor.size()
        scaled = pixmap.scaled(
            label_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self.uic.lbl_monitor.setPixmap(scaled)
        self.update_log(f"Da tai anh: {os.path.basename(file_path)}", "info")

        # Cap nhat Total Unit
        current_val = self.uic.lcd_total_unit.value()
        self.uic.lcd_total_unit.display(current_val + 1)

        # Phat am thanh bao co anh moi
        self._play_beep(1000, 80)

    # ================================================================== #
    #  DONG CUA - Dung Watchdog thread                                  #
    # ================================================================== #
    def closeEvent(self, event):
        self.worker.stop()
        self.worker.wait(2000)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Dark theme cho toan ung dung
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 120, 212))
    app.setPalette(palette)

    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
