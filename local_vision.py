"""
Local Vision System - Local First, AI Fallback
Reads images, PDFs, screenshots using LOCAL tools first.
Only uses AI models when local tools can't handle it.
RAM-aware: picks smallest model based on complexity.
"""
import os
import io
import base64
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger("local_vision")

# ─────────────────────────────────────────────────────────────
# COMPLEXITY LEVELS (determines which model to use)
# ─────────────────────────────────────────────────────────────
@dataclass
class ComplexityLevel:
    name: str
    max_ram_mb: int
    model: str
    description: str

COMPLEXITY = {
    "trivial": ComplexityLevel("trivial", 0, "none", "Local tools only, no AI needed"),
    "simple": ComplexityLevel("simple", 200, "moondream:1.8b", "Basic image understanding"),
    "moderate": ComplexityLevel("moderate", 500, "gemma3:4b", "Complex scenes, documents"),
    "heavy": ComplexityLevel("heavy", 1200, "gemma3:4b", "Detailed analysis, OCR correction"),
}

# ─────────────────────────────────────────────────────────────
# LOCAL TOOLS (No AI needed, instant, zero RAM)
# ─────────────────────────────────────────────────────────────
class LocalOCR:
    """Tesseract OCR - reads text from images locally."""
    
    def __init__(self):
        self.available = False
        self.tesseract_path = self._find_tesseract()
    
    def _find_tesseract(self) -> Optional[str]:
        """Find Tesseract installation."""
        # Common paths
        paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser("~\\AppData\\Local\\Tesseract-OCR\\tesseract.exe"),
        ]
        for p in paths:
            if os.path.exists(p):
                self.available = True
                return p
        # Try PATH
        try:
            subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5)
            self.available = True
            return "tesseract"
        except:
            return None
    
    def read_text(self, image_path: str, lang: str = "eng+hin") -> Dict[str, Any]:
        """Extract text from image using Tesseract."""
        if not self.available:
            return {"success": False, "error": "Tesseract not installed", "fallback": "ai_model"}
        
        try:
            result = subprocess.run(
                [self.tesseract_path, image_path, "stdout", "-l", lang],
                capture_output=True, text=True, timeout=30
            )
            text = result.stdout.strip()
            return {
                "success": True,
                "text": text,
                "method": "tesseract_ocr",
                "complexity": "trivial",
                "ai_needed": False
            }
        except Exception as e:
            return {"success": False, "error": str(e), "fallback": "ai_model"}
    
    def read_image_info(self, image_path: str) -> Dict[str, Any]:
        """Get image metadata using Pillow (no AI needed)."""
        try:
            from PIL import Image
            img = Image.open(image_path)
            return {
                "success": True,
                "format": img.format,
                "mode": img.mode,
                "size": img.size,
                "info": {k: str(v)[:100] for k, v in img.info.items()},
                "method": "pillow_metadata",
                "complexity": "trivial",
                "ai_needed": False
            }
        except ImportError:
            return {"success": False, "error": "Pillow not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class LocalPDFReader:
    """Read PDFs locally without AI."""
    
    def __init__(self):
        self.engine = self._init_engine()
    
    def _init_engine(self):
        """Try PyMuPDF first, then pdfplumber, then PyPDF2."""
        try:
            import fitz  # PyMuPDF
            return "pymupdf"
        except ImportError:
            pass
        try:
            import pdfplumber
            return "pdfplumber"
        except ImportError:
            pass
        try:
            import PyPDF2
            return "pypdf2"
        except ImportError:
            pass
        return None
    
    def read_text(self, pdf_path: str, pages: Optional[list] = None) -> Dict[str, Any]:
        """Extract text from PDF locally."""
        if not self.engine:
            return {"success": False, "error": "No PDF library installed", "fallback": "ai_model"}
        
        try:
            if self.engine == "pymupdf":
                return self._read_pymupdf(pdf_path, pages)
            elif self.engine == "pdfplumber":
                return self._read_pdfplumber(pdf_path, pages)
            elif self.engine == "pypdf2":
                return self._read_pypdf2(pdf_path, pages)
        except Exception as e:
            return {"success": False, "error": str(e), "fallback": "ai_model"}
    
    def _read_pymupdf(self, pdf_path, pages):
        import fitz
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        texts = []
        page_range = pages or range(total_pages)
        
        for i in page_range:
            if i < total_pages:
                page = doc[i]
                text = page.get_text()
                if text.strip():
                    texts.append({"page": i+1, "text": text.strip()})
        
        doc.close()
        full_text = "\n\n".join([t["text"] for t in texts])
        
        return {
            "success": True,
            "text": full_text,
            "pages": texts,
            "total_pages": total_pages,
            "method": "pymupdf",
            "complexity": "trivial",
            "ai_needed": False
        }
    
    def _read_pdfplumber(self, pdf_path, pages):
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            texts = []
            page_range = pages or range(total_pages)
            
            for i in page_range:
                if i < total_pages:
                    text = pdf.pages[i].extract_text()
                    if text and text.strip():
                        texts.append({"page": i+1, "text": text.strip()})
            
            full_text = "\n\n".join([t["text"] for t in texts])
            return {
                "success": True,
                "text": full_text,
                "pages": texts,
                "total_pages": total_pages,
                "method": "pdfplumber",
                "complexity": "trivial",
                "ai_needed": False
            }
    
    def _read_pypdf2(self, pdf_path, pages):
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        texts = []
        page_range = pages or range(total_pages)
        
        for i in page_range:
            if i < total_pages:
                text = reader.pages[i].extract_text()
                if text and text.strip():
                    texts.append({"page": i+1, "text": text.strip()})
        
        full_text = "\n\n".join([t["text"] for t in texts])
        return {
            "success": True,
            "text": full_text,
            "pages": texts,
            "total_pages": total_pages,
            "method": "pypdf2",
            "complexity": "trivial",
            "ai_needed": False
        }
    
    def get_page_as_image(self, pdf_path: str, page_num: int) -> Optional[str]:
        """Convert PDF page to image for AI analysis if needed."""
        try:
            import fitz
            doc = fitz.open(pdf_path)
            if page_num < len(doc):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                b64 = base64.b64encode(img_data).decode()
                doc.close()
                return b64
            doc.close()
        except:
            pass
        return None


class LocalScreenshot:
    """Capture screenshots locally."""
    
    def __init__(self):
        self.backend = self._init_backend()
    
    def _init_backend(self):
        try:
            import mss
            return "mss"
        except ImportError:
            pass
        try:
            import pyautogui
            return "pyautogui"
        except ImportError:
            pass
        return None
    
    def capture(self, region: Optional[tuple] = None) -> Dict[str, Any]:
        """Capture screenshot."""
        if not self.backend:
            return {"success": False, "error": "No screenshot library"}
        
        try:
            if self.backend == "mss":
                return self._capture_mss(region)
            elif self.backend == "pyautogui":
                return self._capture_pyautogui(region)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _capture_mss(self, region):
        import mss
        import mss.tools
        with mss.mss() as sct:
            if region:
                monitor = {"left": region[0], "top": region[1], 
                          "width": region[2], "height": region[3]}
            else:
                monitor = sct.monitors[1]
            img = sct.grab(monitor)
            png = mss.tools.to_png(img.rgb, img.size)
            b64 = base64.b64encode(png).decode()
            return {
                "success": True,
                "image_base64": b64,
                "size": (img.width, img.height),
                "method": "mss",
                "complexity": "trivial"
            }
    
    def _capture_pyautogui(self, region):
        import pyautogui
        img = pyautogui.screenshot(region=region)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return {
            "success": True,
            "image_base64": b64,
            "size": img.size,
            "method": "pyautogui",
            "complexity": "trivial"
        }


# ─────────────────────────────────────────────────────────────
# SMART COMPLEXITY ANALYZER
# ─────────────────────────────────────────────────────────────
def analyze_complexity(file_path: str = None, task: str = "", 
                       content_type: str = "") -> ComplexityLevel:
    """Determine if we need AI or local tools are enough."""
    
    # Simple tasks - local tools only
    simple_keywords = ["read text", "extract text", "ocr", "get text", "text padho"]
    if any(kw in task.lower() for kw in simple_keywords):
        return COMPLEXITY["trivial"]
    
    # PDF text extraction - local
    if content_type == "pdf" or (file_path and file_path.endswith(".pdf")):
        if "image" not in task.lower() and "visual" not in task.lower():
            return COMPLEXITY["trivial"]
    
    # Simple image info - local
    if task.lower() in ["info", "metadata", "size", "format"]:
        return COMPLEXITY["trivial"]
    
    # Understanding/description tasks - need AI
    understand_keywords = ["samjho", "understand", "describe", "explain", "kya hai", 
                           "what is", "batao", "analyze", "review"]
    if any(kw in task.lower() for kw in understand_keywords):
        if "simple" in task.lower() or "quick" in task.lower():
            return COMPLEXITY["simple"]
        return COMPLEXITY["moderate"]
    
    # Default - try local first
    return COMPLEXITY["trivial"]


# ─────────────────────────────────────────────────────────────
# SMART VISION DISPATCHER
# ─────────────────────────────────────────────────────────────
class SmartVision:
    """Smart dispatcher - local tools first, AI fallback."""
    
    def __init__(self):
        self.ocr = LocalOCR()
        self.pdf_reader = LocalPDFReader()
        self.screenshot = LocalScreenshot()
        self._model_cache = {}
    
    def read_file(self, file_path: str, task: str = "read text") -> Dict[str, Any]:
        """
        Smart file reading:
        1. Try local tools first (instant, free, no RAM)
        2. Only use AI if local fails or task requires understanding
        """
        path = Path(file_path)
        
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        
        ext = path.suffix.lower()
        complexity = analyze_complexity(file_path, task)
        
        result = {
            "file": file_path,
            "task": task,
            "complexity": complexity.name,
            "method": "local",
            "ai_needed": False
        }
        
        # ── PDF ──
        if ext == ".pdf":
            pdf_result = self.pdf_reader.read_text(file_path)
            if pdf_result["success"]:
                result.update(pdf_result)
                
                # If task needs understanding and text is long, suggest AI
                if complexity.name != "trivial" and len(pdf_result.get("text", "")) > 500:
                    result["ai_suggestion"] = "Text extracted. Use AI for detailed understanding?"
                    result["ai_model"] = complexity.model
                
                return result
            else:
                # PDF read failed, try AI
                result["method"] = "ai_fallback"
                result["ai_needed"] = True
                result["ai_model"] = complexity.model
                result["error"] = pdf_result.get("error")
                return result
        
        # ── Image ──
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"]:
            # Step 1: Get image info (always local)
            info = self.ocr.read_image_info(file_path)
            result["image_info"] = info
            
            # Step 2: Try OCR (local)
            if "text" in task.lower() or "read" in task.lower() or "ocr" in task.lower():
                ocr_result = self.ocr.read_text(file_path)
                if ocr_result["success"]:
                    result["text"] = ocr_result["text"]
                    result["ocr_method"] = ocr_result["method"]
                    return result
            
            # Step 3: If task needs understanding, use AI
            if complexity.name != "trivial":
                result["method"] = "ai_fallback"
                result["ai_needed"] = True
                result["ai_model"] = complexity.model
            
            return result
        
        # ── Text files - always local ──
        if ext in [".txt", ".md", ".py", ".js", ".ts", ".json", ".xml", 
                   ".html", ".css", ".csv", ".log", ".yaml", ".yml"]:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                result["text"] = text
                result["method"] = "local_file_read"
                return result
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # ── Unknown format - need AI ──
        result["method"] = "ai_fallback"
        result["ai_needed"] = True
        result["ai_model"] = complexity.model
        return result
    
    def read_screenshot(self, task: str = "describe") -> Dict[str, Any]:
        """Capture and analyze screenshot."""
        # Step 1: Capture (local)
        capture = self.screenshot.capture()
        if not capture["success"]:
            return capture
        
        result = {
            "captured": True,
            "size": capture["size"],
            "method": "local_capture"
        }
        
        # Step 2: Analyze complexity
        complexity = analyze_complexity(task=task)
        
        if complexity.name == "trivial":
            # Just return the image, no AI needed
            result["image_base64"] = capture["image_base64"]
            result["ai_needed"] = False
        else:
            # Need AI to understand
            result["image_base64"] = capture["image_base64"]
            result["ai_needed"] = True
            result["ai_model"] = complexity.model
            result["complexity"] = complexity.name
        
        return result
    
    def get_model_for_task(self, task: str, ram_available_mb: int = 4000) -> str:
        """Pick the right model based on task complexity and available RAM."""
        complexity = analyze_complexity(task=task)
        
        # If local tools enough, no model needed
        if complexity.name == "trivial":
            return "none"
        
        # Check RAM and pick appropriate model
        if ram_available_mb < 200:
            return "none"  # Too low RAM, use local only
        
        if ram_available_mb < 500:
            return "moondream:1.8b"  # Smallest vision model
        
        if ram_available_mb < 1500:
            return "gemma3:4b"  # Medium vision model
        
        return "gemma3:4b"  # Best available


# ─────────────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────────────
smart_vision = SmartVision()
