"""
PDF Generator - Create formatted PDF documents from text content
Supports multiple formatting styles and uses Roboto Condensed font.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List
from enum import Enum
import re
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

# Try to import ReportLab
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY, TA_CENTER, TA_RIGHT
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.platypus.flowables import Flowable
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("⚠️ ReportLab not installed. PDF generation will not work.")
    logger.warning("   Install with: pip install reportlab")



class PDFFormat(Enum):
    """PDF formatting styles."""
    SIMPLE_TEXT = "simple_text"
    WITH_BULLETS = "with_bullets"
    FORMATTED_PARAGRAPHS = "formatted_paragraphs"


class PDFGenerator:
    """
    Handles PDF document generation with multiple formatting options.
    Uses ReportLab for professional PDF creation.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize PDF Generator.
        
        Args:
            output_dir: Directory to save PDFs (default: Documents/Nexa PDFs)
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError(
                "ReportLab is required for PDF generation. "
                "Install with: pip install reportlab"
            )
        
        # Set output directory
        if output_dir is None:
            documents_path = Path.home() / "Documents"
            self.output_dir = documents_path / "Nexa PDFs"
        else:
            self.output_dir = Path(output_dir)
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # PDF settings
        self.page_size = letter  # or A4
        self.margin = 0.75 * inch
        
        logger.info(f"✨ PDFGenerator initialized - Output: {self.output_dir}")
    
    def _create_credentials_header(
        self,
        styles,
        metadata: dict,
        title: Optional[str] = None
    ) -> list:
        """
        Create credentials header for academic PDFs.
        
        Args:
            styles: ReportLab stylesheet
            metadata: Dict with user info (name, id, course, date, etc.)
            title: Optional assignment title
            
        Returns:
            List of Paragraph and Spacer elements
        """
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        
        story = []
        
        # Create header style (small, gray text)
        header_style = ParagraphStyle(
            'CredentialHeader',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#4A5568'),
            spaceAfter=4,
            alignment=TA_LEFT
        )
        
        # Create separator style
        separator_style = ParagraphStyle(
            'Separator',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#CBD5E0'),
            spaceAfter=12,
            spaceBefore=8
        )
        
        # Add student name (required)
        name = metadata.get('name', 'Student')
        story.append(Paragraph(f"<b>Student Name:</b> {name}", header_style))
        
        # Add student ID (optional)
        student_id = metadata.get('id', None)
        if student_id:
            story.append(Paragraph(f"<b>Student ID:</b> {student_id}", header_style))
        
        # Add course/subject (optional)
        course = metadata.get('course', None)
        if course:
            story.append(Paragraph(f"<b>Course:</b> {course}", header_style))
        
        # Add date (required - auto-generated if not provided)
        date = metadata.get('date', None)
        if not date:
            date = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"<b>Date:</b> {date}", header_style))
        
        # Add assignment title if provided
        if title:
            story.append(Paragraph(f"<b>Assignment:</b> {title}", header_style))
        
        # Add separator line
        story.append(Paragraph("─" * 60, separator_style))
        story.append(Spacer(1, 0.15 * inch))
        
        return story
    
    def _parse_html_to_reportlab(self, html: str) -> str:
        """
        Convert QTextEdit HTML to ReportLab-compatible markup.
        
        Args:
            html: HTML string from QTextEdit
            
        Returns:
            ReportLab-compatible text with formatting tags
        """
        # Remove Qt-specific HTML wrapper
        html = re.sub(r'<!DOCTYPE.*?>', '', html, flags=re.DOTALL)
        html = re.sub(r'<html>.*?<body[^>]*>', '', html, flags=re.DOTALL)
        html = re.sub(r'</body>.*?</html>', '', html, flags=re.DOTALL)
        
        # Convert Qt font-weight to bold
        html = re.sub(r'<span style="[^"]*font-weight:600[^"]*">(.*?)</span>', r'<b>\1</b>', html, flags=re.DOTALL)
        html = re.sub(r'<span style="[^"]*font-weight:700[^"]*">(.*?)</span>', r'<b>\1</b>', html, flags=re.DOTALL)
        
        # Convert Qt font-style to italic
        html = re.sub(r'<span style="[^"]*font-style:italic[^"]*">(.*?)</span>', r'<i>\1</i>', html, flags=re.DOTALL)
        
        # Convert Qt text-decoration to underline
        html = re.sub(r'<span style="[^"]*text-decoration: underline[^"]*">(.*?)</span>', r'<u>\1</u>', html, flags=re.DOTALL)
        
        # Extract font colors - handle both hex and rgb formats
        def replace_color(match):
            color = match.group(1)
            content = match.group(2)
            logger.debug(f"PDF Color extraction: {color} for content: {content[:50]}...")
            return f'<font color="{color}">{content}</font>'
        
        # Match hex colors like #FF0000 or #ff0000
        html = re.sub(r'<span style="[^"]*color:\s*(#[0-9a-fA-F]{6})[^"]*">(.*?)</span>', replace_color, html, flags=re.DOTALL)
        
        # Match RGB colors like rgb(255, 0, 0) - convert to hex
        def replace_rgb_color(match):
            r = int(match.group(1))
            g = int(match.group(2))
            b = int(match.group(3))
            content = match.group(4)
            hex_color = f'#{r:02x}{g:02x}{b:02x}'
            logger.debug(f"PDF RGB to hex: rgb({r},{g},{b}) -> {hex_color}")
            return f'<font color="{hex_color}">{content}</font>'
        
        html = re.sub(r'<span style="[^"]*color:\s*rgb\((\d+),\s*(\d+),\s*(\d+)\)[^"]*">(.*?)</span>', replace_rgb_color, html, flags=re.DOTALL)
        
        # Clean up paragraph tags
        html = re.sub(r'<p[^>]*>', '', html)
        html = re.sub(r'</p>', '<br/>', html)
        
        # Remove remaining span tags
        html = re.sub(r'<span[^>]*>', '', html)
        html = re.sub(r'</span>', '', html)
        
        # Clean up extra whitespace
        html = re.sub(r'\s+', ' ', html)
        html = html.strip()
        
        logger.debug(f"PDF HTML parsed, length: {len(html)}")
        return html
    
    def create_pdf(
        self,
        text: str,
        filename: Optional[str] = None,
        pdf_format: str = "simple_text",
        title: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Tuple[Path, bool]:
        """
        Create a PDF document from text content.
        
        Args:
            text: Text content to convert to PDF
            filename: Output filename (without .pdf extension, auto-generated if None)
            pdf_format: Formatting style (simple_text, with_bullets, formatted_paragraphs)
            title: Optional document title (displayed at top)
            metadata: Optional dict with user info (name, id, course, etc.) for header
            
        Returns:
            Tuple of (pdf_path, success)
            
        Raises:
            ValueError: If text is empty or format is invalid
        """
        # Validate input
        if not text or not text.strip():
            raise ValueError("Text content cannot be empty")
        
        # Parse format
        try:
            format_enum = PDFFormat(pdf_format.lower())
        except ValueError:
            raise ValueError(
                f"Invalid PDF format: {pdf_format}. "
                f"Must be one of: {', '.join([f.value for f in PDFFormat])}"
            )
        
        # Generate filename if not provided
        if filename is None:
            filename = self._generate_filename()
        
        # Ensure .pdf extension
        if not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        # Full output path
        pdf_path = self.output_dir / filename
        
        logger.info(f"📄 Creating PDF: {pdf_path.name} (Format: {format_enum.value})")
        
        try:
            # Create PDF based on format
            if format_enum == PDFFormat.SIMPLE_TEXT:
                self._create_simple_text_pdf(text, pdf_path, title, metadata)
            elif format_enum == PDFFormat.WITH_BULLETS:
                self._create_bullets_pdf(text, pdf_path, title, metadata)
            elif format_enum == PDFFormat.FORMATTED_PARAGRAPHS:
                self._create_formatted_pdf(text, pdf_path, title, metadata)
            
            logger.info(f"✅ PDF created successfully: {pdf_path}")
            return pdf_path, True
            
        except Exception as e:
            logger.error(f"❌ PDF creation failed: {e}")
            raise RuntimeError(f"Failed to create PDF: {str(e)}")
    
    # --- PDF Creation Methods ---
    
    def _create_simple_text_pdf(self, text: str, output_path: Path, title: Optional[str], metadata: Optional[dict] = None):
        """Create simple text PDF with basic formatting."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Build content
        story = []
        
        # Add credentials header if metadata provided
        if metadata:
            story.extend(self._create_credentials_header(styles, metadata, title))
        elif title:
            # Fallback: just add title if no metadata
            story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 0.3 * inch))
        
        # Check if text is HTML (from QTextEdit)
        is_html = text.strip().startswith('<!DOCTYPE') or text.strip().startswith('<html')
        
        if is_html:
            # Parse HTML and preserve formatting
            parsed_text = self._parse_html_to_reportlab(text)
            # Split by line breaks
            paragraphs = parsed_text.split('<br/>')
        else:
            # Plain text - split by paragraphs
            paragraphs = text.split('\n\n')
        
        # Add text content
        for para in paragraphs:
            if para.strip():
                # Clean paragraph
                para_clean = para.strip()
                if not is_html:
                    para_clean = para_clean.replace('\n', ' ')
                story.append(Paragraph(para_clean, styles['Normal']))
                story.append(Spacer(1, 0.15 * inch))
        
        # Build PDF
        doc.build(story)
    
    def _create_bullets_pdf(self, text: str, output_path: Path, title: Optional[str], metadata: Optional[dict] = None):
        """Create PDF with proper bullet point formatting and sections."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom bullet style with proper indentation
        bullet_style = ParagraphStyle(
            'Bullet',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,
            leftIndent=30,  # Indent the bullet text
            bulletIndent=10,  # Position of bullet symbol
            spaceAfter=8,
            bulletFontName='Helvetica',
            bulletFontSize=11
        )
        
        # Create heading style for sections
        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#9333EA'),
            spaceAfter=10,
            spaceBefore=16,
            fontName='Helvetica-Bold'
        )
        
        # Build content
        story = []
        
        # Add credentials header if metadata provided
        if metadata:
            story.extend(self._create_credentials_header(styles, metadata, title))
        elif title:
            # Fallback: just add title if no metadata
            story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 0.3 * inch))
        
        # Check if text is HTML (from QTextEdit) and parse if needed
        is_html = text.strip().startswith('<!DOCTYPE') or text.strip().startswith('<html')
        if is_html:
            text = self._parse_html_to_reportlab(text)
        
        # Process text into sections and bullet points
        # Split by double newlines for sections
        sections = text.split('\n\n') if not is_html else text.split('<br/><br/>')
        
        for section_idx, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue
            
            lines = section.split('\n')
            
            # Check if first line looks like a heading
            first_line = lines[0].strip()
            is_heading = (
                len(first_line) < 80 and 
                len(lines) > 1 and
                (first_line.endswith(':') or first_line.isupper() or len(first_line.split()) <= 5)
            )
            
            if is_heading:
                # Add heading
                heading_text = first_line.rstrip(':')
                story.append(Paragraph(f"<b>{heading_text}</b>", heading_style))
                lines = lines[1:]  # Process remaining lines as bullets
            
            # Process bullets
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 0.05 * inch))
                    continue
                
                # Remove existing bullet markers (*, -, •, ·, →)
                line_clean = line.lstrip('•-*·→ ')
                
                # Use bulletText parameter for proper bullet rendering
                bullet_para = Paragraph(
                    line_clean,
                    bullet_style,
                    bulletText='•'
                )
                story.append(bullet_para)
            
            # Add space between sections
            if section_idx < len(sections) - 1:
                story.append(Spacer(1, 0.15 * inch))
        
        # Build PDF
        doc.build(story)
    
    def _create_formatted_pdf(self, text: str, output_path: Path, title: Optional[str], metadata: Optional[dict] = None):
        """Create PDF with formatted paragraphs and better typography."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Create custom paragraph style with justified text
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=11,
            leading=16,  # Line spacing
            alignment=TA_JUSTIFY,
            spaceAfter=12
        )
        
        # Create heading style
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#9333EA'),  # Purple theme
            spaceAfter=10,
            spaceBefore=16
        )
        
        # Build content
        story = []
        
        # Add credentials header if metadata provided
        if metadata:
            story.extend(self._create_credentials_header(styles, metadata, title))
        elif title:
            # Fallback: just add title if no metadata
            story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 0.3 * inch))
        
        # Check if text is HTML (from QTextEdit) and parse if needed
        is_html = text.strip().startswith('<!DOCTYPE') or text.strip().startswith('<html')
        if is_html:
            text = self._parse_html_to_reportlab(text)
        
        # Process text intelligently
        sections = text.split('\n\n') if not is_html else text.split('<br/><br/>')
        
        for section in sections:
            section = section.strip()
            if not section:
                continue
            
            # Check if this looks like a heading (short, possibly all caps or ends with :)
            lines = section.split('\n')
            first_line = lines[0].strip()
            
            is_heading = (
                len(first_line) < 60 and
                len(lines) == 1 and
                (first_line.isupper() or first_line.endswith(':'))
            )
            
            if is_heading:
                # Add as heading
                heading_text = first_line.rstrip(':')
                story.append(Paragraph(f"<b>{heading_text}</b>", heading_style))
            else:
                # Check if section contains bullet points
                has_bullets = any(line.strip().startswith(('•', '-', '*', '·', '→')) for line in lines)
                
                if has_bullets:
                    # Process as bulleted list
                    bullet_style = ParagraphStyle(
                        'FormattedBullet',
                        parent=body_style,
                        leftIndent=20,
                        bulletIndent=10
                    )
                    
                    for line in lines:
                        line = line.strip()
                        if line:
                            # Clean bullet
                            line_clean = line.lstrip('•-*·→ ')
                            story.append(Paragraph(f"• {line_clean}", bullet_style))
                else:
                    # Regular paragraph - clean and format
                    para_text = ' '.join(line.strip() for line in lines if line.strip())
                    story.append(Paragraph(para_text, body_style))
        
        # Build PDF
        doc.build(story)
    
    # --- Helper Methods ---
    
    def _generate_filename(self) -> str:
        """
        Generate automatic filename with timestamp.
        
        Returns:
            Filename string
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"Nexa_Document_{timestamp}.pdf"
    
    def get_available_formats(self) -> list:
        """
        Get list of available PDF formats.
        
        Returns:
            List of format names
        """
        return [fmt.value for fmt in PDFFormat]
    
    def get_format_description(self, pdf_format: str) -> str:
        """
        Get description of a PDF format.
        
        Args:
            pdf_format: Format name
            
        Returns:
            Human-readable description
        """
        descriptions = {
            "simple_text": "Plain text with basic paragraph formatting",
            "with_bullets": "Convert lines into bulleted list",
            "formatted_paragraphs": "Advanced formatting with headings and justified text"
        }
        return descriptions.get(pdf_format.lower(), "Unknown format")
    
    def get_output_directory(self) -> Path:
        """
        Get the output directory path.
        
        Returns:
            Path to output directory
        """
        return self.output_dir
