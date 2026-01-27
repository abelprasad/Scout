import os
from .base import BaseTool

class FileSystemTool(BaseTool):
    name = "file_write"
    description = "Write content to a file. Args: {'filename': 'file.txt', 'content': 'text to write'}"
    
    def execute(self, filename, content):
        """Write content to a file"""
        try:
            # Write to ~/ai-agent/output directory
            output_dir = os.path.expanduser("~/ai-agent/output")
            os.makedirs(output_dir, exist_ok=True)
            
            filepath = os.path.join(output_dir, filename)
            
            print(f"[FileSystem] Writing to: {filepath}")
            with open(filepath, 'w') as f:
                f.write(content)
            
            return {
                "success": True,
                "data": f"Successfully wrote to {filepath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

