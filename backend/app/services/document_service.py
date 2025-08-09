from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
from datetime import datetime
import uuid
import io
import PyPDF2
from PIL import Image

from ..models.schemas import DocumentAnalysis, UserProfile, LLMProvider
from .llm_service import LLMRouter
from ..core.logging import get_logger

logger = get_logger(__name__)

class DocumentService:
    """Service for processing and analyzing documents."""
    
    def __init__(self):
        self.llm_router = LLMRouter()
    
    async def process_resume(self, file_content: bytes, filename: str, job_role: str) -> Tuple[UserProfile, DocumentAnalysis]:
        """Process a resume file and extract relevant information."""
        try:
            # Determine file type
            file_type = self._get_file_type(filename)
            
            # Extract text content
            extracted_text = await self._extract_text_content(file_content, file_type)
            
            # Analyze with appropriate LLM
            analysis = await self._analyze_resume_content(extracted_text, job_role, file_type)
            
            # Create user profile from analysis
            user_profile = self._create_user_profile(analysis, job_role)
            
            # Create document analysis record
            doc_analysis = DocumentAnalysis(
                document_id=str(uuid.uuid4()),
                document_type="resume",
                file_name=filename,
                analysis_summary=analysis.get("summary", ""),
                extracted_data=analysis,
                confidence_scores=analysis.get("confidence_scores", {}),
                llm_used=LLMProvider.GEMINI,  # Primary choice for document analysis
                created_at=datetime.now()
            )
            
            return user_profile, doc_analysis
            
        except Exception as e:
            logger.error(f"Error processing resume: {e}")
            raise Exception(f"Failed to process resume: {str(e)}")
    
    def _get_file_type(self, filename: str) -> str:
        """Determine file type from filename."""
        extension = filename.lower().split('.')[-1]
        
        if extension == 'pdf':
            return 'pdf'
        elif extension in ['jpg', 'jpeg', 'png', 'gif']:
            return 'image'
        elif extension in ['doc', 'docx']:
            return 'word'
        elif extension == 'txt':
            return 'text'
        else:
            return 'unknown'
    
    async def _extract_text_content(self, file_content: bytes, file_type: str) -> str:
        """Extract text content from various file types."""
        try:
            if file_type == 'pdf':
                return self._extract_pdf_text(file_content)
            elif file_type == 'image':
                return await self._extract_image_text(file_content)
            elif file_type == 'text':
                return file_content.decode('utf-8')
            elif file_type in ['word', 'unknown']:
                # For Word docs and unknown types, we'd need additional libraries
                logger.warning(f"File type {file_type} not fully supported, attempting text extraction")
                return file_content.decode('utf-8', errors='ignore')
            else:
                raise Exception(f"Unsupported file type: {file_type}")
                
        except Exception as e:
            logger.error(f"Error extracting text from {file_type}: {e}")
            raise Exception(f"Failed to extract text from document: {str(e)}")
    
    def _extract_pdf_text(self, pdf_content: bytes) -> str:
        """Extract text from PDF content."""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_content))
            text = ""
            
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    async def _extract_image_text(self, image_content: bytes) -> str:
        """Extract text from image using OCR (placeholder for actual OCR implementation)."""
        try:
            # In a real implementation, you would use OCR libraries like Tesseract
            # For now, return a placeholder
            logger.info("Image OCR processing - placeholder implementation")
            return "Extracted text from image (OCR placeholder)"
        except Exception as e:
            logger.error(f"Error extracting image text: {e}")
            raise Exception(f"Failed to extract text from image: {str(e)}")
    
    async def _analyze_resume_content(self, text_content: str, job_role: str, file_type: str) -> Dict[str, Any]:
        """Analyze resume content using LLM."""
        try:
            analysis_prompt = f"""
            Analyze the following resume content for a {job_role} position. Extract and structure the following information:

            1. Personal Information:
               - Name
               - Contact details (email, phone)
               - Location

            2. Professional Experience:
               - Job titles and companies
               - Years of experience
               - Key responsibilities and achievements
               - Relevant experience for {job_role}

            3. Skills and Technologies:
               - Technical skills
               - Soft skills
               - Programming languages, tools, frameworks
               - Industry-specific skills

            4. Education:
               - Degrees and institutions
               - Graduation dates
               - Relevant coursework
               - GPA (if mentioned)

            5. Certifications and Additional Information:
               - Professional certifications
               - Languages spoken
               - Publications, projects, awards

            6. Gap Analysis:
               - Skills that match the {job_role} requirements
               - Areas where additional training might be needed
               - Strengths for the role
               - Potential growth areas

            Resume Content:
            {text_content}

            Please provide the analysis in a structured JSON format with confidence scores for each extracted element.
            """
            
            # Use LLM router to get the best model for document analysis
            llm_response = await self.llm_router.generate_response(
                "document_analysis", 
                analysis_prompt,
                max_tokens=2000
            )
            
            # Parse the response (in a real implementation, you'd have more robust parsing)
            analysis_text = llm_response.get("response", "")
            
            return {
                "raw_analysis": analysis_text,
                "summary": f"Resume analysis for {job_role} position",
                "llm_used": llm_response.get("llm_used", "unknown"),
                "confidence_scores": {
                    "overall": 0.85,
                    "skills_extraction": 0.90,
                    "experience_extraction": 0.88,
                    "education_extraction": 0.92
                },
                "extracted_skills": self._extract_skills_from_analysis(analysis_text),
                "extracted_experience": self._extract_experience_from_analysis(analysis_text),
                "job_role_match": self._calculate_role_match(analysis_text, job_role)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing resume content: {e}")
            raise Exception(f"Failed to analyze resume: {str(e)}")
    
    def _extract_skills_from_analysis(self, analysis_text: str) -> List[str]:
        """Extract skills list from LLM analysis (placeholder implementation)."""
        # In a real implementation, this would parse the structured LLM response
        # For now, return some common skills as placeholders
        return [
            "Python", "JavaScript", "Project Management", "Communication",
            "Problem Solving", "Team Leadership", "Data Analysis"
        ]
    
    def _extract_experience_from_analysis(self, analysis_text: str) -> List[Dict[str, Any]]:
        """Extract experience list from LLM analysis (placeholder implementation)."""
        # In a real implementation, this would parse the structured LLM response
        return [
            {
                "title": "Software Engineer",
                "company": "Tech Company",
                "duration": "2+ years",
                "description": "Developed web applications and APIs"
            }
        ]
    
    def _calculate_role_match(self, analysis_text: str, job_role: str) -> Dict[str, Any]:
        """Calculate how well the resume matches the job role."""
        # Placeholder implementation
        return {
            "match_percentage": 75,
            "matching_skills": ["Python", "Project Management", "Team Leadership"],
            "missing_skills": ["Advanced Machine Learning", "Cloud Architecture"],
            "recommendations": [
                "Consider additional training in cloud technologies",
                "Highlight project management experience more prominently"
            ]
        }
    
    def _create_user_profile(self, analysis: Dict[str, Any], job_role: str) -> UserProfile:
        """Create a UserProfile from the resume analysis."""
        try:
            return UserProfile(
                user_id=str(uuid.uuid4()),
                name="John Doe",  # Would be extracted from analysis
                email="john.doe@example.com",  # Would be extracted from analysis
                skills=analysis.get("extracted_skills", []),
                experience_years=3,  # Would be calculated from analysis
                education=[
                    {
                        "degree": "Bachelor's in Computer Science",
                        "institution": "University of Technology",
                        "year": "2020"
                    }
                ],
                previous_roles=analysis.get("extracted_experience", []),
                preferences={
                    "target_role": job_role,
                    "communication_style": "detailed",
                    "learning_pace": "moderate"
                }
            )
        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            raise Exception(f"Failed to create user profile: {str(e)}")
    
    async def analyze_company_document(self, file_content: bytes, filename: str, document_type: str) -> DocumentAnalysis:
        """Analyze company documents like policies, handbooks, etc."""
        try:
            file_type = self._get_file_type(filename)
            extracted_text = await self._extract_text_content(file_content, file_type)
            
            analysis_prompt = f"""
            Analyze this company {document_type} document and extract key information that would be relevant for new employee onboarding:

            1. Key policies and procedures
            2. Important dates and deadlines
            3. Contact information and resources
            4. Required actions for new employees
            5. Cultural and behavioral guidelines

            Document Content:
            {extracted_text}

            Provide a structured summary that can be used to create onboarding tasks and provide guidance to new employees.
            """
            
            llm_response = await self.llm_router.generate_response(
                "document_analysis", 
                analysis_prompt
            )
            
            return DocumentAnalysis(
                document_id=str(uuid.uuid4()),
                document_type=document_type,
                file_name=filename,
                analysis_summary=llm_response.get("response", ""),
                extracted_data={"raw_text": extracted_text},
                confidence_scores={"overall": 0.80},
                llm_used=LLMProvider.GEMINI,
                created_at=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing company document: {e}")
            raise Exception(f"Failed to analyze document: {str(e)}")