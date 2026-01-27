class BaseTool:
    """Base class for all tools"""
    name = ""
    description = ""
    
    def execute(self, **kwargs):
        """Execute the tool. Must return dict with 'success' and 'data' or 'error'"""
        raise NotImplementedError
    
    def get_schema(self):
        """Return JSON schema describing this tool's arguments"""
        return {
            "name": self.name,
            "description": self.description
        }
