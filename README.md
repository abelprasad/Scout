# AI Agent System

Self-hosted autonomous AI agent that searches for internships and emails detailed results using LLM orchestration and browser automation.

## 🚀 Features

- **Autonomous Goal Execution**: Takes natural language goals and breaks them into executable steps
- **Browser Automation**: Uses Playwright to visit websites and extract full content (not just search snippets)
- **Multi-Tool Orchestration**: Web search, file system, email, and browser tools
- **Self-Hosted**: Runs on local infrastructure with no cloud dependencies
- **RESTful API**: Submit jobs and check status via HTTP endpoints

## 🏗️ Architecture
```
User Goal → FastAPI → Background Worker → Agent Loop
                                           ↓
                                    LLM Decision Engine
                                           ↓
                            [WebSearch] [Browser] [Email] [FileSystem]
                                           ↓
                                     Results & Notifications
```

## 🛠️ Tech Stack

- **Python**: Core agent logic and API
- **FastAPI**: RESTful API server
- **Ollama**: Local LLM inference (Llama 3.1)
- **Playwright**: Headless browser automation
- **Tavily API**: Web search integration
- **Gmail SMTP**: Email notifications

## 📦 Installation
```bash
git clone https://github.com/abelprasad/ai-agent.git
cd ai-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install
```

## 🔑 Configuration

Create `.env` file:
```env
TAVILY_API_KEY=your_tavily_key
EMAIL_SENDER=your@email.com
EMAIL_PASSWORD=your_app_password
EMAIL_RECIPIENT=your@email.com
```

## 🚀 Usage

Start the agent:
```bash
python main.py
```

Submit a job:
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"goal": "Find NASA internships, visit their website, and email me details"}'
```

## 💡 Example Workflows

**Internship Search**: Searches job boards, visits company websites, extracts full job descriptions
**Research Tasks**: Gathers information from multiple sources and compiles reports
**Monitoring**: Checks websites for updates and sends notifications

## 🎯 Future Enhancements

- Form filling automation for job applications
- Database persistence for job tracking
- Web dashboard for job management
- Advanced filtering and ranking

## 📄 License

MIT License - see LICENSE file for details
