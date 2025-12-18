import os
from pypdf import PdfReader
from docx import Document

class ParserService:
    def parse_resume(self, file_path: str) -> str:
        """
        Extracts text from a PDF or DOCX file.
        """
        if not os.path.exists(file_path):
            return ""
            
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == ".pdf":
                return self._parse_pdf(file_path)
            elif ext == ".docx":
                return self._parse_docx(file_path)
            else:
                return ""
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return ""

    def _parse_pdf(self, file_path: str) -> str:
        text = ""
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text

    def _parse_docx(self, file_path: str) -> str:
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs])
        return text

parser_service = ParserService()
