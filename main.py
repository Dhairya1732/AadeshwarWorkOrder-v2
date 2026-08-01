import sys
from dotenv import load_dotenv

load_dotenv()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow
from core.config import resource_path

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Work Order Generator")
    app.setOrganizationName("Aadeshwar Enterprises")

    # Load app icon if it exists
    icon_path = resource_path("assets/card_image.png")
    app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()