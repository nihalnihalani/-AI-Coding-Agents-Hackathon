from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta
import base64

from github import Github, GithubException
from github.Repository import Repository
from github.Issue import Issue

from .base_tool import BaseTool, ToolExecutionResult
from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

class GitHubTool(BaseTool):
    """GitHub integration tool for repository management and project setup."""
    
    def __init__(self):
        super().__init__(
            name="github_tool",
            description="GitHub integration for repository access, issue management, and project setup"
        )
        
        self.client = None
        self.user = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize GitHub client."""
        try:
            if not settings.github_token:
                logger.warning("GitHub token not configured")
                return
            
            self.client = Github(settings.github_token)
            self.user = self.client.get_user()
            
            logger.info(f"GitHub client initialized successfully. User: {self.user.login}")
            
        except GithubException as e:
            logger.error(f"Error initializing GitHub client: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Unexpected error initializing GitHub: {e}")
            self.client = None
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Execute GitHub actions."""
        try:
            if action == "create_repository":
                return await self._create_repository(parameters)
            elif action == "add_collaborator":
                return await self._add_collaborator(parameters)
            elif action == "create_issue":
                return await self._create_issue(parameters)
            elif action == "create_project_board":
                return await self._create_project_board(parameters)
            elif action == "setup_onboarding_repo":
                return await self._setup_onboarding_repo(parameters)
            elif action == "create_branch":
                return await self._create_branch(parameters)
            elif action == "create_pull_request":
                return await self._create_pull_request(parameters)
            elif action == "list_repositories":
                return await self._list_repositories(parameters)
            elif action == "get_repository_info":
                return await self._get_repository_info(parameters)
            elif action == "create_onboarding_issues":
                return await self._create_onboarding_issues(parameters)
            elif action == "assign_mentor":
                return await self._assign_mentor(parameters)
            else:
                return ToolExecutionResult(
                    success=False,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            logger.error(f"Error executing GitHub action {action}: {e}")
            return ToolExecutionResult(
                success=False,
                error=f"GitHub action failed: {str(e)}"
            )
    
    async def _create_repository(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a new GitHub repository."""
        try:
            name = parameters.get("name")
            description = parameters.get("description", "")
            private = parameters.get("private", False)
            auto_init = parameters.get("auto_init", True)
            gitignore_template = parameters.get("gitignore_template")
            license_template = parameters.get("license_template")
            
            if not name:
                return ToolExecutionResult(
                    success=False,
                    error="Repository name is required"
                )
            
            # Create repository
            repo = self.user.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=auto_init,
                gitignore_template=gitignore_template,
                license_template=license_template
            )
            
            return ToolExecutionResult(
                success=True,
                data={
                    "repository_id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "private": repo.private,
                    "description": repo.description,
                    "created_at": repo.created_at.isoformat()
                }
            )
            
        except GithubException as e:
            return ToolExecutionResult(
                success=False,
                error=f"GitHub API error: {str(e)}"
            )
    
    async def _add_collaborator(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Add a collaborator to a repository."""
        try:
            repo_name = parameters.get("repository")
            username = parameters.get("username")
            permission = parameters.get("permission", "push")  # pull, push, admin, maintain, triage
            
            if not repo_name or not username:
                return ToolExecutionResult(
                    success=False,
                    error="Repository name and username are required"
                )
            
            repo = self.client.get_repo(repo_name)
            repo.add_to_collaborators(username, permission=permission)
            
            return ToolExecutionResult(
                success=True,
                data={
                    "repository": repo_name,
                    "username": username,
                    "permission": permission,
                    "message": f"Added {username} as collaborator with {permission} permission"
                }
            )
            
        except GithubException as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error adding collaborator: {str(e)}"
            )
    
    async def _create_issue(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a new issue in a repository."""
        try:
            repo_name = parameters.get("repository")
            title = parameters.get("title")
            body = parameters.get("body", "")
            assignees = parameters.get("assignees", [])
            labels = parameters.get("labels", [])
            milestone = parameters.get("milestone")
            
            if not repo_name or not title:
                return ToolExecutionResult(
                    success=False,
                    error="Repository name and issue title are required"
                )
            
            repo = self.client.get_repo(repo_name)
            
            # Create issue
            issue = repo.create_issue(
                title=title,
                body=body,
                assignees=assignees,
                labels=labels,
                milestone=milestone
            )
            
            return ToolExecutionResult(
                success=True,
                data={
                    "issue_id": issue.id,
                    "issue_number": issue.number,
                    "title": issue.title,
                    "url": issue.html_url,
                    "state": issue.state,
                    "assignees": [assignee.login for assignee in issue.assignees],
                    "labels": [label.name for label in issue.labels],
                    "created_at": issue.created_at.isoformat()
                }
            )
            
        except GithubException as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating issue: {str(e)}"
            )
    
    async def _setup_onboarding_repo(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Set up a complete onboarding repository for new employee."""
        try:
            employee_name = parameters.get("employee_name")
            employee_github = parameters.get("employee_github")
            job_title = parameters.get("job_title", "Developer")
            team = parameters.get("team", "Engineering")
            
            if not employee_name:
                return ToolExecutionResult(
                    success=False,
                    error="Employee name is required"
                )
            
            # Create repository name
            repo_name = f"onboarding-{employee_name.lower().replace(' ', '-')}"
            
            # Create repository
            repo_result = await self._create_repository({
                "name": repo_name,
                "description": f"Onboarding repository for {employee_name} ({job_title})",
                "private": True,
                "auto_init": True,
                "gitignore_template": "Python"
            })
            
            if not repo_result.success:
                return repo_result
            
            repo_full_name = repo_result.data["full_name"]
            repo = self.client.get_repo(repo_full_name)
            
            # Create onboarding files
            await self._create_onboarding_files(repo, employee_name, job_title, team)
            
            # Add employee as collaborator if GitHub username provided
            if employee_github:
                await self._add_collaborator({
                    "repository": repo_full_name,
                    "username": employee_github,
                    "permission": "push"
                })
            
            # Create onboarding issues
            issues_result = await self._create_onboarding_issues({
                "repository": repo_full_name,
                "employee_name": employee_name,
                "job_title": job_title,
                "assignee": employee_github
            })
            
            # Create project board
            project_result = await self._create_project_board({
                "repository": repo_full_name,
                "name": f"{employee_name} Onboarding",
                "description": f"Onboarding progress tracking for {employee_name}"
            })
            
            return ToolExecutionResult(
                success=True,
                data={
                    "repository": repo_result.data,
                    "issues_created": issues_result.data if issues_result.success else [],
                    "project_board": project_result.data if project_result.success else None,
                    "onboarding_files": [
                        "README.md",
                        "ONBOARDING.md", 
                        "FIRST_WEEK.md",
                        "RESOURCES.md"
                    ],
                    "message": f"Onboarding repository created successfully for {employee_name}"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error setting up onboarding repository: {str(e)}"
            )
    
    async def _create_onboarding_files(self, repo: Repository, employee_name: str, job_title: str, team: str):
        """Create onboarding documentation files."""
        try:
            # README.md
            readme_content = f"""# {employee_name}'s Onboarding Repository

Welcome to your personalized onboarding repository! This space contains everything you need to get started in your new role as {job_title} with the {team} team.

## 📋 Quick Start

1. Review the [Onboarding Guide](./ONBOARDING.md)
2. Complete your [First Week Checklist](./FIRST_WEEK.md)
3. Explore [Company Resources](./RESOURCES.md)
4. Track your progress using the Issues and Project board

## 🎯 Your Onboarding Goals

- [ ] Complete all setup tasks
- [ ] Meet your team members
- [ ] Complete required training
- [ ] Start contributing to projects
- [ ] Get comfortable with our processes

## 🤝 Need Help?

- Check the Issues tab for your onboarding tasks
- Reach out to your manager or buddy
- Ask questions in team Slack channels
- Use this repository to track your progress

---
*Generated by Aura AI Onboarding Assistant*
"""
            
            repo.create_file(
                "README.md",
                f"Initial onboarding setup for {employee_name}",
                readme_content
            )
            
            # ONBOARDING.md
            onboarding_content = f"""# Onboarding Guide for {employee_name}

## Welcome to the Team! 🎉

This guide will help you navigate your first few weeks as a {job_title} with our {team} team.

## Phase 1: Getting Started (Week 1)

### Administrative Tasks
- [ ] Complete HR paperwork
- [ ] Set up your workspace
- [ ] Get your equipment (laptop, monitor, etc.)
- [ ] Set up VPN and security tools

### Account Setup
- [ ] Company email account
- [ ] Slack workspace access
- [ ] GitHub organization access
- [ ] Development environment setup
- [ ] Password manager setup

### Meet Your Team
- [ ] Schedule 1:1 with your manager
- [ ] Meet your onboarding buddy
- [ ] Team introduction session
- [ ] Department overview meeting

## Phase 2: Learning and Training (Weeks 2-3)

### Technical Training
- [ ] Company coding standards
- [ ] Development workflow
- [ ] Testing procedures
- [ ] Deployment processes
- [ ] Security best practices

### Company Culture
- [ ] Mission and values training
- [ ] Company history and structure
- [ ] Communication guidelines
- [ ] Performance expectations

## Phase 3: Integration (Week 4+)

### Project Involvement
- [ ] Review current projects
- [ ] Assign first tasks/tickets
- [ ] Set up development environment
- [ ] Make first contribution
- [ ] Code review process

### Ongoing Development
- [ ] Set 30-60-90 day goals
- [ ] Schedule regular check-ins
- [ ] Join relevant working groups
- [ ] Begin mentoring relationships

## Resources and Contacts

### Key People
- **Manager**: [Manager Name]
- **Onboarding Buddy**: [Buddy Name]
- **HR Contact**: [HR Contact]
- **IT Support**: [IT Contact]

### Important Links
- Company Handbook
- Engineering Wiki
- Code Style Guide
- Slack Channels Directory

---
*Last updated: {datetime.now().strftime('%Y-%m-%d')}*
"""
            
            repo.create_file(
                "ONBOARDING.md",
                "Detailed onboarding guide",
                onboarding_content
            )
            
            # FIRST_WEEK.md
            first_week_content = f"""# First Week Checklist - {employee_name}

## Day 1: Welcome and Setup
- [ ] Arrive at office/join virtual welcome
- [ ] Office tour (if in-person)
- [ ] Meet your manager
- [ ] Get workspace setup
- [ ] Receive equipment and access credentials
- [ ] Complete initial HR requirements
- [ ] Join company Slack and introduce yourself

## Day 2: System Access and Tools
- [ ] Set up development environment
- [ ] Install required software and tools
- [ ] Test VPN and remote access
- [ ] Access company systems (email, calendar, etc.)
- [ ] Complete security training
- [ ] Set up password manager

## Day 3: Team Integration
- [ ] Meet with onboarding buddy
- [ ] Team introductions and role explanations
- [ ] Review team processes and workflows
- [ ] Join relevant Slack channels and mailing lists
- [ ] Schedule upcoming meetings and training sessions

## Day 4: Project Orientation
- [ ] Review current team projects
- [ ] Understand codebase structure
- [ ] Set up local development environment
- [ ] Review documentation and wikis
- [ ] Identify first tasks or learning objectives

## Day 5: Check-in and Planning  
- [ ] First week retrospective with manager
- [ ] Address any blockers or concerns
- [ ] Plan week 2 objectives
- [ ] Schedule ongoing 1:1s
- [ ] Update onboarding progress

## End of Week Goals
By the end of your first week, you should:
- Have all necessary access and tools
- Understand your role and initial expectations
- Know who to contact for different types of help
- Feel comfortable with basic company processes
- Have a clear plan for week 2

## Notes Section
Use this space to jot down important information, questions, or observations:

---

**Completed on**: ___________
**Manager Sign-off**: ___________
"""
            
            repo.create_file(
                "FIRST_WEEK.md",
                "First week detailed checklist",
                first_week_content
            )
            
            # RESOURCES.md
            resources_content = f"""# Resources for {employee_name}

## 📚 Learning Resources

### Company Documentation
- [ ] Employee Handbook
- [ ] Engineering Documentation
- [ ] API Documentation
- [ ] Style Guides
- [ ] Architecture Overview

### Training Materials
- [ ] Security Training (Required)
- [ ] Compliance Training (Required)
- [ ] Product Training
- [ ] Technical Stack Training
- [ ] Soft Skills Development

## 🔧 Tools and Systems

### Development Tools
- **IDE/Editor**: [Recommended setup]
- **Version Control**: GitHub
- **Communication**: Slack
- **Project Management**: [Tool name]
- **CI/CD**: [Pipeline tools]

### Access Required
- [ ] GitHub Organization
- [ ] Cloud Platform Access
- [ ] Database Access (if needed)
- [ ] Monitoring Tools
- [ ] Deployment Tools

## 👥 Key Contacts

### Immediate Team
| Role | Name | Slack | Email | Notes |
|------|------|--------|-------|--------|
| Manager | [Name] | @username | email | Direct supervisor |
| Buddy | [Name] | @username | email | Onboarding helper |
| Tech Lead | [Name] | @username | email | Technical guidance |

### Support Teams
| Team | Contact | Purpose |
|------|---------|---------|
| IT Support | #it-support | Technical issues |
| HR | #hr-help | HR questions |
| Security | #security | Security concerns |
| Facilities | #facilities | Office/equipment |

## 🎯 Goals and Expectations

### 30 Days
- Complete all required training
- Understand team processes
- Make first meaningful contribution
- Build relationships with team

### 60 Days  
- Contribute regularly to projects
- Understand broader system architecture
- Take ownership of specific areas
- Mentor newer team members

### 90 Days
- Fully productive team member
- Contributing to planning and decisions
- Identifying improvement opportunities
- Leading small initiatives

## 📞 Who to Contact For...

- **Technical Questions**: Tech Lead or Buddy
- **Process Questions**: Manager or Buddy  
- **HR/Benefits**: HR Team
- **Equipment Issues**: IT Support
- **Access Problems**: IT Support or Manager
- **General Questions**: Buddy or Manager

## 📅 Important Dates

- **End of Probation**: [Date]
- **First Performance Review**: [Date]
- **Team Events**: [Upcoming events]
- **Training Deadlines**: [Any required deadlines]

---
*Keep this document updated as you discover new resources!*
"""
            
            repo.create_file(
                "RESOURCES.md",
                "Comprehensive resource guide",
                resources_content
            )
            
        except GithubException as e:
            logger.error(f"Error creating onboarding files: {e}")
            raise
    
    async def _create_onboarding_issues(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create standard onboarding issues."""
        try:
            repo_name = parameters.get("repository")
            employee_name = parameters.get("employee_name", "New Employee")
            job_title = parameters.get("job_title", "Team Member")
            assignee = parameters.get("assignee")
            
            if not repo_name:
                return ToolExecutionResult(
                    success=False,
                    error="Repository name is required"
                )
            
            # Standard onboarding issues
            issues_to_create = [
                {
                    "title": "🏁 Day 1: Welcome and Initial Setup",
                    "body": f"""Welcome to the team, {employee_name}! 🎉

This issue tracks your Day 1 onboarding tasks:

## Tasks to Complete:
- [ ] Office tour and workspace setup
- [ ] Meet with manager
- [ ] Complete initial HR paperwork
- [ ] Receive equipment and credentials
- [ ] Join company Slack and introduce yourself
- [ ] Review the onboarding repository

## Success Criteria:
- All access credentials working
- Workspace set up and comfortable
- Connected with team on Slack
- Clear understanding of first week plan

**Due**: End of Day 1
**Priority**: High""",
                    "labels": ["onboarding", "day-1", "high-priority"]
                },
                {
                    "title": "💻 Week 1: Development Environment Setup",
                    "body": f"""Set up your development environment for {job_title} role.

## Tasks:
- [ ] Install required software and tools
- [ ] Clone necessary repositories
- [ ] Set up local development environment
- [ ] Test build and deployment processes
- [ ] Configure IDE/editor preferences
- [ ] Set up debugging tools

## Resources:
- Development setup guide: [Link]
- Required tools list: [Link]
- Team coding standards: [Link]

**Due**: End of Week 1""",
                    "labels": ["onboarding", "setup", "development"]
                },
                {
                    "title": "👥 Week 1-2: Team Integration",
                    "body": f"""Get to know your team and understand our processes.

## Meeting Schedule:
- [ ] 1:1 with manager
- [ ] Meet onboarding buddy
- [ ] Team introduction session
- [ ] Department overview
- [ ] Coffee chats with key stakeholders

## Learning Objectives:
- [ ] Understand team structure and roles
- [ ] Learn communication channels and etiquette
- [ ] Review current projects and priorities
- [ ] Understand team workflows

**Due**: End of Week 2""",
                    "labels": ["onboarding", "team", "meetings"]
                },
                {
                    "title": "📚 Weeks 2-3: Training and Documentation",
                    "body": f"""Complete required training and familiarize yourself with company processes.

## Required Training:
- [ ] Security training (mandatory)
- [ ] Compliance training (mandatory)
- [ ] Company culture and values
- [ ] Product overview
- [ ] Technical architecture overview

## Documentation Review:
- [ ] Employee handbook
- [ ] Engineering guidelines
- [ ] API documentation
- [ ] Code style guides
- [ ] Deployment procedures

**Due**: End of Week 3""",
                    "labels": ["onboarding", "training", "documentation"]
                },
                {
                    "title": "🚀 Week 4: First Contribution",
                    "body": f"""Make your first meaningful contribution to the team.

## Milestone Goals:
- [ ] Identify first task/project
- [ ] Review and understand codebase area
- [ ] Implement solution
- [ ] Write tests
- [ ] Submit pull request
- [ ] Address code review feedback
- [ ] Merge first contribution

## Success Criteria:
- Code follows team standards
- Proper tests included
- Documentation updated
- Positive code review
- Successfully deployed

**Due**: End of Week 4""",
                    "labels": ["onboarding", "first-contribution", "milestone"]
                },
                {
                    "title": "📊 30-Day Check-in and Goal Setting",
                    "body": f"""30-day onboarding review and planning.

## Review Topics:
- [ ] Progress assessment
- [ ] Feedback on onboarding experience
- [ ] Address any concerns or blockers
- [ ] Identify areas for additional support
- [ ] Celebrate achievements

## Goal Setting:
- [ ] Set 60-day objectives
- [ ] Identify growth areas
- [ ] Plan training/development activities
- [ ] Discuss career progression
- [ ] Schedule regular check-ins

**Due**: Day 30""",
                    "labels": ["onboarding", "review", "planning"]
                }
            ]
            
            created_issues = []
            
            for issue_data in issues_to_create:
                issue_params = {
                    "repository": repo_name,
                    "title": issue_data["title"],
                    "body": issue_data["body"],
                    "labels": issue_data.get("labels", [])
                }
                
                if assignee:
                    issue_params["assignees"] = [assignee]
                
                result = await self._create_issue(issue_params)
                if result.success:
                    created_issues.append(result.data)
            
            return ToolExecutionResult(
                success=True,
                data={
                    "issues_created": created_issues,
                    "total_count": len(created_issues),
                    "repository": repo_name,
                    "assignee": assignee
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating onboarding issues: {str(e)}"
            )
    
    async def _create_project_board(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a project board for tracking onboarding progress."""
        try:
            repo_name = parameters.get("repository")
            name = parameters.get("name", "Onboarding Progress")
            description = parameters.get("description", "Track onboarding tasks and milestones")
            
            if not repo_name:
                return ToolExecutionResult(
                    success=False,
                    error="Repository name is required"
                )
            
            repo = self.client.get_repo(repo_name)
            
            # Create project
            project = repo.create_project(
                name=name,
                body=description
            )
            
            # Create columns
            columns = [
                {"name": "📋 To Do", "preset": None},
                {"name": "🔄 In Progress", "preset": None},
                {"name": "👀 Review", "preset": None},
                {"name": "✅ Done", "preset": None}
            ]
            
            created_columns = []
            for col_data in columns:
                column = project.create_column(col_data["name"])
                created_columns.append({
                    "id": column.id,
                    "name": column.name,
                    "url": column.url
                })
            
            return ToolExecutionResult(
                success=True,
                data={
                    "project_id": project.id,
                    "name": project.name,
                    "url": project.html_url,
                    "columns": created_columns,
                    "repository": repo_name
                }
            )
            
        except GithubException as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating project board: {str(e)}"
            )
    
    async def _create_branch(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a new branch in a repository."""
        try:
            repo_name = parameters.get("repository")
            branch_name = parameters.get("branch_name")
            source_branch = parameters.get("source_branch", "main")
            
            if not repo_name or not branch_name:
                return ToolExecutionResult(
                    success=False,
                    error="Repository name and branch name are required"
                )
            
            repo = self.client.get_repo(repo_name)
            source_branch_obj = repo.get_branch(source_branch)
            
            repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source_branch_obj.commit.sha
            )
            
            return ToolExecutionResult(
                success=True,
                data={
                    "repository": repo_name,
                    "branch_name": branch_name,
                    "source_branch": source_branch,
                    "message": f"Branch '{branch_name}' created successfully"
                }
            )
            
        except GithubException as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating branch: {str(e)}"
            )
    
    async def _create_pull_request(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Create a pull request."""
        try:
            repo_name = parameters.get("repository")
            title = parameters.get("title")
            body = parameters.get("body", "")
            head = parameters.get("head")  # source branch
            base = parameters.get("base", "main")  # target branch
            draft = parameters.get("draft", False)
            
            if not repo_name or not title or not head:
                return ToolExecutionResult(
                    success=False,
                    error="Repository name, title, and head branch are required"
                )
            
            repo = self.client.get_repo(repo_name)
            
            pr = repo.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
                draft=draft
            )
            
            return ToolExecutionResult(
                success=True,
                data={
                    "pr_id": pr.id,
                    "pr_number": pr.number,
                    "title": pr.title,
                    "url": pr.html_url,
                    "state": pr.state,
                    "head": pr.head.ref,
                    "base": pr.base.ref,
                    "draft": pr.draft,
                    "created_at": pr.created_at.isoformat()
                }
            )
            
        except GithubException as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error creating pull request: {str(e)}"
            )
    
    async def _list_repositories(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """List repositories for the authenticated user or organization."""
        try:
            repo_type = parameters.get("type", "all")  # all, owner, member
            sort = parameters.get("sort", "updated")
            direction = parameters.get("direction", "desc")
            per_page = parameters.get("per_page", 30)
            
            repos = self.user.get_repos(
                type=repo_type,
                sort=sort,
                direction=direction
            )
            
            repository_list = []
            count = 0
            
            for repo in repos:
                if count >= per_page:
                    break
                
                repository_list.append({
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "url": repo.html_url,
                    "description": repo.description,
                    "private": repo.private,
                    "language": repo.language,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "updated_at": repo.updated_at.isoformat()
                })
                count += 1
            
            return ToolExecutionResult(
                success=True,
                data={
                    "repositories": repository_list,
                    "total_count": len(repository_list),
                    "filter_type": repo_type
                }
            )
            
        except GithubException as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error listing repositories: {str(e)}"
            )
    
    async def _get_repository_info(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Get detailed information about a repository."""
        try:
            repo_name = parameters.get("repository")
            
            if not repo_name:
                return ToolExecutionResult(
                    success=False,
                    error="Repository name is required"
                )
            
            repo = self.client.get_repo(repo_name)
            
            return ToolExecutionResult(
                success=True,
                data={
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "private": repo.private,
                    "language": repo.language,
                    "size": repo.size,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "open_issues": repo.open_issues_count,
                    "default_branch": repo.default_branch,
                    "created_at": repo.created_at.isoformat(),
                    "updated_at": repo.updated_at.isoformat(),
                    "topics": repo.get_topics()
                }
            )
            
        except GithubException as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error getting repository info: {str(e)}"
            )
    
    async def _assign_mentor(self, parameters: Dict[str, Any]) -> ToolExecutionResult:
        """Assign a mentor by adding them as a collaborator and creating mentor issue."""
        try:
            repo_name = parameters.get("repository")
            mentor_username = parameters.get("mentor_username")
            employee_name = parameters.get("employee_name")
            
            if not repo_name or not mentor_username or not employee_name:
                return ToolExecutionResult(
                    success=False,
                    error="Repository name, mentor username, and employee name are required"
                )
            
            # Add mentor as collaborator
            collab_result = await self._add_collaborator({
                "repository": repo_name,
                "username": mentor_username,
                "permission": "admin"
            })
            
            # Create mentor guidance issue
            mentor_issue = await self._create_issue({
                "repository": repo_name,
                "title": f"🤝 Mentor Guidance for {employee_name}",
                "body": f"""Hi @{mentor_username}! 👋

You've been assigned as the mentor for {employee_name}'s onboarding. Here's how you can help:

## Mentor Responsibilities:
- [ ] Introduce yourself and schedule initial meeting
- [ ] Review onboarding progress weekly
- [ ] Answer questions and provide guidance
- [ ] Help with technical challenges
- [ ] Provide feedback on work and code reviews
- [ ] Check in regularly during first 30 days

## Key Milestones to Support:
- [ ] Week 1: Initial setup and orientation
- [ ] Week 2-3: Training and documentation review  
- [ ] Week 4: First contribution
- [ ] Day 30: Progress review and goal setting

## Resources:
- Employee's onboarding repository: {repo_name}
- Mentor guidelines: [Link to mentor guide]
- Escalation contacts: [Manager info]

Thanks for helping {employee_name} succeed! 🚀""",
                "assignees": [mentor_username],
                "labels": ["mentoring", "onboarding"]
            })
            
            return ToolExecutionResult(
                success=True,
                data={
                    "mentor_username": mentor_username,
                    "employee_name": employee_name,
                    "repository": repo_name,
                    "collaborator_added": collab_result.success,
                    "mentor_issue": mentor_issue.data if mentor_issue.success else None,
                    "message": f"Successfully assigned {mentor_username} as mentor for {employee_name}"
                }
            )
            
        except Exception as e:
            return ToolExecutionResult(
                success=False,
                error=f"Error assigning mentor: {str(e)}"
            )
    
    def is_available(self) -> bool:
        """Check if the GitHub tool is available."""
        return self.client is not None and self.user is not None
    
    def get_available_actions(self) -> List[str]:
        """Get list of available actions."""
        return [
            "create_repository",
            "add_collaborator",
            "create_issue",
            "create_project_board",
            "setup_onboarding_repo",
            "create_branch",
            "create_pull_request",
            "list_repositories",
            "get_repository_info",
            "create_onboarding_issues",
            "assign_mentor"
        ]