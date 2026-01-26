import ollama
import json

class Agent:
    def __init__(self, tools):
        self.tools = {tool.name: tool for tool in tools}
        self.conversation_history = []
        self.verbose = True
    
    def run(self, goal, job_id=None):
        """Main agent loop - keeps running until goal is complete"""

        """Main agent loop - keeps running until goal is complete"""
        
        # Build tool descriptions for the LLM
        tool_descriptions = "\n".join([
            f"- {name}: {tool.description}" 
            for name, tool in self.tools.items()
        ])
        
        # Initialize conversation with system prompt
        self.conversation_history = [
            {
                "role": "system",
                "content": f"""You are an autonomous agent. Your ONLY job is to complete the user's goal using the available tools.

Available tools:
{tool_descriptions}

RESPONSE FORMAT - Use ONLY these JSON formats:

To use a tool:
{{"tool": "tool_name", "args": {{"key": "value"}}}}

When completely done:
{{"done": true, "summary": "what you accomplished"}}

IMPORTANT: If the goal asks you to EMAIL results, you MUST use the send_email tool. Do not just save to file.
"""
            },
            {
                "role": "user",
                "content": f"Goal: {goal}"
            }
        ]
        
        max_iterations = 15
        
        for iteration in range(max_iterations):
            print(f"\n{'='*60}")
            print(f"Iteration {iteration + 1}/{max_iterations}")
            print(f"{'='*60}")
            
            # Get next action from LLM
            response = ollama.chat(
                model='llama3.1:8b',
                messages=self.conversation_history,
                format='json',
                options={
                    'temperature': 0.1
                }
            )
            
            response_content = response['message']['content']
            
            if self.verbose:
                print(f"[Agent] LLM response: {response_content[:200]}...")
            
            try:
                action = json.loads(response_content)
            except json.JSONDecodeError as e:
                print(f"[Agent] Failed to parse JSON: {e}")
                print(f"[Agent] Raw response: {response_content}")
                return f"Agent error: Invalid JSON response from LLM"
            
            # Check if agent says it's done
            if action.get('done'):
                summary = action.get('summary', 'Task completed')
                print(f"\n[Agent] ✓ Complete: {summary}")
                return summary
            
            # Execute the tool
            tool_name = action.get('tool')
            tool_args = action.get('args', {})
            
            if not tool_name:
                print("[Agent] No tool specified in response")
                # Add guidance to conversation
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_content
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": f"Error: You must specify a tool to use. Available tools: {list(self.tools.keys())}. Use format: {{\"tool\": \"tool_name\", \"args\": {{...}}}}"
                })
                continue
            
            if tool_name not in self.tools:
                error_msg = f"Unknown tool: {tool_name}"
                print(f"[Agent] {error_msg}")
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response_content
                })
                self.conversation_history.append({
                    "role": "user",
                    "content": f"Error: {error_msg}. Available tools: {list(self.tools.keys())}"
                })
                continue
            
            print(f"[Agent] Executing {tool_name} with args: {tool_args}")
            
            # Execute the tool
            result = self.tools[tool_name].execute(**tool_args)
            
            print(f"[Agent] Tool result: {result}")
            
            # Add to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_content
            })
            self.conversation_history.append({
                "role": "user",
                "content": f"Tool execution result: {json.dumps(result)}"
            })
        
        return "Max iterations reached without completing goal"
