"""
Text Refiner - AI-powered text refinement and improvement
Uses LLMManager (Llama/Gemini) for various text transformation modes.
"""

import logging
from typing import Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RefinementMode(Enum):
    """Text refinement modes."""
    # Original modes
    FORMAL = "formal"
    SHORTER = "shorter"
    GRAMMAR_ONLY = "grammar_only"
    IMPROVE = "improve"
    SUMMARIZE = "summarize"
    CASUAL = "casual"
    
    # Study Tools
    EXTRACT_TERMS = "extract_terms"
    FLASHCARDS = "flashcards"
    STUDY_QUESTIONS = "study_questions"
    DIFFICULTY_CHECK = "difficulty_check"
    
    # Writing Enhancement
    PARAPHRASE = "paraphrase"
    EXPAND = "expand"
    SIMPLIFY = "simplify"
    ACADEMIC = "academic"
    
    # Organization
    OUTLINE = "outline"
    ADD_HEADINGS = "add_headings"


class TextRefiner:
    """
    Handles text refinement using AI models.
    Provides various modes for improving, transforming, and refining text content.
    """
    
    def __init__(self, llm_manager):
        """
        Initialize Text Refiner.
        
        Args:
            llm_manager: LLMManager instance for AI processing
        """
        self.llm_manager = llm_manager
        
        # Refinement prompts for each mode
        self.mode_prompts = {
            # Original modes
            RefinementMode.FORMAL: self._get_formal_prompt,
            RefinementMode.SHORTER: self._get_shorter_prompt,
            RefinementMode.GRAMMAR_ONLY: self._get_grammar_prompt,
            RefinementMode.IMPROVE: self._get_improve_prompt,
            RefinementMode.SUMMARIZE: self._get_summarize_prompt,
            RefinementMode.CASUAL: self._get_casual_prompt,
            
            # Study Tools
            RefinementMode.EXTRACT_TERMS: self._get_extract_terms_prompt,
            RefinementMode.FLASHCARDS: self._get_flashcards_prompt,
            RefinementMode.STUDY_QUESTIONS: self._get_study_questions_prompt,
            RefinementMode.DIFFICULTY_CHECK: self._get_difficulty_check_prompt,
            
            # Writing Enhancement
            RefinementMode.PARAPHRASE: self._get_paraphrase_prompt,
            RefinementMode.EXPAND: self._get_expand_prompt,
            RefinementMode.SIMPLIFY: self._get_simplify_prompt,
            RefinementMode.ACADEMIC: self._get_academic_prompt,
            
            # Organization
            RefinementMode.OUTLINE: self._get_outline_prompt,
            RefinementMode.ADD_HEADINGS: self._get_add_headings_prompt,
        }
        
        logger.info("✨ TextRefiner initialized with 16 refinement modes (6 original + 10 student features)")
    
    def refine_text(self, text: str, mode: str) -> Tuple[str, str]:
        """
        Refine text using specified mode.
        
        Args:
            text: Text content to refine
            mode: Refinement mode (formal, shorter, grammar_only, improve, summarize, casual)
            
        Returns:
            Tuple of (refined_text, mode_used_by_llm)
            
        Raises:
            ValueError: If mode is invalid or text is empty
        """
        # Validate input
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Parse mode
        try:
            refinement_mode = RefinementMode(mode.lower())
        except ValueError:
            raise ValueError(f"Invalid refinement mode: {mode}. Must be one of: {', '.join([m.value for m in RefinementMode])}")
        
        logger.info(f"🔄 Refining text with mode: {refinement_mode.value} ({len(text)} chars)")
        
        # Get prompt for mode
        prompt_func = self.mode_prompts.get(refinement_mode)
        if not prompt_func:
            raise ValueError(f"No prompt defined for mode: {refinement_mode.value}")
        
        prompt = prompt_func(text)
        
        # Generate refined text using LLM
        try:
            refined_text, llm_mode = self.llm_manager.generate_response(
                prompt,
                skip_cache=True,  # Don't cache refinements - each is unique
                use_raw_prompt=True  # Use prompt as-is without JSON wrapper
            )
            
            # Clean up the response
            refined_text = self._clean_response(refined_text)
            
            logger.info(f"✅ Text refined successfully using {llm_mode.value} model ({len(refined_text)} chars)")
            return refined_text, llm_mode.value
            
        except Exception as e:
            logger.error(f"❌ Text refinement failed: {e}")
            raise RuntimeError(f"Failed to refine text: {str(e)}")
    
    # --- Prompt Generators for Each Mode ---
    
    def _get_formal_prompt(self, text: str) -> str:
        """Generate prompt for formal tone conversion."""
        return f"""You are a professional writing assistant. Transform the following text into a formal, professional tone while preserving all key information and meaning.

Requirements:
- Use formal language and professional vocabulary
- Remove casual expressions, slang, and contractions
- Maintain proper grammar and sentence structure
- Keep the same length approximately (don't make it significantly longer)
- Preserve all important facts and details
- Output ONLY the refined text, no explanations or comments

Original Text:
{text}

Formal Version:"""
    
    def _get_shorter_prompt(self, text: str) -> str:
        """Generate prompt for making text more concise."""
        return f"""You are a concise writing assistant. Make the following text shorter and more concise while retaining all essential information.

Requirements:
- Remove redundant words and phrases
- Use active voice where possible
- Keep sentences short and clear
- Preserve all key facts and important points
- Aim to reduce length by at least 30-40%
- Output ONLY the shortened text, no explanations or comments

Original Text:
{text}

Shorter Version:"""
    
    def _get_grammar_prompt(self, text: str) -> str:
        """Generate prompt for grammar and spelling fixes only."""
        return f"""You are a grammar and spelling checker. Fix any grammatical errors, spelling mistakes, and punctuation issues in the following text. Do NOT change the tone, style, or meaning - only fix technical errors.

Requirements:
- Correct spelling mistakes
- Fix grammatical errors (subject-verb agreement, tense consistency, etc.)
- Correct punctuation (commas, periods, apostrophes, etc.)
- Fix capitalization issues
- Do NOT rephrase sentences or change word choices unless grammatically necessary
- Do NOT change the writing style or tone
- Output ONLY the corrected text, no explanations, notes, or comments
- Do NOT add "Note:", "I corrected", or any other meta-commentary
- Return the text exactly as it should appear in the final document

Original Text:
{text}

Corrected Version:"""
    
    def _get_improve_prompt(self, text: str) -> str:
        """Generate prompt for overall text improvement."""
        return f"""You are an expert writing assistant. Improve the following text to make it clearer, more engaging, and better structured while preserving the original meaning and intent.

Requirements:
- Enhance clarity and readability
- Improve sentence flow and transitions
- Use more precise and impactful vocabulary
- Fix any grammar or spelling errors
- Maintain the original tone and style (don't make it too formal or casual)
- Keep approximately the same length
- Output ONLY the improved text, no explanations or comments

Original Text:
{text}

Improved Version:"""
    
    def _get_summarize_prompt(self, text: str) -> str:
        """Generate prompt for text summarization."""
        return f"""You are a summarization assistant. Create a clear, concise summary of the following text that captures all key points and main ideas.

Requirements:
- Extract and present the main ideas and key points
- Organize information logically
- Use clear, concise language
- Aim for 30-50% of the original length (or less for very long texts)
- Preserve all critical information and conclusions
- Use bullet points or short paragraphs for clarity
- Output ONLY the summary, no introductory phrases like "Here is a summary:" or explanations

Original Text:
{text}

Summary:"""
    
    def _get_casual_prompt(self, text: str) -> str:
        """Generate prompt for casual tone conversion."""
        return f"""You are a friendly writing assistant. Transform the following text into a casual, conversational tone while keeping all important information.

Requirements:
- Use casual, friendly language
- Include contractions (I'm, don't, can't, etc.)
- Write as if speaking to a friend
- Keep sentences natural and conversational
- Maintain all key facts and details
- Keep approximately the same length
- Output ONLY the casual version, no explanations or comments

Original Text:
{text}

Casual Version:"""
    
    # --- STUDY TOOLS ---
    
    def _get_extract_terms_prompt(self, text: str) -> str:
        """Generate prompt for extracting key terms."""
        return f"""You are an educational assistant. Extract and list the most important key terms, concepts, and vocabulary from the following text.

Requirements:
- Identify 10-15 most important terms/concepts
- List each term with a brief definition (1-2 sentences)
- Organize by importance (most important first)
- Include technical terms, key concepts, and critical vocabulary
- Format as: "Term: Definition"
- Output ONLY the list, no introductory text

Original Text:
{text}

Key Terms:"""
    
    def _get_flashcards_prompt(self, text: str) -> str:
        """Generate prompt for creating flashcards."""
        return f"""You are a study assistant. Create 8-12 flashcards from the following text to help students learn and memorize the content.

Requirements:
- Create clear question and answer pairs
- Cover main concepts, definitions, and important facts
- Questions should test understanding, not just memorization
- Keep answers concise (1-3 sentences)
- Format each as: "Q: [question]\\nA: [answer]\\n"
- Include mix of: definitions, applications, examples, relationships
- Output ONLY the flashcards, no introductory text

Original Text:
{text}

Flashcards:"""
    
    def _get_study_questions_prompt(self, text: str) -> str:
        """Generate prompt for creating study questions."""
        return f"""You are an educator. Create 6-10 study questions from the following text to help students review and test their understanding.

Requirements:
- Mix of difficulty levels (easy, medium, hard)
- Include different question types: recall, comprehension, application, analysis
- Questions should promote critical thinking
- Number each question (1., 2., 3., etc.)
- Focus on main concepts and key takeaways
- Output ONLY the questions, no answers or introductory text

Original Text:
{text}

Study Questions:"""
    
    def _get_difficulty_check_prompt(self, text: str) -> str:
        """Generate prompt for checking difficulty level."""
        return f"""You are a readability analyst. Analyze the following text and provide a difficulty assessment.

Requirements:
- Estimate reading grade level (e.g., "Grade 8-10", "College level")
- Identify complexity factors: vocabulary, sentence structure, concepts
- Note any jargon or technical terms that may be challenging
- Suggest the appropriate audience (high school, college, general public, etc.)
- Keep assessment concise (4-6 sentences)
- Output ONLY the assessment, no extra commentary

Text to Analyze:
{text}

Difficulty Assessment:"""
    
    # --- WRITING ENHANCEMENT ---
    
    def _get_paraphrase_prompt(self, text: str) -> str:
        """Generate prompt for paraphrasing."""
        return f"""You are a writing assistant. Paraphrase the following text using completely different words and sentence structures while preserving all original meaning and information.

Requirements:
- Use synonyms and alternative phrasings
- Restructure sentences (change active/passive, reorder clauses)
- Maintain the same level of detail and formality
- Keep approximately the same length
- Preserve all facts, dates, names, and key information
- Output ONLY the paraphrased text, no explanations

Original Text:
{text}

Paraphrased Version:"""
    
    def _get_expand_prompt(self, text: str) -> str:
        """Generate prompt for expanding text."""
        return f"""You are a writing assistant. Expand the following text by adding more detail, explanation, and context while staying on topic.

Requirements:
- Add supporting details and examples
- Elaborate on key points with more explanation
- Include relevant context and background
- Maintain the original tone and style
- Aim for 50-100% longer than original
- Stay focused on the original topic
- Output ONLY the expanded text, no meta-commentary

Original Text:
{text}

Expanded Version:"""
    
    def _get_simplify_prompt(self, text: str) -> str:
        """Generate prompt for simplifying text."""
        return f"""You are an educational writer. Simplify the following text to make it easier to understand for a general audience.

Requirements:
- Replace complex words with simpler alternatives
- Break long sentences into shorter ones
- Explain technical terms in plain language
- Remove unnecessary jargon
- Maintain all key information and facts
- Aim for 6th-8th grade reading level
- Output ONLY the simplified text, no explanations

Original Text:
{text}

Simplified Version:"""
    
    def _get_academic_prompt(self, text: str) -> str:
        """Generate prompt for academic tone conversion."""
        return f"""You are an academic writing assistant. Transform the following text into formal academic style suitable for research papers and scholarly work.

Requirements:
- Use formal, scholarly language and vocabulary
- Employ third-person perspective (avoid "I", "you")
- Use passive voice where appropriate
- Add transitional phrases and academic connectors
- Remove colloquialisms and casual expressions
- Maintain objective, analytical tone
- Keep approximately the same length
- Output ONLY the academic version, no comments

Original Text:
{text}

Academic Version:"""
    
    # --- ORGANIZATION ---
    
    def _get_outline_prompt(self, text: str) -> str:
        """Generate prompt for creating outline."""
        return f"""You are an organizational assistant. Create a hierarchical outline from the following text showing the main ideas and supporting points.

Requirements:
- Use standard outline format (I., A., 1., a., etc.)
- Identify main topics (Roman numerals: I, II, III)
- List subtopics under each main topic (A, B, C)
- Include key supporting points (1, 2, 3)
- Keep entries concise (phrases, not full sentences)
- Maintain logical flow and hierarchy
- Output ONLY the outline, no introductory text

Original Text:
{text}

Outline:"""
    
    def _get_add_headings_prompt(self, text: str) -> str:
        """Generate prompt for adding section headings."""
        return f"""You are an editor. Add appropriate section headings to the following text to improve organization and readability.

Requirements:
- Insert clear, descriptive headings before each major section
- Use consistent heading style (Title Case)
- Headings should summarize the section content
- Create 3-6 headings depending on text length
- Keep headings concise (2-6 words)
- Preserve all original text, only add headings
- Format headings in bold or with markers (##, ###)
- Output the text WITH headings inserted

Original Text:
{text}

Text with Headings:"""
    
    # --- Helper Methods ---
    
    def _clean_response(self, text: str) -> str:
        """
        Clean up AI response by removing common artifacts.
        
        Args:
            text: Raw AI response
            
        Returns:
            Cleaned text
        """
        # Remove common prefixes/suffixes that AI might add
        prefixes_to_remove = [
            "here is the",
            "here's the",
            "formal version:",
            "shorter version:",
            "corrected version:",
            "improved version:",
            "summary:",
            "casual version:",
            "refined text:",
            "refined version:",
        ]
        
        text_lower = text.lower().strip()
        
        for prefix in prefixes_to_remove:
            if text_lower.startswith(prefix):
                # Find where the actual content starts
                start_idx = len(prefix)
                # Skip any following whitespace or colons
                while start_idx < len(text) and text[start_idx] in [' ', ':', '\n', '\r', '\t']:
                    start_idx += 1
                text = text[start_idx:]
                break
        
        # Remove leading/trailing quotes if present
        text = text.strip()
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```") and text.endswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (code block markers)
            if len(lines) > 2:
                text = "\n".join(lines[1:-1]).strip()
        
        # CRITICAL FIX: Remove "Note:" sections that LLM adds despite instructions
        # Look for "Note:" at the end of text and remove everything after it
        import re
        # Match "Note:" or "note:" followed by anything (case insensitive)
        note_pattern = r'\n+Note:\s*.*$'
        text = re.sub(note_pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text.strip()
    
    def get_available_modes(self) -> list:
        """
        Get list of available refinement modes.
        
        Returns:
            List of mode names
        """
        return [mode.value for mode in RefinementMode]
    
    def get_mode_description(self, mode: str) -> str:
        """
        Get description of a refinement mode.
        
        Args:
            mode: Refinement mode name
            
        Returns:
            Human-readable description
        """
        descriptions = {
            # Original modes
            "formal": "Convert text to formal, professional tone",
            "shorter": "Make text more concise (30-40% shorter)",
            "grammar_only": "Fix grammar and spelling errors only",
            "improve": "Enhance clarity, flow, and readability",
            "summarize": "Create a concise summary of key points",
            "casual": "Convert text to casual, conversational tone",
            
            # Study Tools
            "extract_terms": "Extract and define key terms and concepts",
            "flashcards": "Generate question/answer flashcards for studying",
            "study_questions": "Create study questions to test understanding",
            "difficulty_check": "Analyze reading level and complexity",
            
            # Writing Enhancement
            "paraphrase": "Rewrite using different words (avoid plagiarism)",
            "expand": "Add more detail and explanation",
            "simplify": "Make easier to understand (6th-8th grade level)",
            "academic": "Convert to scholarly/research paper style",
            
            # Organization
            "outline": "Create hierarchical outline structure",
            "add_headings": "Add section headings for better organization"
        }
        return descriptions.get(mode.lower(), "Unknown mode")
