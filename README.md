# AI Agent System

A self-hosted autonomous AI agent that discovers internships using LLM orchestration, browser automation, and persistent database storage.

![AI Agent Demo](https://img.shields.io/badge/Status-Production%20Ready-brightgreen) ![Python](https://img.shields.io/badge/Python-3.10+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green) ![SQLite](https://img.shields.io/badge/Database-SQLite-blue)

## 🚀 Overview

This system combines multiple cutting-edge technologies to create an autonomous job discovery and management platform:

- **Autonomous Goal Execution**: Takes natural language instructions and breaks them into executable steps
- **Browser Automation**: Uses Playwright to visit websites and extract comprehensive job data
- **Database Integration**: SQLite storage with full CRUD operations and application tracking
- **Professional Web Interface**: Dark-themed dashboard for managing discovered opportunities
- **Self-Hosted**: Runs entirely on local infrastructure with no cloud dependencies

## 🏗️ Architecture
```
User Input → FastAPI Server → Background Worker → Agent Loop
                                                      ↓
                                               LLM Decision Engine (Ollama)
                                                      ↓
                                    ┌─────────────────────────────────┐
                                    │  Tool Orchestration Layer      │
                                    │  ├── Web Search (Tavily API)   │
                                    │  ├── Browser Automation        │
                                    │  ├── Database Operations       │
                                    │  ├── Email Notifications       │
                                    │  └── File System Operations    │
                                    └─────────────────────────────────┘
                                                      ↓
                                    ┌─────────────────────────────────┐
                                    │  Persistent Storage & UI       │
                                    │  ├── SQLite Database           │
                                    │  ├── Web Dashboard (CRUD)      │
                                    │  └── Email Reports             │
                                    └─────────────────────────────────┘
```

## 🛠️ Technology Stack

### Core Infrastructure
- **Python 3.10+**: Primary development language
- **FastAPI**: High-performance REST API framework
- **Ollama**: Local LLM inference engine (Llama 3.1 8B)
- **SQLAlchemy**: Database ORM and management
- **SQLite**: Lightweight, embedded database

### AI & Automation
- **LLM Orchestration**: Autonomous goal decomposition and tool selection
- **Playwright**: Headless browser automation for web scraping
- **Tavily API**: Intelligent web search integration
- **Tool Calling**: Dynamic function execution based on LLM decisions

### User Interface
- **Modern Web Dashboard**: Dark theme, responsive design
- **Real-time Updates**: Live statistics and data refresh
- **CRUD Operations**: Complete internship management workflow
- **Search & Filtering**: Advanced data discovery capabilities

## ⚡ Quick Start

### Prerequisites
- Python 3.10 or higher
- Linux environment (tested on Ubuntu/Mint)
- 8GB+ RAM recommended for local LLM

### Installation

1. **Clone the repository**
```bash
   git clone https://github.com/abelprasad/scout.git
   cd scout
```

2. **Set up Python environment**
```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
```

3. **Install browser automation**
```bash
   playwright install
```

4. **Install and configure Ollama**
```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama pull llama3.1:8b
```

5. **Configure environment variables**
```bash
   cp .env.example .env
   # Edit .env with your API keys and email credentials
```

### Configuration

Create a `.env` file with your credentials:
```env
# Web Search API
TAVILY_API_KEY=tvly-your-api-key-here

# Email Configuration (Gmail)
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-16-char-app-password
EMAIL_RECIPIENT=your-email@gmail.com
```

### Running the System

**Start both servers simultaneously:**
```bash
./start_system.sh
```

**Or start individually:**
```bash
# Terminal 1: AI Agent API
python main.py

# Terminal 2: Web Dashboard
python web_dashboard.py
```

## 📱 Usage

### API Endpoints

**Submit a new job:**
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"goal": "Find 5 software engineering internships and save to database"}'
```

**Check job status:**
```bash
curl http://localhost:8000/jobs/{job_id}
```

### Web Dashboard

Access the management interface at `http://localhost:8001`

