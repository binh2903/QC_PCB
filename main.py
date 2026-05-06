import sys
import os
import winsound
import platform
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QListWidgetItem, QTableWidgetItem,
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QSlider, QGroupBox, QTableWidget, QHeaderView, QFrame, QMessageBox
)
from PyQt6.QtGui import QPixmap, QColor, QPalette, QFont
from PyQt6 import QtCore
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt
from ui_main import Ui_MainWindow
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ====================================================================== #
#  SDK CAMERA - Them duong dan de import MvCameraControl                 #
# ====================================================================== #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SDK_PYTHON_DIR = os.path.join(BASE_DIR, "Development", "Samples", "Python")
MvImport_DIR = os.path.join(SDK_PYTHON_DIR, "MvImport")

# Them duong dan vao sys.path neu ton tai
if os.path.isdir(MvImport_DIR):
    if MvImport_DIR not in sys.path:
        sys.path.insert(0, MvImport_DIR)

try:
    from MvCameraControl_class import *
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("[WARNING] MvCameraControl_class khong tim thay. Camera SDK se hoat dong o che do demo.")


def decoding_char(ctypes_char_array):
    """Doc ky tu tu ctypes char array (tu SDK)."""
    try:
        byte_str = memoryview(ctypes_char_array).tobytes()
        null_index = byte_str.find(b'\x00')
        if null_index != -1:
            byte_str = byte_str[:null_index]
        for enc in ['utf-8', 'gbk', 'latin-1']:
            try:
                return byte_str.decode(enc)
            except UnicodeDecodeError:
                continue
        return byte_str.decode('latin-1', errors='replace')
    except Exception:
        return "Unknown"

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

        # ---- PAGE SWITCHING ----
        self.current_page = 1
        self.uic.btn_nav_inspection.clicked.connect(lambda: self._switch_page(1))
        self.uic.btn_nav_settings.clicked.connect(lambda: self._switch_page(2))

        # ---- Tao giao dien PAGE 2 (Camera Settings) ----
        self._create_page2()
        self._update_page_buttons()
        # An page 2 ban dau
        self.page2_widget.hide()

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
        self.uic.page_inspection.setGeometry(margin, main_top, left_w, main_h)

        # CAM_VIEW: chiem het INSPECTOR tru 70px cho nut
        btn_area_h = 70
        cam_h = main_h - btn_area_h - 10
        self.uic.CAM_VIEW.setGeometry(0, 0, left_w, cam_h)

        # lbl_monitor_inspect (fill CAM_VIEW)
        self.uic.lbl_monitor_inspect.setGeometry(5, 5, left_w - 10, cam_h - 10)

        # 3 NUT BAM (chia deu)
        btn_y = cam_h + 8
        btn_h = btn_area_h - 18
        btn_gap = 8
        btn_w = (left_w - btn_gap * 2) // 3
        self.uic.btn_start.setGeometry(0, btn_y, btn_w, btn_h)
        self.uic.btn_reset.setGeometry(btn_w + btn_gap, btn_y, btn_w, btn_h)
        self.uic.btn_stop.setGeometry((btn_w + btn_gap) * 2, btn_y, btn_w, btn_h)

        # ---- RIGHT PANEL ----
        # Note: Right panel (tracking_log_group and counter_group) is part of page_inspection

        # Tracking log group: 58% of right panel height
        log_h = int(main_h * 0.58)
        # Note: Geometry setting on layout-managed widgets may override layout
        # self.uic.tracking_log_group.setGeometry(0, 0, right_w, log_h)
        # self.uic.table_tracking_log.setGeometry(0, 30, right_w, log_h - 65)
        # self.uic.btn_add_log.setGeometry(right_w - 180, log_h - 30, 80, 26)
        # self.uic.btn_delete_log.setGeometry(right_w - 90, log_h - 30, 80, 26)

        # Counter group: phan con lai
        counter_y = log_h + 5
        counter_h = main_h - log_h - 5
        # self.uic.counter_group.setGeometry(0, counter_y, right_w, counter_h)

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

        # ---- PAGE 2 LAYOUT (neu dang hien thi) ----
        if self.current_page == 2:
            self._do_page2_layout()

    # ================================================================== #
    #  PAGE SWITCHING - Chuyen giua trang 1 va trang 2                   #
    # ================================================================== #
    def _switch_page(self, page):
        """Chuyen giua trang 1 (Quan sat) va trang 2 (Cai dat Camera)."""
        if page == self.current_page:
            return
        self.current_page = page
        self._update_page_buttons()
        if page == 1:
            # An page 2, hien page 1
            self.page2_widget.hide()
            self.uic.stackedWidget.setCurrentIndex(0)
            self.update_log("Chuyen sang trang QUAN SAT", "info")
        else:
            # An page 1, hien page 2
            self.uic.stackedWidget.setCurrentIndex(1)
            self.page2_widget.show()
            self._do_page2_layout()
            self.update_log("Chuyen sang trang CAI DAT CAMERA", "info")
            # Quet camera khi vao trang 2
            if self.current_page == 2:
                self._refresh_camera_list()

    def _update_page_buttons(self):
        """Cap nhat mau nut page theo trang hien tai."""
        if self.current_page == 1:
            self.uic.btn_nav_inspection.setStyleSheet(
                "QPushButton { background-color: #00e676; color: #1e1e1e; border-radius: 4px; "
                "border: 1px solid #00e676; font-weight: bold; } "
                "QPushButton:hover { background-color: #69f0ae; }"
            )
            self.uic.btn_nav_settings.setStyleSheet(
                "QPushButton { background-color: #424242; color: #aaaaaa; border-radius: 4px; "
                "border: 1px solid #555; } QPushButton:hover { background-color: #616161; }"
            )
        else:
            self.uic.btn_nav_inspection.setStyleSheet(
                "QPushButton { background-color: #424242; color: #aaaaaa; border-radius: 4px; "
                "border: 1px solid #555; } QPushButton:hover { background-color: #616161; }"
            )
            self.uic.btn_nav_settings.setStyleSheet(
                "QPushButton { background-color: #42a5f5; color: #1e1e1e; border-radius: 4px; "
                "border: 1px solid #42a5f5; font-weight: bold; } "
                "QPushButton:hover { background-color: #90caf9; }"
            )

    # ================================================================== #
    #  PAGE 2 - TAO GIAO DIEN CAI DAT CAMERA                            #
    # ================================================================== #
    def _create_page2(self):
        """Tao toan bo giao dien trang 2 - Camera Settings."""
        self.page2_widget = QWidget(self.uic.centralwidget)
        self.page2_widget.setStyleSheet("background: transparent;")

        # ---- Camera Selection Group ----
        self.cam_group = QGroupBox("CHON CAMERA", self.page2_widget)
        self.cam_group.setStyleSheet(
            "QGroupBox { color: #42a5f5; font-size: 13px; font-weight: bold; "
            "border: 1px solid #42a5f5; border-radius: 6px; padding-top: 15px; "
            "background-color: rgba(30,30,30,200); } "
            "QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px; }"
        )

        self.lbl_cam_type = QLabel("Loai camera:", self.cam_group)
        self.lbl_cam_type.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.combo_cam_type = QComboBox(self.cam_group)
        self.combo_cam_type.addItems(["USB Camera", "GigE Camera", "Tat ca"])
        self.combo_cam_type.setStyleSheet(
            "QComboBox { background-color: #2b2b2b; color: white; border: 1px solid #555; "
            "border-radius: 4px; padding: 5px 10px; font-size: 11px; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox QAbstractItemView { background-color: #2b2b2b; color: white; }"
        )

        self.lbl_cam_list = QLabel("Danh sach camera:", self.cam_group)
        self.lbl_cam_list.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.combo_cam_list = QComboBox(self.cam_group)
        self.combo_cam_list.setStyleSheet(
            "QComboBox { background-color: #2b2b2b; color: white; border: 1px solid #555; "
            "border-radius: 4px; padding: 5px 10px; font-size: 11px; min-height: 22px; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox QAbstractItemView { background-color: #2b2b2b; color: white; }"
        )

        self.btn_refresh_cam = QPushButton("Quet lai", self.cam_group)
        self.btn_refresh_cam.setStyleSheet(
            "QPushButton { background-color: #42a5f5; color: #1e1e1e; border-radius: 4px; "
            "padding: 6px 16px; font-weight: bold; font-size: 11px; } "
            "QPushButton:hover { background-color: #90caf9; }"
        )
        self.btn_refresh_cam.clicked.connect(self._refresh_camera_list)

        # ---- Camera Parameters Group ----
        self.param_group = QGroupBox("THONG SO CAMERA", self.page2_widget)
        self.param_group.setStyleSheet(
            "QGroupBox { color: #00e676; font-size: 13px; font-weight: bold; "
            "border: 1px solid #00e676; border-radius: 6px; padding-top: 15px; "
            "background-color: rgba(30,30,30,200); } "
            "QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px; }"
        )

        # Exposure
        self.lbl_exposure = QLabel("Exposure (us):", self.param_group)
        self.lbl_exposure.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.slider_exposure = QSlider(Qt.Orientation.Horizontal, self.param_group)
        self.slider_exposure.setRange(100, 100000)
        self.slider_exposure.setValue(10000)
        self.slider_exposure.setStyleSheet(
            "QSlider::groove:horizontal { background: #444; height: 6px; border-radius: 3px; } "
            "QSlider::handle:horizontal { background: #00e676; width: 14px; margin: -4px 0; "
            "border-radius: 7px; } "
            "QSlider::sub-page:horizontal { background: #00e676; border-radius: 3px; }"
        )
        self.lbl_exposure_val = QLabel("10000", self.param_group)
        self.lbl_exposure_val.setStyleSheet("color: #00e676; font-weight: bold; font-size: 11px; background: transparent;")
        self.slider_exposure.valueChanged.connect(
            lambda v: self.lbl_exposure_val.setText(str(v))
        )

        # Gain
        self.lbl_gain = QLabel("Gain (dB):", self.param_group)
        self.lbl_gain.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.slider_gain = QSlider(Qt.Orientation.Horizontal, self.param_group)
        self.slider_gain.setRange(0, 480)
        self.slider_gain.setValue(0)
        self.slider_gain.setStyleSheet(
            "QSlider::groove:horizontal { background: #444; height: 6px; border-radius: 3px; } "
            "QSlider::handle:horizontal { background: #fdd835; width: 14px; margin: -4px 0; "
            "border-radius: 7px; } "
            "QSlider::sub-page:horizontal { background: #fdd835; border-radius: 3px; }"
        )
        self.lbl_gain_val = QLabel("0.0", self.param_group)
        self.lbl_gain_val.setStyleSheet("color: #fdd835; font-weight: bold; font-size: 11px; background: transparent;")
        self.slider_gain.valueChanged.connect(
            lambda v: self.lbl_gain_val.setText(f"{v/10:.1f}")
        )

        # White Balance
        self.lbl_wb = QLabel("White Balance:", self.param_group)
        self.lbl_wb.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.combo_wb = QComboBox(self.param_group)
        self.combo_wb.addItems(["Off", "Auto", "Manual - 2800K", "Manual - 6500K"])
        self.combo_wb.setStyleSheet(
            "QComboBox { background-color: #2b2b2b; color: white; border: 1px solid #555; "
            "border-radius: 4px; padding: 5px 10px; font-size: 11px; } "
            "QComboBox::drop-down { border: none; } "
            "QComboBox QAbstractItemView { background-color: #2b2b2b; color: white; }"
        )

        # Gamma
        self.lbl_gamma = QLabel("Gamma:", self.param_group)
        self.lbl_gamma.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.slider_gamma = QSlider(Qt.Orientation.Horizontal, self.param_group)
        self.slider_gamma.setRange(10, 300)
        self.slider_gamma.setValue(100)
        self.slider_gamma.setStyleSheet(
            "QSlider::groove:horizontal { background: #444; height: 6px; border-radius: 3px; } "
            "QSlider::handle:horizontal { background: #ce93d8; width: 14px; margin: -4px 0; "
            "border-radius: 7px; } "
            "QSlider::sub-page:horizontal { background: #ce93d8; border-radius: 3px; }"
        )
        self.lbl_gamma_val = QLabel("1.00", self.param_group)
        self.lbl_gamma_val.setStyleSheet("color: #ce93d8; font-weight: bold; font-size: 11px; background: transparent;")
        self.slider_gamma.valueChanged.connect(
            lambda v: self.lbl_gamma_val.setText(f"{v/100:.2f}")
        )

        # ---- Action Buttons Group ----
        self.action_group = QGroupBox("THAO TAC", self.page2_widget)
        self.action_group.setStyleSheet(
            "QGroupBox { color: #fdd835; font-size: 13px; font-weight: bold; "
            "border: 1px solid #fdd835; border-radius: 6px; padding-top: 15px; "
            "background-color: rgba(30,30,30,200); } "
            "QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px; }"
        )

        self.btn_connect = QPushButton("Ket noi Camera", self.action_group)
        self.btn_connect.setStyleSheet(
            "QPushButton { background-color: #00c853; color: white; border-radius: 4px; "
            "padding: 10px; font-size: 12px; font-weight: bold; } "
            "QPushButton:hover { background-color: #00e676; }"
        )
        self.btn_connect.clicked.connect(self._on_connect_camera)

        self.btn_disconnect = QPushButton("Ngat ket noi", self.action_group)
        self.btn_disconnect.setStyleSheet(
            "QPushButton { background-color: #e53935; color: white; border-radius: 4px; "
            "padding: 10px; font-size: 12px; font-weight: bold; } "
            "QPushButton:hover { background-color: #ff5252; }"
        )
        self.btn_disconnect.clicked.connect(self._on_disconnect_camera)
        self.btn_disconnect.setEnabled(False)

        self.btn_apply_params = QPushButton("Ap dung tham so", self.action_group)
        self.btn_apply_params.setStyleSheet(
            "QPushButton { background-color: #42a5f5; color: #1e1e1e; border-radius: 4px; "
            "padding: 10px; font-size: 12px; font-weight: bold; } "
            "QPushButton:hover { background-color: #90caf9; }"
        )
        self.btn_apply_params.clicked.connect(self._on_apply_params)

        self.btn_grab_image = QPushButton("Chup anh thu", self.action_group)
        self.btn_grab_image.setStyleSheet(
            "QPushButton { background-color: #ab47bc; color: white; border-radius: 4px; "
            "padding: 10px; font-size: 12px; font-weight: bold; } "
            "QPushButton:hover { background-color: #ce93d8; }"
        )
        self.btn_grab_image.clicked.connect(self._on_grab_test_image)

        # ---- Status / Info Group ----
        self.info_group = QGroupBox("THONG TIN HE THONG", self.page2_widget)
        self.info_group.setStyleSheet(
            "QGroupBox { color: #aaaaaa; font-size: 13px; font-weight: bold; "
            "border: 1px solid #555; border-radius: 6px; padding-top: 15px; "
            "background-color: rgba(30,30,30,200); } "
            "QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px; }"
        )

        self.lbl_sdk_ver = QLabel("SDK Version: --", self.info_group)
        self.lbl_sdk_ver.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.lbl_cam_status = QLabel("Trang thai: Chua ket noi", self.info_group)
        self.lbl_cam_status.setStyleSheet("color: #e53935; font-size: 11px; font-weight: bold; background: transparent;")
        self.lbl_cam_model = QLabel("Model: --", self.info_group)
        self.lbl_cam_model.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.lbl_cam_ip = QLabel("IP: --", self.info_group)
        self.lbl_cam_ip.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")
        self.lbl_cam_sn = QLabel("Serial: --", self.info_group)
        self.lbl_cam_sn.setStyleSheet("color: #aaa; font-size: 11px; background: transparent;")

        # ---- Preview Group (right side) ----
        self.preview_group = QGroupBox("XEM TRUOC", self.page2_widget)
        self.preview_group.setStyleSheet(
            "QGroupBox { color: #00e676; font-size: 13px; font-weight: bold; "
            "border: 2px solid #00e676; border-radius: 6px; padding-top: 15px; "
            "background-color: #000000; } "
            "QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px; }"
        )
        self.lbl_preview = QLabel("Chua co anh preview", self.preview_group)
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setStyleSheet("color: #555; font-size: 14px; background: transparent;")

        # ---- Camera Device Info Table ----
        self.table_cam_info = QTableWidget(self.page2_widget)
        self.table_cam_info.setColumnCount(3)
        self.table_cam_info.setHorizontalHeaderLabels(["Thong so", "Gia tri", "Mo ta"])
        self.table_cam_info.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: #2b2b2b; color: #42a5f5; "
            "border: 1px solid #444; padding: 5px; font-weight: bold; }"
        )
        self.table_cam_info.setStyleSheet(
            "QTableWidget { background-color: #1e1e1e; color: white; gridline-color: #444; "
            "border: 1px solid #444; border-radius: 4px; } "
            "QTableWidget::item { padding: 4px; } "
            "QTableWidget::item:selected { background-color: #42a5f5; }"
        )
        self.table_cam_info.verticalHeader().setVisible(False)
        self.table_cam_info.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_cam_info.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # SDK khong ket noi - an bang thong tin
        if not SDK_AVAILABLE:
            self.lbl_sdk_ver.setText("SDK Version: SDK chua cai dat")
            self.lbl_cam_status.setText("Trang thai: SDK khong kha dung (Demo mode)")
            self.lbl_cam_status.setStyleSheet("color: #fdd835; font-size: 11px; font-weight: bold; background: transparent;")

    def _do_page2_layout(self):
        """Tinh toan layout cho page 2 theo kich thuoc window."""
        w = self.width()
        h = self.height()
        margin = 15
        main_top = 85  # title bar + 5px
        main_h = h - main_top - 10
        main_w = w - margin * 2

        self.page2_widget.setGeometry(margin, main_top, main_w, main_h)

        # Left side: Camera selection + Parameters + Actions + Info (55% width)
        left_w = int(main_w * 0.45)
        right_x = left_w + 15
        right_w = main_w - left_w - 15

        # ---- Camera Selection Group ----
        cam_h = 150
        self.cam_group.setGeometry(0, 0, left_w, cam_h)
        self.lbl_cam_type.setGeometry(15, 22, 90, 25)
        self.combo_cam_type.setGeometry(110, 22, 120, 28)
        self.lbl_cam_list.setGeometry(15, 60, 110, 25)
        self.combo_cam_list.setGeometry(15, 88, left_w - 140, 30)
        self.btn_refresh_cam.setGeometry(left_w - 110, 88, 95, 30)

        # ---- Camera Parameters Group ----
        param_y = cam_h + 10
        param_h = main_h - cam_h - 10
        self.param_group.setGeometry(0, param_y, left_w, param_h)

        # Param sliders
        p_margin = 15
        p_label_w = 90
        p_slider_w = left_w - p_label_w - 80
        p_val_w = 60

        row_h = 55
        # Exposure
        self.lbl_exposure.setGeometry(p_margin, 22, p_label_w, 22)
        self.slider_exposure.setGeometry(p_margin + p_label_w + 5, 22, p_slider_w, 22)
        self.lbl_exposure_val.setGeometry(p_margin + p_label_w + p_slider_w + 15, 22, p_val_w, 22)

        # Gain
        self.lbl_gain.setGeometry(p_margin, 22 + row_h, p_label_w, 22)
        self.slider_gain.setGeometry(p_margin + p_label_w + 5, 22 + row_h, p_slider_w, 22)
        self.lbl_gain_val.setGeometry(p_margin + p_label_w + p_slider_w + 15, 22 + row_h, p_val_w, 22)

        # White Balance
        self.lbl_wb.setGeometry(p_margin, 22 + row_h * 2, p_label_w, 22)
        self.combo_wb.setGeometry(p_margin + p_label_w + 5, 22 + row_h * 2, p_slider_w, 28)

        # Gamma
        self.lbl_gamma.setGeometry(p_margin, 22 + row_h * 3, p_label_w, 22)
        self.slider_gamma.setGeometry(p_margin + p_label_w + 5, 22 + row_h * 3, p_slider_w, 22)
        self.lbl_gamma_val.setGeometry(p_margin + p_label_w + p_slider_w + 15, 22 + row_h * 3, p_val_w, 22)

        # ---- Right side: Preview + Info + Actions ----
        # Preview (top 55%)
        preview_h = int(main_h * 0.50)
        self.preview_group.setGeometry(right_x, 0, right_w, preview_h)
        self.lbl_preview.setGeometry(10, 20, right_w - 20, preview_h - 30)

        # Info table (middle 25%)
        info_y = preview_h + 10
        info_h = int(main_h * 0.22)
        self.table_cam_info.setGeometry(right_x, info_y, right_w, info_h)

        # Action buttons (bottom 20%)
        action_y = info_y + info_h + 10
        action_h = main_h - action_y
        self.action_group.setGeometry(right_x, action_y, right_w, action_h)
        btn_w = (right_w - 50) // 2
        btn_h = max(30, (action_h - 40) // 2)
        btn_gap = 10
        self.btn_connect.setGeometry(15, 22, btn_w, btn_h)
        self.btn_disconnect.setGeometry(15 + btn_w + btn_gap, 22, btn_w, btn_h)
        self.btn_apply_params.setGeometry(15, 22 + btn_h + btn_gap, btn_w, btn_h)
        self.btn_grab_image.setGeometry(15 + btn_w + btn_gap, 22 + btn_h + btn_gap, btn_w, btn_h)

    # ================================================================== #
    #  CAMERA SDK - Quet, Ket noi, Ngat ket noi                         #
    # ================================================================== #
    def _refresh_camera_list(self):
        """Quet danh sach camera ket noi voi may tinh."""
        self.combo_cam_list.clear()

        if not SDK_AVAILABLE:
            self.combo_cam_list.addItem("[Demo] Camera 1 - MVS-500M")
            self.combo_cam_list.addItem("[Demo] Camera 2 - MVS-1200M")
            self.lbl_sdk_ver.setText("SDK Version: Demo Mode (SDK chua cai dat)")
            self.update_log("SDK khong kha dung - Hien thi camera demo", "info")
            return

        try:
            MvCamera.MV_CC_Initialize()
            sdk_ver = MvCamera.MV_CC_GetSDKVersion()
            self.lbl_sdk_ver.setText(f"SDK Version: 0x{sdk_ver:08X}")

            device_list = MV_CC_DEVICE_INFO_LIST()
            tlayer_type = MV_GIGE_DEVICE | MV_USB_DEVICE

            ret = MvCamera.MV_CC_EnumDevices(tlayer_type, device_list)
            if ret != 0:
                self.update_log(f"Loi quet camera: ret=0x{ret:08X}", "error")
                return

            if device_list.nDeviceNum == 0:
                self.combo_cam_list.addItem("Khong tim thay camera nao!")
                self.update_log("Khong tim thay camera nao", "error")
                return

            for i in range(device_list.nDeviceNum):
                mvcc_dev_info = cast(
                    device_list.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)
                ).contents
                if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE:
                    model = decoding_char(mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName)
                    ip_raw = mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp
                    ip = f"{(ip_raw >> 24) & 0xff}.{(ip_raw >> 16) & 0xff}.{(ip_raw >> 8) & 0xff}.{ip_raw & 0xff}"
                    self.combo_cam_list.addItem(f"[GigE] {model} ({ip})")
                elif mvcc_dev_info.nTLayerType == MV_USB_DEVICE:
                    model = decoding_char(mvcc_dev_info.SpecialInfo.stUsb3VInfo.chModelName)
                    serial = decoding_char(mvcc_dev_info.SpecialInfo.stUsb3VInfo.chSerialNumber)
                    self.combo_cam_list.addItem(f"[USB] {model} (SN:{serial})")

            self.update_log(f"Tim thay {device_list.nDeviceNum} camera", "info")

        except Exception as e:
            self.update_log(f"Loi quet camera: {str(e)}", "error")

    def _on_connect_camera(self):
        """Ket noi den camera da chon."""
        if not SDK_AVAILABLE:
            self.lbl_cam_status.setText("Trang thai: Demo mode - Mo phong ket noi")
            self.lbl_cam_status.setStyleSheet("color: #00e676; font-size: 11px; font-weight: bold; background: transparent;")
            self.lbl_cam_model.setText("Model: MVS-500M (Demo)")
            self.btn_connect.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
            self._play_beep(800, 100)
            self.update_log("Demo mode: Mo phong ket noi camera", "info")
            return

        idx = self.combo_cam_list.currentIndex()
        if idx < 0:
            QMessageBox.warning(self, "Canh bao", "Vui long chon camera truoc!")
            return

        self.update_log(f"Dang ket noi camera #{idx}...", "info")
        # Camera connection logic would go here using MvCamera
        self.lbl_cam_status.setText("Trang thai: Dang ket noi...")
        self.lbl_cam_status.setStyleSheet("color: #fdd835; font-size: 11px; font-weight: bold; background: transparent;")

    def _on_disconnect_camera(self):
        """Ngat ket noi camera."""
        self.lbl_cam_status.setText("Trang thai: Da ngat ket noi")
        self.lbl_cam_status.setStyleSheet("color: #e53935; font-size: 11px; font-weight: bold; background: transparent;")
        self.lbl_cam_model.setText("Model: --")
        self.lbl_cam_ip.setText("IP: --")
        self.lbl_cam_sn.setText("Serial: --")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self._play_beep(400, 150)
        self.update_log("Da ngat ket noi camera", "info")

    def _on_apply_params(self):
        """Ap dung tham so camera (Exposure, Gain, WB, Gamma)."""
        exposure = self.slider_exposure.value()
        gain = self.slider_gain.value()
        wb = self.combo_wb.currentText()
        gamma = self.slider_gamma.value()

        self.update_log(
            f"Ap dung tham so: Exposure={exposure}us, Gain={gain/10:.1f}dB, "
            f"WB={wb}, Gamma={gamma/100:.2f}", "info"
        )
        self._play_beep(600, 80)

        # Update info table
        self.table_cam_info.setRowCount(0)
        params = [
            ("Exposure", f"{exposure} us", "Thoi gian phơi sáng"),
            ("Gain", f"{gain/10:.1f} dB", "Muc tang bo sung"),
            ("White Balance", wb, "Can banh mau trang"),
            ("Gamma", f"{gamma/100:.2f}", "Chinh gamma mau sac"),
        ]
        for name, value, desc in params:
            row = self.table_cam_info.rowCount()
            self.table_cam_info.insertRow(row)
            self.table_cam_info.setItem(row, 0, QTableWidgetItem(name))
            val_item = QTableWidgetItem(value)
            val_item.setForeground(QColor("#00e676"))
            self.table_cam_info.setItem(row, 1, val_item)
            self.table_cam_info.setItem(row, 2, QTableWidgetItem(desc))

    def _on_grab_test_image(self):
        """Chup anh thu tu camera (demo mode)."""
        self._play_beep(1000, 50)
        if not SDK_AVAILABLE:
            # Demo: hien thi anh mau
            self.lbl_preview.setText("Demo: Anh mau tu camera\n(Chua ket noi camera that)")
            self.lbl_preview.setStyleSheet("color: #42a5f5; font-size: 14px; font-weight: bold; background: transparent;")
            self.update_log("Demo mode: Mo phong chup anh thu", "info")
        else:
            self.lbl_preview.setText("Dang chup anh...")
            self.update_log("Dang chup anh tu camera...", "info")

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
        self.uic.lbl_monitor_inspect.clear()
        self.uic.lbl_monitor_inspect.setText("")
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

        # Scale anh vua voi lbl_monitor_inspect
        label_size = self.uic.lbl_monitor_inspect.size()
        scaled = pixmap.scaled(
            label_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self.uic.lbl_monitor_inspect.setPixmap(scaled)
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
