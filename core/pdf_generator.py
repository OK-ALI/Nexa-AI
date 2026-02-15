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
    
    # --- HTML Processing Methods ---
    
    def _clean_inline_html(self, html: str) -> str:
        """
        Clean inline HTML tags to ReportLab-compatible markup.
        Handles both web editor output and QTextEdit HTML.
        
        Supported ReportLab tags: <b>, <i>, <u>, <font face/color/size>, <br/>
        """
        # --- Font tag normalization ---
        # Convert <font style="font-size: Xpt;"> to <font size="X">
        # Also preserve face and color attributes on the same tag
        def normalize_font_tag(match):
            attrs_str = match.group(1)
            parts = []
            
            # Extract font-size from style attribute
            size_m = re.search(r'font-size:\s*(\d+(?:\.\d+)?)pt', attrs_str)
            if size_m:
                parts.append(f'size="{int(float(size_m.group(1)))}"')
            
            # Extract face attribute
            face_m = re.search(r'face="([^"]*)"', attrs_str)
            if face_m:
                parts.append(f'face="{face_m.group(1)}"')
            
            # Extract color attribute
            color_m = re.search(r'color="([^"]*)"', attrs_str)
            if color_m:
                parts.append(f'color="{color_m.group(1)}"')
            
            if parts:
                return f'<font {" ".join(parts)}>'
            return ''
        
        html = re.sub(r'<font\b([^>]*)>', normalize_font_tag, html)
        
        # --- Qt/Span-based formatting conversion ---
        # Bold: font-weight:600/700/bold
        html = re.sub(
            r'<span[^>]*font-weight:\s*(?:600|700|bold)[^>]*>(.*?)</span>',
            r'<b>\1</b>', html, flags=re.DOTALL
        )
        # Italic: font-style:italic
        html = re.sub(
            r'<span[^>]*font-style:\s*italic[^>]*>(.*?)</span>',
            r'<i>\1</i>', html, flags=re.DOTALL
        )
        # Underline: text-decoration: underline
        html = re.sub(
            r'<span[^>]*text-decoration:\s*underline[^>]*>(.*?)</span>',
            r'<u>\1</u>', html, flags=re.DOTALL
        )
        
        # --- Color conversion ---
        # Span with hex color -> <font color="">
        def span_color_to_font(match):
            style = match.group(1)
            content = match.group(2)
            hex_m = re.search(r'color:\s*(#[0-9a-fA-F]{3,6})', style)
            rgb_m = re.search(r'color:\s*rgb\((\d+),\s*(\d+),\s*(\d+)\)', style)
            if hex_m:
                return f'<font color="{hex_m.group(1)}">{content}</font>'
            elif rgb_m:
                r, g, b = int(rgb_m.group(1)), int(rgb_m.group(2)), int(rgb_m.group(3))
                return f'<font color="#{r:02x}{g:02x}{b:02x}">{content}</font>'
            return content
        
        html = re.sub(r'<span\s+style="([^"]*)">(.*?)</span>', span_color_to_font, html, flags=re.DOTALL)
        
        # --- Cleanup ---
        html = re.sub(r'</?span[^>]*>', '', html)           # Strip remaining spans
        html = re.sub(r'</?(?:div|p)[^>]*>', '', html)      # Strip block tags (handled elsewhere)
        html = re.sub(r'<font\s*>(.*?)</font>', r'\1', html, flags=re.DOTALL)  # Remove empty font tags
        html = re.sub(r'<br\s*/?>', '<br/>', html)          # Normalize <br> variants
        html = re.sub(r'[ \t]+', ' ', html)                 # Normalize spaces (keep <br/>)
        
        return html.strip()
    
    def _parse_html_to_reportlab(self, html: str) -> str:
        """
        Convert HTML to ReportLab-compatible flat markup string.
        Handles both web editor innerHTML and QTextEdit HTML.
        
        For richer conversion (alignment, lists), use _convert_html_to_flowables() instead.
        """
        # Remove document wrappers
        html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.DOTALL)
        html = re.sub(r'<html[^>]*>.*?<body[^>]*>', '', html, flags=re.DOTALL)
        html = re.sub(r'</body>\s*</html>', '', html, flags=re.DOTALL)
        
        # Convert list items to bullet text before stripping list tags
        html = re.sub(r'<li[^>]*>(.*?)</li>', '• \\1<br/>', html, flags=re.DOTALL)
        html = re.sub(r'</?(?:ul|ol)[^>]*>', '', html)
        
        # Convert paragraph/div endings to line breaks
        html = re.sub(r'</(?:div|p)>', '<br/>', html)
        html = re.sub(r'<(?:div|p)[^>]*>', '', html)
        
        # Clean inline formatting to ReportLab-compatible tags
        html = self._clean_inline_html(html)
        
        # Collapse excessive <br/> sequences
        html = re.sub(r'(?:<br/>\s*){3,}', '<br/><br/>', html)
        
        # Final whitespace cleanup
        html = re.sub(r'\s+', ' ', html).strip()
        
        logger.debug(f"PDF HTML parsed (flat), length: {len(html)}")
        return html
    
    def _detect_html_content(self, text: str) -> bool:
        """Detect whether text contains HTML markup (web editor or QTextEdit)."""
        if not text:
            return False
        t = text.strip()
        # QTextEdit full-document wrappers
        if t.startswith('<!DOCTYPE') or t.startswith('<html'):
            return True
        # Web editor block/inline tags
        if re.search(r'<(?:div|p|ul|ol|li|br|font|b|i|u|h[1-6]|span)\b', t, re.IGNORECASE):
            return True
        return False
    
    def _convert_html_to_flowables(self, html: str, base_style, styles) -> list:
        """
        Convert web editor HTML into structured ReportLab flowables.
        Preserves alignment, lists, font sizes, colors, and inline formatting.
        
        Args:
            html: Raw innerHTML from web editor or QTextEdit HTML
            base_style: Default ParagraphStyle for body text
            styles: ReportLab stylesheet
            
        Returns:
            List of ReportLab flowables
        """
        align_map = {
            'left': TA_LEFT,
            'center': TA_CENTER,
            'right': TA_RIGHT,
            'justify': TA_JUSTIFY,
        }
        
        story = []
        _style_counter = [0]  # Mutable counter for unique style names
        
        def make_style(parent, **kwargs):
            """Create a uniquely-named ParagraphStyle."""
            _style_counter[0] += 1
            return ParagraphStyle(f'Auto_{_style_counter[0]}', parent=parent, **kwargs)
        
        # Clean document wrappers
        html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.DOTALL)
        html = re.sub(r'<html[^>]*>.*?<body[^>]*>', '', html, flags=re.DOTALL)
        html = re.sub(r'</body>\s*</html>', '', html, flags=re.DOTALL)
        html = re.sub(r'<br\s*/?>', '<br/>', html)
        html = html.strip()
        
        if not html:
            return story
        
        # Split into block-level segments: lists vs everything else
        segments = re.split(r'(<(?:ul|ol)\b[^>]*>.*?</(?:ul|ol)>)', html, flags=re.DOTALL)
        
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            
            # --- Unordered list ---
            ul_match = re.match(r'<ul\b[^>]*>(.*?)</ul>', segment, re.DOTALL)
            if ul_match:
                items = re.findall(r'<li[^>]*>(.*?)</li>', ul_match.group(1), re.DOTALL)
                for item_html in items:
                    clean = self._clean_inline_html(item_html)
                    if clean.strip():
                        bstyle = make_style(base_style, leftIndent=30, bulletIndent=12, spaceAfter=4)
                        story.append(Paragraph(clean, bstyle, bulletText='\u2022'))
                story.append(Spacer(1, 0.1 * inch))
                continue
            
            # --- Ordered list ---
            ol_match = re.match(r'<ol\b[^>]*>(.*?)</ol>', segment, re.DOTALL)
            if ol_match:
                items = re.findall(r'<li[^>]*>(.*?)</li>', ol_match.group(1), re.DOTALL)
                for idx, item_html in enumerate(items, 1):
                    clean = self._clean_inline_html(item_html)
                    if clean.strip():
                        nstyle = make_style(base_style, leftIndent=30, bulletIndent=12, spaceAfter=4)
                        story.append(Paragraph(clean, nstyle, bulletText=f'{idx}.'))
                story.append(Spacer(1, 0.1 * inch))
                continue
            
            # --- Regular content: split by <div> / <p> blocks ---
            blocks = re.split(r'(?:</div>|</p>)', segment)
            
            for block in blocks:
                block = block.strip()
                if not block:
                    continue
                
                # Extract alignment from opening div/p style
                align = base_style.alignment
                align_m = re.search(r'text-align:\s*(left|center|right|justify)', block)
                if align_m:
                    align = align_map.get(align_m.group(1), base_style.alignment)
                
                # Remove opening div/p tag
                block = re.sub(r'<(?:div|p)\b[^>]*>', '', block)
                
                # Split by <br/> for line breaks within the block
                lines = block.split('<br/>')
                
                for line in lines:
                    clean = self._clean_inline_html(line)
                    if not clean.strip():
                        continue
                    
                    if align != base_style.alignment:
                        pstyle = make_style(base_style, alignment=align)
                    else:
                        pstyle = base_style
                    
                    story.append(Paragraph(clean, pstyle))
                
                # Small gap between blocks
                if story and not isinstance(story[-1], Spacer):
                    story.append(Spacer(1, 0.06 * inch))
        
        # Remove trailing spacer
        if story and isinstance(story[-1], Spacer):
            story.pop()
        
        return story
    
    def _add_page_number(self, canvas_obj, doc):
        """Draw page number footer on each page."""
        canvas_obj.saveState()
        
        page_num = canvas_obj.getPageNumber()
        page_w = self.page_size[0]
        
        # Page number at bottom center
        canvas_obj.setFont('Helvetica', 9)
        canvas_obj.setFillColor(colors.HexColor('#999999'))
        canvas_obj.drawCentredString(page_w / 2.0, 0.4 * inch, f"Page {page_num}")
        
        # Subtle branding at bottom-right
        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(colors.HexColor('#CCCCCC'))
        canvas_obj.drawRightString(page_w - self.margin, 0.4 * inch, "Generated by Nexa AI")
        
        canvas_obj.restoreState()
    
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
        """Create simple text PDF with basic formatting and page numbers."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        if metadata:
            story.extend(self._create_credentials_header(styles, metadata, title))
        elif title:
            story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 0.3 * inch))
        
        # Detect HTML content (web editor or QTextEdit)
        is_html = self._detect_html_content(text)
        
        if is_html:
            parsed_text = self._parse_html_to_reportlab(text)
            paragraphs = [p for p in parsed_text.split('<br/>') if p.strip()]
        else:
            paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue
            if not is_html:
                para_clean = para_clean.replace('\n', ' ')
            story.append(Paragraph(para_clean, styles['Normal']))
            story.append(Spacer(1, 0.15 * inch))
        
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
    
    def _create_bullets_pdf(self, text: str, output_path: Path, title: Optional[str], metadata: Optional[dict] = None):
        """Create PDF with bullet points, section headings, and page numbers."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        styles = getSampleStyleSheet()
        
        bullet_style = ParagraphStyle(
            'Bullet', parent=styles['Normal'],
            fontSize=11, leading=16,
            leftIndent=30, bulletIndent=10,
            spaceAfter=8,
            bulletFontName='Helvetica', bulletFontSize=11
        )
        heading_style = ParagraphStyle(
            'SectionHeading', parent=styles['Heading2'],
            fontSize=13, textColor=colors.HexColor('#9333EA'),
            spaceAfter=10, spaceBefore=16, fontName='Helvetica-Bold'
        )
        
        story = []
        
        if metadata:
            story.extend(self._create_credentials_header(styles, metadata, title))
        elif title:
            story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 0.3 * inch))
        
        # Detect and parse HTML content
        is_html = self._detect_html_content(text)
        if is_html:
            text = self._parse_html_to_reportlab(text)
        
        # Split into sections
        sections = text.split('\n\n') if not is_html else text.split('<br/><br/>')
        
        for section_idx, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue
            
            # Split lines appropriately for HTML vs plain text
            lines = section.split('<br/>') if is_html else section.split('\n')
            
            first_line = lines[0].strip()
            is_heading = (
                len(first_line) < 80 and len(lines) > 1 and
                (first_line.endswith(':') or first_line.isupper() or len(first_line.split()) <= 5)
            )
            
            if is_heading:
                heading_text = first_line.rstrip(':')
                story.append(Paragraph(f"<b>{heading_text}</b>", heading_style))
                lines = lines[1:]
            
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 0.05 * inch))
                    continue
                line_clean = line.lstrip('\u2022-*\u00b7\u2192 ')
                story.append(Paragraph(line_clean, bullet_style, bulletText='\u2022'))
            
            if section_idx < len(sections) - 1:
                story.append(Spacer(1, 0.15 * inch))
        
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
    
    def _create_formatted_pdf(self, text: str, output_path: Path, title: Optional[str], metadata: Optional[dict] = None):
        """Create PDF with rich formatting, alignment, lists, and page numbers."""
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=self.page_size,
            leftMargin=self.margin,
            rightMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        styles = getSampleStyleSheet()
        
        body_style = ParagraphStyle(
            'CustomBody', parent=styles['Normal'],
            fontSize=11, leading=16,
            alignment=TA_LEFT, spaceAfter=8
        )
        heading_style = ParagraphStyle(
            'CustomHeading', parent=styles['Heading2'],
            fontSize=14, textColor=colors.HexColor('#9333EA'),
            spaceAfter=10, spaceBefore=16
        )
        
        story = []
        
        if metadata:
            story.extend(self._create_credentials_header(styles, metadata, title))
        elif title:
            story.append(Paragraph(title, styles['Title']))
            story.append(Spacer(1, 0.3 * inch))
        
        # Detect content type
        is_html = self._detect_html_content(text)
        
        if is_html:
            # Use rich HTML-to-flowables converter for full formatting fidelity
            flowables = self._convert_html_to_flowables(text, body_style, styles)
            story.extend(flowables)
        else:
            # Plain text fallback with heading/bullet detection
            sections = text.split('\n\n')
            
            for section in sections:
                section = section.strip()
                if not section:
                    continue
                
                lines = section.split('\n')
                first_line = lines[0].strip()
                
                is_heading = (
                    len(first_line) < 60 and len(lines) == 1 and
                    (first_line.isupper() or first_line.endswith(':'))
                )
                
                if is_heading:
                    heading_text = first_line.rstrip(':')
                    story.append(Paragraph(f"<b>{heading_text}</b>", heading_style))
                else:
                    has_bullets = any(
                        line.strip().startswith(('\u2022', '-', '*', '\u00b7', '\u2192'))
                        for line in lines
                    )
                    
                    if has_bullets:
                        bullet_style = ParagraphStyle(
                            'FormattedBullet', parent=body_style,
                            leftIndent=30, bulletIndent=12, spaceAfter=4
                        )
                        for line in lines:
                            line = line.strip()
                            if line:
                                line_clean = line.lstrip('\u2022-*\u00b7\u2192 ')
                                story.append(Paragraph(line_clean, bullet_style, bulletText='\u2022'))
                    else:
                        para_text = ' '.join(l.strip() for l in lines if l.strip())
                        story.append(Paragraph(para_text, body_style))
        
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
    
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
