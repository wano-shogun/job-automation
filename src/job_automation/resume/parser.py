"""Parse resume files (PDF, DOCX, TXT) into structured data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from anthropic import Anthropic


@dataclass
class ResumeSection:
    """A section of a resume."""

    title: str
    content: str


@dataclass
class ParsedResume:
    """Parsed resume with sections."""

    raw_text: str
    sections: dict[str, str]  # e.g. {"experience": "...", "skills": "..."}
    skills: list[str]
    experience_years: int
    summary: str


class ResumeParser:
    """Parse resume files into structured data."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize parser."""
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()

    def parse_resume(self, file_path: str | Path) -> ParsedResume:
        """Parse a resume file.

        Args:
            file_path: Path to resume (PDF, DOCX, or TXT)

        Returns:
            ParsedResume with extracted information
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Resume file not found: {file_path}")

        # Read file content
        if file_path.suffix.lower() == ".pdf":
            text = self._extract_pdf(file_path)
        elif file_path.suffix.lower() in [".docx", ".doc"]:
            text = self._extract_docx(file_path)
        else:  # Assume txt
            text = file_path.read_text()

        # Use Claude to structure the resume
        return self._structure_resume(text)

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF."""
        try:
            import PyPDF2

            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except ImportError:
            raise ImportError(
                "PyPDF2 required for PDF parsing. Install with: pip install PyPDF2"
            )

    def _extract_docx(self, file_path: Path) -> str:
        """Extract text from DOCX."""
        try:
            from docx import Document

            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except ImportError:
            raise ImportError(
                "python-docx required for DOCX parsing. Install with: pip install python-docx"
            )

    def _structure_resume(self, text: str) -> ParsedResume:
        """Structure resume text using Claude."""
        prompt = f"""Parse this resume and extract structured information:

RESUME:
{text}

Extract and return:
1. All sections (Experience, Skills, Education, etc)
2. List of technical skills
3. Years of experience
4. Brief summary (2-3 sentences)

Format as JSON."""

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )

        result = response.content[0].text

        # Parse Claude's response
        return self._parse_claude_response(text, result)

    def _parse_claude_response(self, original_text: str, response: str) -> ParsedResume:
        """Parse Claude's structured response."""
        import json
        import re

        # Extract JSON from response
        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {}
        except json.JSONDecodeError:
            data = {}

        return ParsedResume(
            raw_text=original_text,
            sections=data.get("sections", {}),
            skills=data.get("skills", []),
            experience_years=data.get("experience_years", 0),
            summary=data.get("summary", ""),
        )
