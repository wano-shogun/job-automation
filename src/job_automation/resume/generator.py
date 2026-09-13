"""Generate resume files (PDF, DOCX) from text."""

from __future__ import annotations

from pathlib import Path


class ResumeGenerator:
    """Generate resume files in various formats."""

    @staticmethod
    def to_pdf(text: str, output_path: str | Path) -> Path:
        """Generate PDF resume from text.

        Args:
            text: Resume text
            output_path: Output PDF path

        Returns:
            Path to generated PDF
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.units import inch

            doc = SimpleDocTemplate(
                str(output_path), pagesize=letter, topMargin=0.5 * inch
            )
            styles = getSampleStyleSheet()
            story = []

            # Add paragraphs
            for line in text.split("\n"):
                if line.strip():
                    p = Paragraph(line, styles["Normal"])
                    story.append(p)
                    story.append(Spacer(1, 0.1 * inch))

            doc.build(story)
            return output_path

        except ImportError:
            raise ImportError(
                "reportlab required for PDF generation. Install with: pip install reportlab"
            )

    @staticmethod
    def to_docx(text: str, output_path: str | Path) -> Path:
        """Generate DOCX resume from text.

        Args:
            text: Resume text
            output_path: Output DOCX path

        Returns:
            Path to generated DOCX
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            from docx import Document

            doc = Document()

            # Add paragraphs
            for line in text.split("\n"):
                if line.strip():
                    doc.add_paragraph(line)

            doc.save(str(output_path))
            return output_path

        except ImportError:
            raise ImportError(
                "python-docx required for DOCX generation. Install with: pip install python-docx"
            )

    @staticmethod
    def to_txt(text: str, output_path: str | Path) -> Path:
        """Generate TXT resume.

        Args:
            text: Resume text
            output_path: Output TXT path

        Returns:
            Path to generated TXT
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text)
        return output_path

    @staticmethod
    def to_file(
        text: str, output_path: str | Path, format: str = "pdf"
    ) -> Path:
        """Generate resume in specified format.

        Args:
            text: Resume text
            output_path: Output file path
            format: Format (pdf, docx, txt)

        Returns:
            Path to generated file
        """
        generator = ResumeGenerator()

        if format.lower() == "pdf":
            return generator.to_pdf(text, output_path)
        elif format.lower() == "docx":
            return generator.to_docx(text, output_path)
        else:
            return generator.to_txt(text, output_path)
