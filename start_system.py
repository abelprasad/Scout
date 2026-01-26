import subprocess
import time
import os
from multiprocessing import Process

def start_agent_server():
    """Start the main AI agent server"""
    print("🤖 Starting AI Agent Server on port 8000...")
    subprocess.run(["python", "main.py"])

def start_web_dashboard():
    """Start the web dashboard server"""
    print("🌐 Starting Web Dashboard on port 8001...")
    subprocess.run(["python", "web_dashboard.py"])

def main():
    print("🚀 Starting AI Agent System...")
    print("=" * 50)
    
    # Start both servers as separate processes
    agent_process = Process(target=start_agent_server)
    dashboard_process = Process(target=start_web_dashboard)
    
    try:
        # Start both servers
        agent_process.start()
        time.sleep(2)  # Give agent server time to start
        dashboard_process.start()
        
        print("✅ AI Agent Server: http://localhost:8000")
        print("✅ Web Dashboard: http://localhost:8001")
        print("\nSystem ready for demo! Press Ctrl+C to stop both servers.")
        
        # Keep running until user interrupts
        agent_process.join()
        dashboard_process.join()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down system...")
        agent_process.terminate()
        dashboard_process.terminate()
        agent_process.join()
        dashboard_process.join()
        print("✅ System stopped cleanly")

if __name__ == "__main__":
    main()
