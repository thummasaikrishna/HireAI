# talent_resonance/agents/jd_analyzer.py
import re
import json
from typing import Dict, Any, List, Optional
import logging
from .base_agent import BaseAgent
from ..ml.embeddings import TextEmbedder
from ..db.db_manager import DatabaseManager

class JDAnalyzerAgent(BaseAgent):
    """
    Agent responsible for analyzing job descriptions and extracting key requirements.
    """
    
    def __init__(self, agent_id: Optional[str] = None, 
                 db_manager: DatabaseManager = None,
                 embedder: TextEmbedder = None):
        """
        Initialize the JD Analyzer Agent.
        
        Args:
            agent_id: Unique identifier for the agent
            db_manager: Database manager instance
            embedder: Text embedder for generating embeddings
        """
        super().__init__(agent_id, "JD Analyzer")
        self.db_manager = db_manager
        self.embedder = embedder
        self.logger = logging.getLogger("agent.jd_analyzer")
        
    async def process_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming message to analyze a job description.
        
        Args:
            message: The message containing the job description to analyze
            
        Returns:
            A response with the analyzed job data
        """
        message_type = message.get("type", "unknown")
        
        if message_type == "analyze_jd":
            jd_text = message.get("data", {}).get("jd_text", "")
            jd_id = message.get("data", {}).get("jd_id")
            
            if not jd_text:
                return {
                    "type": "error",
                    "error": "No job description text provided"
                }
            
            # Process the job description
            analysis_result = await self._analyze_job_description(jd_text)
            
            # Store the results if we have a JD ID
            if jd_id and self.db_manager:
                await self._store_analysis_result(jd_id, analysis_result)
            
            return {
                "type": "jd_analysis_complete",
                "data": {
                    "jd_id": jd_id,
                    "analysis": analysis_result
                }
            }
        else:
            return {
                "type": "error",
                "error": f"Unknown message type for JD Analyzer: {message_type}"
            }
    
    async def _analyze_job_description(self, jd_text: str) -> Dict[str, Any]:
        """
        Analyze a job description text to extract key components.
        
        Args:
            jd_text: The job description text to analyze
            
        Returns:
            A dictionary containing the analyzed components
        """
        self.logger.info("Analyzing job description")
        
        # This would be implemented with Ollama LLM in production
        # Here's a simplified mock implementation
        try:
            # Extract key sections
            sections = self._extract_sections(jd_text)
            
            # Extract requirements
            required_skills = self._extract_skills(sections.get("requirements", ""))
            preferred_skills = self._extract_skills(sections.get("preferred_qualifications", ""))
            
            # Extract experience requirements
            experience = self._extract_experience(jd_text)
            
            # Extract education requirements
            education = self._extract_education(jd_text)
            
            # Generate embeddings if available
            embeddings = None
            if self.embedder:
                embeddings = self.embedder.get_embedding(jd_text).tolist()
            
            # Structure the results
            result = {
                "title": self._extract_title(jd_text),
                "summary": self._generate_summary(jd_text),
                "required_skills": required_skills,
                "preferred_skills": preferred_skills,
                "experience": experience,
                "education": education,
                "sections": sections,
                "embeddings": embeddings
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing job description: {str(e)}")
            raise
    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from the job description."""
        # In a real implementation, this would use more sophisticated NLP
        # Simple regex-based section extraction for demonstration
        sections = {}
        
        # Common section headers in job descriptions
        section_patterns = [
            (r"(?i)job\s+summary|summary|about\s+the\s+role", "summary"),
            (r"(?i)responsibilities|duties|what\s+you\'ll\s+do", "responsibilities"),
            (r"(?i)requirements|qualifications|what\s+you\'ll\s+need", "requirements"),
            (r"(?i)preferred\s+qualifications|nice\s+to\s+have", "preferred_qualifications"),
            (r"(?i)benefits|perks|what\s+we\s+offer", "benefits"),
            (r"(?i)about\s+us|company|who\s+we\s+are", "about_company")
        ]
        
        for pattern, section_name in section_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start_idx = match.end()
                # Find the next section header
                next_section_start = len(text)
                for next_pattern, _ in section_patterns:
                    next_match = re.search(next_pattern, text[start_idx:], re.IGNORECASE)
                    if next_match:
                        next_section_idx = start_idx + next_match.start()
                        if next_section_idx < next_section_start:
                            next_section_start = next_section_idx
                
                # Extract the section content
                section_content = text[start_idx:next_section_start].strip()
                sections[section_name] = section_content
        
        return sections
    
    def _extract_title(self, text: str) -> str:
        """Extract the job title from the text."""
        # Simple heuristic: first line is often the title
        lines = text.strip().split('\n')
        if lines:
            return lines[0].strip()
        return "Unknown Position"
    
    def _generate_summary(self, text: str) -> str:
        """Generate a summary of the job description."""
        # In real implementation, this would use LLM
        # Simplified version just takes the first paragraph
        paragraphs = text.strip().split('\n\n')
        if len(paragraphs) > 1:
            return paragraphs[1].strip()
        return "No summary available"
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills from text."""
        # In real implementation, this would use NER and skill taxonomy
        # Simple keyword-based extraction for demonstration
        common_skills = [
            "python", "java", "javascript", "sql", "aws", "azure",
            "docker", "kubernetes", "react", "angular", "vue",
            "machine learning", "data analysis", "project management",
            "agile", "scrum", "communication", "leadership"
        ]
        
        found_skills = []
        for skill in common_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                found_skills.append(skill)
        
        return found_skills
    
    def _extract_experience(self, text: str) -> Dict[str, Any]:
        """Extract experience requirements."""
        # Look for patterns like "X+ years of experience"
        years_pattern = r'(\d+)\+?\s+years?\s+(?:of\s+)?experience'
        match = re.search(years_pattern, text, re.IGNORECASE)
        
        years = None
        if match:
            years = int(match.group(1))
        
        return {
            "minimum_years": years,
            "senior_level": years >= 5 if years else None
        }
    
    def _extract_education(self, text: str) -> Dict[str, Any]:
        """Extract education requirements."""
        # Look for degree requirements
        degree_patterns = {
            "bachelor": r"bachelor'?s|BA|BS|B\.A\.|B\.S\.",
            "master": r"master'?s|MA|MS|M\.A\.|M\.S\.",
            "phd": r"ph\.?d\.?|doctorate"
        }
        
        required_degrees = []
        for degree, pattern in degree_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                required_degrees.append(degree)
        
        return {
            "required_degrees": required_degrees,
            "degree_required": len(required_degrees) > 0
        }
    
    async def _store_analysis_result(self, jd_id: str, analysis: Dict[str, Any]) -> None:
        """Store the analysis result in the database."""
        if not self.db_manager:
            self.logger.warning("No database manager available, skipping storage")
            return
        
        try:
            # Convert analysis to JSON string
            analysis_json = json.dumps(analysis)
            
            # Store in database
            query = """
                INSERT INTO job_descriptions (jd_id, title, analysis, created_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (jd_id) DO UPDATE SET
                    title = excluded.title,
                    analysis = excluded.analysis,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            await self.db_manager.execute(
                query, 
                (jd_id, analysis.get("title", "Untitled Position"), analysis_json)
            )
            
            self.logger.info(f"Stored analysis for JD ID: {jd_id}")
            
        except Exception as e:
            self.logger.error(f"Error storing analysis result: {str(e)}")
            raise
