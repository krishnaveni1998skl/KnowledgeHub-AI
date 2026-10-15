"""
Tesseract OCR fallback module for scanned documents and images.
Rule 8: Starts with Tesseract only, avoiding unnecessary duplicate OCR libraries.
Handles Windows path discovery and graceful fallback when Tesseract is not installed.
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Optional
from PIL import Image
import pytesseract
from app.config import settings

logger = logging.getLogger(__name__)

# Known default installation paths on Windows
COMMON_WINDOWS_TESSERACT_PATHS = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    Path(os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")),
]

def get_tesseract_executable() -> Optional[str]:
    """Finds the tesseract executable on Windows or in PATH."""
    # 1. Custom configured command
    if settings.TESSERACT_CMD and os.path.isfile(settings.TESSERACT_CMD):
        return settings.TESSERACT_CMD

    # 2. In PATH
    which_path = shutil.which("tesseract")
    if which_path:
        return which_path

    # 3. Common Windows paths
    for p in COMMON_WINDOWS_TESSERACT_PATHS:
        if p.is_file():
            return str(p)

    return None

def is_tesseract_available() -> bool:
    """Checks whether Tesseract is installed and usable."""
    exe = get_tesseract_executable()
    return exe is not None

def configure_pytesseract():
    """Configures pytesseract with the discovered executable path."""
    exe = get_tesseract_executable()
    if exe:
        pytesseract.pytesseract.tesseract_cmd = exe

# Attempt auto-configuration on module import
configure_pytesseract()

def ocr_image(image: Image.Image) -> str:
    """
    Runs Tesseract OCR on a PIL Image object.
    Raises RuntimeError if Tesseract is not installed on the system.
    """
    configure_pytesseract()
    if not is_tesseract_available():
        raise RuntimeError(
            "Tesseract OCR is not installed or not found in system PATH. "
            "Please install Tesseract OCR for Windows to process scanned images."
        )

    try:
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"Tesseract OCR execution failed: {e}")
        raise RuntimeError(f"OCR execution failed: {e}")
