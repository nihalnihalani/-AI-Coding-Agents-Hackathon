from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
import os
import tempfile
import uuid

from .base_tool import BaseTool, ToolExecutionResult
from ..services.document_service import DocumentService
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class DocumentTool(BaseTool):
    """Document management tool for file processing and content generation."""
    
    def __init__(self):
        super().__init__(
            name="document_tool",
            description="Document processing, analysis, and generation tool"
        )
        
        self.document_service = DocumentService()
        self.temp_storage = {}  # In-memory storage for demo purposes
        
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Execute document actions."""
        try:
            if action == "process_resume":
                return await self._process_resume(parameters)
            elif action == "analyze_document":
                return await self._analyze_document(parameters)
            elif action == "generate_welcome_packet":
                return await self._generate_welcome_packet(parameters)
            elif action == "create_training_checklist":
                return await self._create_training_checklist(parameters)
            elif action == "generate_role_guide":
                return await self._generate_role_guide(parameters)
            elif action == "create_team_introduction":
                return await self._create_team_introduction(parameters)
            elif action == "generate_first_day_agenda":
                return await self._generate_first_day_agenda(parameters)
            elif action == "create_policy_summary":
                return await self._create_policy_summary(parameters)
            elif action == "store_document":
                return await self._store_document(parameters)
            elif action == "retrieve_document":
                return await self._retrieve_document(parameters)
            else:
                return ToolExecutionResult(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            logger.error(f"Error executing document action {action}: {e}")
            return ToolExecutionResult(
                success=False,
                error=f"Document action failed: {str(e)}"
            )
    
    async def _process_resume(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Process a resume file and extract information."""
        try:
            file_content = parameters.get("file_content")  # bytes
            filename = parameters.get("filename")
            job_role = parameters.get("job_role", "General Employee")
            
            if not file_content or not filename:
                return ToolExecutionResult(
                    success=False,
                    error="File content and filename are required"
                )
            
            # Process the resume
            user_profile, doc_analysis = await self.document_service.process_resume(
                file_content, filename, job_role
            )
            
            # Store the processed results
            document_id = doc_analysis.document_id
            self.temp_storage[document_id] = {
                "user_profile": user_profile.dict(),
                "analysis": doc_analysis.dict(),
                "processed_at": datetime.now().isoformat()
            }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": document_id,
                    "user_profile": user_profile.dict(),
                    "analysis_summary": doc_analysis.analysis_summary,
                    "extracted_skills": user_profile.skills,
                    "experience_years": user_profile.experience_years,
                    "job_role": job_role,
                    "confidence_scores": doc_analysis.confidence_scores,
                    "message": "Resume processed successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error processing resume: {str(e)}"
            )
    
    async def _analyze_document(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Analyze any document type for onboarding relevant information."""
        try:
            file_content = parameters.get("file_content")
            filename = parameters.get("filename")
            document_type = parameters.get("document_type", "general")
            
            if not file_content or not filename:
                return ToolExecutionResult(
                    success=False,
                    error="File content and filename are required"
                )
            
            # Analyze the document
            doc_analysis = await self.document_service.analyze_company_document(
                file_content, filename, document_type
            )
            
            # Store the analysis
            self.temp_storage[doc_analysis.document_id] = {
                "analysis": doc_analysis.dict(),
                "analyzed_at": datetime.now().isoformat()
            }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": doc_analysis.document_id,
                    "document_type": document_type,
                    "analysis_summary": doc_analysis.analysis_summary,
                    "key_points": self._extract_key_points(doc_analysis.analysis_summary),
                    "confidence_score": doc_analysis.confidence_scores.get("overall", 0.8),
                    "message": "Document analyzed successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error analyzing document: {str(e)}"
            )
    
    async def _generate_welcome_packet(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Generate a personalized welcome packet for new employee."""
        try:
            employee_name = parameters.get("employee_name", "New Employee")
            job_title = parameters.get("job_title", "Team Member")
            start_date = parameters.get("start_date", datetime.now().strftime("%Y-%m-%d"))
            department = parameters.get("department", "General")
            manager_name = parameters.get("manager_name", "Manager")
            
            # Generate welcome packet content
            welcome_packet = self._create_welcome_packet_content(
                employee_name, job_title, start_date, department, manager_name
            )
            
            # Store the document
            document_id = str(uuid.uuid4())
            self.temp_storage[document_id] = {
                "document_type": "welcome_packet",
                "content": welcome_packet,
                "employee_name": employee_name,
                "created_at": datetime.now().isoformat()
            }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": document_id,
                    "document_type": "welcome_packet",
                    "employee_name": employee_name,
                    "content_preview": welcome_packet[:500] + "..." if len(welcome_packet) > 500 else welcome_packet,
                    "full_content": welcome_packet,
                    "message": "Welcome packet generated successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error generating welcome packet: {str(e)}"
            )
    
    async def _create_training_checklist(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a personalized training checklist."""
        try:
            job_role = parameters.get("job_role", "General Employee")
            employee_name = parameters.get("employee_name", "New Employee")
            experience_level = parameters.get("experience_level", "intermediate")
            specific_skills = parameters.get("specific_skills", [])
            
            # Generate training checklist
            checklist = self._create_training_checklist_content(
                job_role, employee_name, experience_level, specific_skills
            )
            
            document_id = str(uuid.uuid4())
            self.temp_storage[document_id] = {
                "document_type": "training_checklist",
                "content": checklist,
                "job_role": job_role,
                "employee_name": employee_name,
                "created_at": datetime.now().isoformat()
            }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": document_id,
                    "document_type": "training_checklist",
                    "job_role": job_role,
                    "employee_name": employee_name,
                    "checklist_items": self._extract_checklist_items(checklist),
                    "full_content": checklist,
                    "message": "Training checklist created successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating training checklist: {str(e)}"
            )
    
    async def _generate_role_guide(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Generate a comprehensive role-specific guide."""
        try:
            job_title = parameters.get("job_title", "Team Member")
            department = parameters.get("department", "General")
            team_info = parameters.get("team_info", {})
            key_responsibilities = parameters.get("key_responsibilities", [])
            
            # Generate role guide
            role_guide = self._create_role_guide_content(
                job_title, department, team_info, key_responsibilities
            )
            
            document_id = str(uuid.uuid4())
            self.temp_storage[document_id] = {
                "document_type": "role_guide",
                "content": role_guide,
                "job_title": job_title,
                "department": department,
                "created_at": datetime.now().isoformat()
            }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": document_id,
                    "document_type": "role_guide",
                    "job_title": job_title,
                    "department": department,
                    "sections": ["Overview", "Responsibilities", "Success Metrics", "Resources"],
                    "full_content": role_guide,
                    "message": "Role guide generated successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error generating role guide: {str(e)}"
            )
    
    async def _create_team_introduction(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a team introduction document."""
        try:
            team_name = parameters.get("team_name", "Our Team")
            team_members = parameters.get("team_members", [])
            team_mission = parameters.get("team_mission", "")
            projects = parameters.get("projects", [])
            
            # Generate team introduction
            team_intro = self._create_team_introduction_content(
                team_name, team_members, team_mission, projects
            )
            
            document_id = str(uuid.uuid4())
            self.temp_storage[document_id] = {
                "document_type": "team_introduction",
                "content": team_intro,
                "team_name": team_name,
                "created_at": datetime.now().isoformat()
            }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": document_id,
                    "document_type": "team_introduction",
                    "team_name": team_name,
                    "team_size": len(team_members),
                    "full_content": team_intro,
                    "message": "Team introduction created successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating team introduction: {str(e)}"
            )
    
    async def _generate_first_day_agenda(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Generate a personalized first day agenda."""
        try:
            employee_name = parameters.get("employee_name", "New Employee")
            start_time = parameters.get("start_time", "9:00 AM")
            manager_name = parameters.get("manager_name", "Manager")
            buddy_name = parameters.get("buddy_name")
            office_location = parameters.get("office_location", "Main Office")
            
            # Generate first day agenda
            agenda = self._create_first_day_agenda_content(
                employee_name, start_time, manager_name, buddy_name, office_location
            )
            
            document_id = str(uuid.uuid4())
            self.temp_storage[document_id] = {
                "document_type": "first_day_agenda",
                "content": agenda,
                "employee_name": employee_name,
                "created_at": datetime.now().isoformat()
            }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": document_id,
                    "document_type": "first_day_agenda",
                    "employee_name": employee_name,
                    "agenda_items": self._extract_agenda_items(agenda),
                    "full_content": agenda,
                    "message": "First day agenda generated successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error generating first day agenda: {str(e)}"
            )
    
    async def _create_policy_summary(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a summary of important company policies."""
        try:
            policies = parameters.get("policies", [])
            employee_role = parameters.get("employee_role", "General Employee")
            department = parameters.get("department", "General")
            
            # Generate policy summary
            policy_summary = self._create_policy_summary_content(
                policies, employee_role, department
            )
            
            document_id = str(uuid.uuid4())
            self.temp_storage[document_id] = {
                "document_type": "policy_summary",
                "content": policy_summary,
                "employee_role": employee_role,
                "created_at": datetime.now().isoformat()
            }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": document_id,
                    "document_type": "policy_summary",
                    "employee_role": employee_role,
                    "policies_count": len(policies),
                    "full_content": policy_summary,
                    "message": "Policy summary created successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating policy summary: {str(e)}"
            )
    
    async def _store_document(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Store a document for later retrieval."""
        try:
            document_id = parameters.get("document_id") or str(uuid.uuid4())
            content = parameters.get("content", "")
            document_type = parameters.get("document_type", "general")
            metadata = parameters.get("metadata", {})
            
            self.temp_storage[document_id] = {
                "document_type": document_type,
                "content": content,
                "metadata": metadata,
                "stored_at": datetime.now().isoformat()
            }
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": document_id,
                    "document_type": document_type,
                    "content_length": len(content),
                    "message": "Document stored successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error storing document: {str(e)}"
            )
    
    async def _retrieve_document(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Retrieve a stored document."""
        try:
            document_id = parameters.get("document_id")
            
            if not document_id:
                return ToolExecutionResult(
                    success=False,
                    error="Document ID is required"
                )
            
            if document_id not in self.temp_storage:
                return ToolExecutionResult(
                    success=False,
                    error="Document not found"
                )
            
            document = self.temp_storage[document_id]
            
            return ToolExecutionResult(
                success=True,
                data={
                    "document_id": document_id,
                    "document_type": document.get("document_type"),
                    "content": document.get("content"),
                    "metadata": document.get("metadata", {}),
                    "stored_at": document.get("stored_at"),
                    "message": "Document retrieved successfully"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error retrieving document: {str(e)}"
            )
    
    def _create_welcome_packet_content(self, employee_name: str, job_title: str, 
                                     start_date: str, department: str, manager_name: str) -> str:
        """Create welcome packet content."""
        return f"""
# Welcome to the Team, {employee_name}! 🎉

We're thrilled to have you join us as our new {job_title} in the {department} department. Your official start date is {start_date}.

## What to Expect on Your First Day

### Arrival and Check-in
- **Time**: 9:00 AM
- **Location**: Main Reception
- **Contact**: {manager_name} (your manager)

### Your First Week Overview
1. **Day 1**: Welcome, workspace setup, and orientation
2. **Day 2**: Team introductions and system access
3. **Day 3**: Training programs and documentation review
4. **Day 4**: Project overview and initial assignments
5. **Day 5**: First week review and planning

## Important Information

### What to Bring
- Government-issued ID
- Completed tax forms (if not submitted online)
- Banking information for direct deposit
- Emergency contact information

### Your Workspace
- A dedicated workspace has been prepared for you
- All necessary equipment will be provided
- IT will help with setup and access

### Key Contacts
- **Manager**: {manager_name}
- **HR Representative**: [HR Contact]
- **IT Support**: [IT Contact]
- **Onboarding Buddy**: [Buddy Name]

## Company Culture & Values

We pride ourselves on:
- **Innovation**: Always looking for better solutions
- **Collaboration**: Working together to achieve great things
- **Growth**: Supporting continuous learning and development
- **Integrity**: Doing the right thing, always

## Next Steps

1. Review this welcome packet thoroughly
2. Complete any remaining pre-boarding tasks
3. Prepare questions for your first day
4. Get excited about your new journey with us!

We can't wait to meet you and see the amazing contributions you'll make to our team!

---
*Generated on {datetime.now().strftime('%Y-%m-%d')} by Aura AI Onboarding Assistant*
"""
    
    def _create_training_checklist_content(self, job_role: str, employee_name: str, 
                                         experience_level: str, specific_skills: List[str]) -> str:
        """Create training checklist content."""
        return f"""
# Training Checklist for {employee_name}
## Role: {job_role} | Experience Level: {experience_level.title()}

### Mandatory Training (All Employees)
- [ ] **Security Awareness Training** (Required - Complete within 7 days)
- [ ] **Code of Conduct** (Required - Complete within 7 days)
- [ ] **Data Privacy & GDPR** (Required - Complete within 14 days)
- [ ] **Anti-Harassment & Inclusion** (Required - Complete within 14 days)
- [ ] **Emergency Procedures** (Required - Complete within 7 days)

### Role-Specific Training ({job_role})
- [ ] **{job_role} Fundamentals** (Complete within 14 days)
- [ ] **Company Systems & Tools** (Complete within 10 days)
- [ ] **Quality Standards & Best Practices** (Complete within 21 days)
- [ ] **Project Management Methodology** (Complete within 21 days)
- [ ] **Performance Metrics & KPIs** (Complete within 30 days)

### Technical Skills Enhancement
{self._generate_technical_skills_section(specific_skills, experience_level)}

### Soft Skills Development
- [ ] **Communication Best Practices** (Recommended - Complete within 30 days)
- [ ] **Time Management Techniques** (Optional - Complete within 45 days)
- [ ] **Conflict Resolution** (Optional - Complete within 60 days)
- [ ] **Leadership Principles** (Optional - Complete within 60 days)

### Department-Specific Training
- [ ] **Department Overview & Structure** (Complete within 14 days)
- [ ] **Team Workflows & Processes** (Complete within 21 days)
- [ ] **Client/Customer Interaction Guidelines** (Complete within 30 days)
- [ ] **Escalation Procedures** (Complete within 21 days)

### Progress Tracking
- **Week 1 Goal**: Complete all mandatory training
- **Week 2 Goal**: Finish role-specific fundamentals
- **Week 3 Goal**: Complete technical skills assessment
- **Week 4 Goal**: Begin advanced training modules

### Resources & Support
- **Learning Management System**: [LMS Portal]
- **Training Coordinator**: [Contact Info]
- **Technical Mentor**: [Mentor Name]
- **Questions & Support**: [Help Channel]

---
*Checklist generated on {datetime.now().strftime('%Y-%m-%d')}*
*Training plan customized for {experience_level} level {job_role}*
"""
    
    def _generate_technical_skills_section(self, specific_skills: List[str], experience_level: str) -> str:
        """Generate technical skills training section based on role and experience."""
        if not specific_skills:
            return "- [ ] **Role-Specific Technical Training** (Complete within 30 days)"
        
        skills_section = ""
        for skill in specific_skills:
            if experience_level.lower() == "beginner":
                skills_section += f"- [ ] **{skill} Fundamentals** (Complete within 30 days)\n"
            elif experience_level.lower() == "advanced":
                skills_section += f"- [ ] **Advanced {skill} Techniques** (Complete within 21 days)\n"
            else:
                skills_section += f"- [ ] **{skill} Best Practices** (Complete within 30 days)\n"
        
        return skills_section
    
    def _create_role_guide_content(self, job_title: str, department: str, 
                                 team_info: Dict[str, Any], key_responsibilities: List[str]) -> str:
        """Create role-specific guide content."""
        return f"""
# {job_title} Role Guide
## Department: {department}

### Role Overview
As a {job_title} in our {department} department, you'll play a crucial role in our organization's success. This guide outlines everything you need to know about your position.

### Key Responsibilities
{self._format_responsibilities(key_responsibilities)}

### Success Metrics
- **90 Days**: Fully integrated into team workflows
- **6 Months**: Contributing independently to projects
- **1 Year**: Mentoring newer team members and driving initiatives

### Team Structure
{self._format_team_info(team_info)}

### Tools & Technologies
- **Primary Tools**: [List of main tools]
- **Communication**: Slack, Email, Video Conferencing
- **Project Management**: [PM Tool]
- **Documentation**: [Wiki/Knowledge Base]

### Career Development
- **Growth Path**: [Career progression options]
- **Skill Development**: [Recommended skills to develop]
- **Training Opportunities**: [Available training programs]
- **Mentorship**: [Mentorship program details]

### Performance Expectations
- **Quality**: Deliver high-quality work that meets standards
- **Collaboration**: Work effectively with team members
- **Communication**: Keep stakeholders informed of progress
- **Initiative**: Proactively identify and solve problems
- **Learning**: Continuously improve skills and knowledge

### Resources
- **Role-specific documentation**: [Links]
- **Best practices guide**: [Links]
- **Team playbooks**: [Links]
- **Industry resources**: [External resources]

---
*Role guide generated on {datetime.now().strftime('%Y-%m-%d')}*
"""
    
    def _format_responsibilities(self, responsibilities: List[str]) -> str:
        """Format responsibilities list."""
        if not responsibilities:
            return "- Collaborate with team members on various projects\n- Contribute to departmental goals and objectives"
        
        return "\n".join([f"- {resp}" for resp in responsibilities])
    
    def _format_team_info(self, team_info: Dict[str, Any]) -> str:
        """Format team information."""
        if not team_info:
            return "Your team structure and reporting relationships will be discussed during orientation."
        
        formatted = ""
        if "size" in team_info:
            formatted += f"- **Team Size**: {team_info['size']} members\n"
        if "manager" in team_info:
            formatted += f"- **Reports To**: {team_info['manager']}\n"
        if "peers" in team_info:
            formatted += f"- **Peer Roles**: {', '.join(team_info['peers'])}\n"
        
        return formatted
    
    def _create_team_introduction_content(self, team_name: str, team_members: List[Dict], 
                                        team_mission: str, projects: List[str]) -> str:
        """Create team introduction content."""
        members_section = ""
        for member in team_members:
            name = member.get("name", "Team Member")
            role = member.get("role", "Team Member")
            bio = member.get("bio", "")
            members_section += f"### {name} - {role}\n{bio}\n\n"
        
        projects_section = "\n".join([f"- {project}" for project in projects]) if projects else "- Various ongoing initiatives"
        
        return f"""
# Meet {team_name}! 👥

{team_mission}

## Our Team Members

{members_section}

## Current Projects
{projects_section}

## Team Culture
- **Collaboration**: We work together to achieve common goals
- **Innovation**: We encourage creative thinking and new ideas  
- **Support**: We help each other grow and succeed
- **Fun**: We believe work should be enjoyable!

## Communication
- **Daily Standups**: [Time/Frequency]
- **Team Meetings**: [Schedule]
- **Slack Channel**: #{team_name.lower().replace(' ', '-')}
- **Office Hours**: [Available times for questions]

## Getting Started
1. Join our team Slack channel
2. Schedule coffee chats with team members
3. Review our current project documentation
4. Ask questions - we're here to help!

Welcome to the team! 🚀

---
*Team introduction created on {datetime.now().strftime('%Y-%m-%d')}*
"""
    
    def _create_first_day_agenda_content(self, employee_name: str, start_time: str,
                                       manager_name: str, buddy_name: Optional[str], 
                                       office_location: str) -> str:
        """Create first day agenda content."""
        buddy_section = f"- **10:30 AM**: Meet your onboarding buddy, {buddy_name}" if buddy_name else ""
        
        return f"""
# {employee_name}'s First Day Agenda
## Date: {datetime.now().strftime('%A, %B %d, %Y')}
## Location: {office_location}

### Morning Schedule

- **{start_time}**: Arrival and Welcome
  - Check in at reception
  - Meet {manager_name} (your manager)
  - Collect welcome packet and badges

- **9:30 AM**: Workspace Setup
  - Tour of your workspace
  - Equipment setup and testing
  - Basic IT setup assistance

{buddy_section}

- **11:00 AM**: HR Orientation
  - Benefits overview
  - Complete remaining paperwork
  - Security and access setup

- **12:00 PM**: Lunch Break
  - Welcome lunch with your team
  - Informal getting-to-know-you time

### Afternoon Schedule

- **1:00 PM**: Company Overview
  - Mission, vision, and values
  - Company history and culture
  - Organizational structure

- **2:00 PM**: Department Introduction
  - Meet department leadership
  - Understand department goals
  - Review current initiatives

- **3:00 PM**: Role-Specific Orientation
  - Detailed job responsibilities
  - Performance expectations
  - Initial goals and objectives

- **4:00 PM**: Systems and Tools Training
  - IT systems walkthrough
  - Software installation and setup
  - Communication tools setup

- **4:30 PM**: First Day Wrap-up
  - Q&A session with {manager_name}
  - Schedule upcoming meetings
  - Plan for tomorrow and the week ahead

### What to Bring
- Government-issued photo ID
- Completed pre-boarding forms
- Banking information for payroll
- Emergency contact information
- Any questions you have!

### Who You'll Meet Today
- **{manager_name}** - Your Manager
- **HR Representative** - For orientation and paperwork
- **IT Support** - For technical setup
{f"- **{buddy_name}** - Your Onboarding Buddy" if buddy_name else ""}
- **Team Members** - During lunch and introductions

### After Your First Day
- Review welcome materials
- Complete any pending setup tasks
- Prepare questions for tomorrow
- Rest well - you've got this! 💪

---
*Agenda prepared on {datetime.now().strftime('%Y-%m-%d')}*
*Questions? Contact {manager_name} or HR*
"""
    
    def _create_policy_summary_content(self, policies: List[str], employee_role: str, department: str) -> str:
        """Create policy summary content."""
        policies_section = ""
        if policies:
            for policy in policies:
                policies_section += f"### {policy}\n[Summary of {policy} relevant to {employee_role}]\n\n"
        else:
            policies_section = "### Key Company Policies\nDetailed policy information will be provided during orientation.\n\n"
        
        return f"""
# Company Policy Summary
## For: {employee_role} - {department} Department

## Important Policies Overview

{policies_section}

### Code of Conduct
All employees are expected to maintain professional behavior and adhere to our ethical standards.

### Data Privacy & Security
Protecting company and customer data is everyone's responsibility. Follow all security protocols.

### Communication Guidelines
Professional communication is expected in all interactions, both internal and external.

### Performance Standards
Clear expectations for quality, productivity, and collaboration in your role.

### Professional Development
Information about training opportunities, career growth, and skill development.

---
*Policy summary generated on {datetime.now().strftime('%Y-%m-%d')}*
*For detailed policies, refer to the employee handbook*
"""
    
    def _extract_key_points(self, analysis_summary: str) -> List[str]:
        """Extract key points from analysis summary."""
        # Simple extraction - could be made more sophisticated
        points = []
        lines = analysis_summary.split('\n')
        for line in lines:
            if line.strip() and (line.startswith('-') or line.startswith('•') or 'important' in line.lower()):
                points.append(line.strip())
        return points[:5]  # Return top 5 points
    
    def _extract_checklist_items(self, checklist_content: str) -> List[str]:
        """Extract checklist items from content."""
        items = []
        lines = checklist_content.split('\n')
        for line in lines:
            if '- [ ]' in line:
                item = line.replace('- [ ]', '').strip()
                if item:
                    items.append(item)
        return items
    
    def _extract_agenda_items(self, agenda_content: str) -> List[Dict[str, str]]:
        """Extract agenda items with times."""
        items = []
        lines = agenda_content.split('\n')
        for line in lines:
            if '**' in line and 'AM' in line or 'PM' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    time = parts[0].replace('**', '').replace('-', '').strip()
                    activity = parts[1].strip()
                    items.append({"time": time, "activity": activity})
        return items
    
    def is_available(self) -> bool:
        """Check if the document tool is available."""
        return True  # Always available for basic document operations
    
    def get_available_actions(self) -> List[str]:
        """Get list of available actions."""
        return [
            "process_resume",
            "analyze_document",
            "generate_welcome_packet",
            "create_training_checklist",
            "generate_role_guide",
            "create_team_introduction",
            "generate_first_day_agenda",
            "create_policy_summary",
            "store_document",
            "retrieve_document"
        ]