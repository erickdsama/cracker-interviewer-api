import os
from pypdf import PdfReader
from docx import Document
from ..core.logger import get_logger

logger = get_logger(__name__)

class ParserService:
    def parse_resume(self, file_input, filename: str = "") -> str:
        """
        Extracts text from a PDF or DOCX file (path or stream).
        """
        try:
            # Determine extension
            if isinstance(file_input, str):
                ext = os.path.splitext(file_input)[1].lower()
                if not os.path.exists(file_input):
                    return ""
                # Open file if it's a path
                with open(file_input, "rb") as f:
                    return self._parse_stream(f, ext)
            else:
                # Assume it's a stream
                if not filename:
                    return "" # Need filename for extension
                ext = os.path.splitext(filename)[1].lower()
                return self._parse_stream(file_input, ext)

        except Exception as e:
            logger.error(f"Error parsing resume: {e}")
            return ""

    def _parse_stream(self, stream, ext: str) -> str:
        try:
            if ext == ".pdf":
                return self._parse_pdf(stream)
            elif ext == ".docx":
                return self._parse_docx(stream)
            else:
                return ""
        except Exception as e:
            raise e

    def _parse_pdf(self, stream) -> str:
        text = ""
        reader = PdfReader(stream)
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def _parse_docx(self, stream) -> str:
        doc = Document(stream)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

parser_service = ParserService()