Features:
- **Statistics Dashboard**: Real-time metrics on discovered opportunities
- **Search & Filter**: Find specific internships by company, title, or keywords  
- **Application Tracking**: Mark positions as applied, interviewing, or offered
- **CRUD Operations**: Create, edit, and delete internship records
- **Responsive Design**: Works on desktop and mobile devices

## 🎯 Example Workflows

### Autonomous Internship Discovery
```json
{
  "goal": "Find 10 marine biology internships, visit their websites for detailed requirements, save everything to database, and email me a summary"
}
```

**The agent will:**
1. Search for relevant opportunities using web search
2. Visit each job posting website to extract full details
3. Save all findings to the persistent database
4. Send a comprehensive email report
5. Make data available in the web dashboard

### Application Management
- Use the web dashboard to track application status
- Add notes and interview feedback
- Filter by application status or company
- Export data for external use

### Scheduled Monitoring
- Set up cron jobs to run daily searches
- Automatically discover new postings
- Get email notifications for new opportunities

## 🔧 Development

### Project Structure
```
scout/
├── agent.py              # Core agent orchestration logic
├── main.py               # FastAPI server and job management
├── database.py           # Database schema and utilities
├── web_dashboard.py      # CRUD web interface
├── tools/               # Tool implementations
│   ├── websearch.py     # Web search integration
│   ├── browser.py       # Playwright automation
│   ├── email.py         # Email notifications
│   ├── database.py      # Database operations
│   └── filesystem.py    # File system operations
└── output/              # Generated files and reports
```

### Adding New Tools

Implement the `BaseTool` interface:
```python
from tools.base import BaseTool

class CustomTool(BaseTool):
    name = "custom_action"
    description = "Description for the LLM to understand when to use this tool"
    
    def execute(self, **kwargs):
        # Tool implementation
        return {
            "success": True,
            "data": "Tool result"
        }
```

Register in `main.py`:
```python
tools = [
    WebSearchTool(),
    BrowserTool(),
    EmailTool(),
    DatabaseTool(),
    CustomTool()  # Add your new tool
]
```

## 📊 Features

### AI Agent Capabilities
- **Natural Language Processing**: Understands complex, multi-step goals
- **Autonomous Planning**: Breaks down objectives into executable tasks
- **Tool Selection**: Intelligently chooses appropriate tools for each step
- **Error Recovery**: Handles failures and retries with alternative approaches
- **Context Awareness**: Maintains conversation state across tool executions

### Browser Automation
- **Headless Operation**: Runs without GUI requirements
- **Anti-Detection**: Realistic user-agent strings and behavior patterns
- **Content Extraction**: Intelligent parsing of job posting structures
- **Screenshot Capture**: Visual documentation of discovered content
- **Form Interaction**: Capability for future auto-application features

### Database Management
- **Duplicate Prevention**: URL-based deduplication of job postings
- **Rich Metadata**: Company, location, requirements, deadlines
- **Application Tracking**: Full lifecycle from discovery to offer
- **Search Indexing**: Fast full-text search across all fields
- **Data Export**: JSON and CSV export capabilities

## 🚀 Deployment

### Local Development
The system is designed to run on a local development machine or self-hosted server.

### Production Considerations
- **Process Management**: Use systemd or supervisor for production deployment
- **Database**: Consider PostgreSQL for multi-user scenarios
- **Reverse Proxy**: Nginx configuration for public access
- **Security**: Environment variable management and API key rotation
- **Monitoring**: Logging and alerting for autonomous operations

## 🤝 Contributing

This is a portfolio project demonstrating AI agent architecture, full-stack development, and automation capabilities. The codebase showcases:

- Modern Python development practices
- API design and documentation
- Database modeling and ORM usage  
- Frontend development with vanilla JavaScript
- AI/ML integration and prompt engineering
- Systems programming and deployment

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🎯 Results

This system has successfully:
- Discovered 100+ internship opportunities across multiple domains
- Automated the tedious process of job board monitoring  
- Created a centralized application tracking workflow
- Demonstrated practical applications of AI agent technology
- Showcased full-stack development capabilities

**Built for Summer 2026 internship search - helping to systematically discover and manage opportunities in the competitive tech hiring market.**

