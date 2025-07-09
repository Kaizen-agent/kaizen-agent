import os
from pathlib import Path
from kaizen.autofix.test.code_region import (
    CodeRegionExecutor, 
    CodeRegionExtractor,
    RegionInfo, 
    AgentEntryPoint, 
    RegionType
)

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

def test_email_agent_runner():
    """Test running the provided EmailAgent code using the code runner."""
    print("🧪 Testing EmailAgent runner integration...")
    test_dir = Path("test_email_agent")
    test_dir.mkdir(exist_ok=True)
    agent_path = test_dir / "email_agent.py"
    agent_code = '''
from llama_index.core.agent import ReActAgent
from llama_index.llms.gemini import Gemini
from llama_index.core.tools.function_tool import FunctionTool
from typing import Dict, Any
import os
from dotenv import load_dotenv

class EmailAgent:
    """An agent for improving email drafts using AI."""
    
    def __init__(self, api_key: str = None):
        load_dotenv()
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable or pass it to the constructor.")
        self.llm = Gemini(model="models/gemini-2.0-flash-lite", temperature=0.1)
        self.agent = self._create_agent()
    def _improve_email_with_llm(self, email_draft: str) -> str:
        prompt = f"""
        Please improve the following email draft to make it more professional, clear, and effective. 
        Maintain the original intent and tone while enhancing clarity, grammar, and professionalism.
        
        Original email: \"{email_draft}\"
        
        Improved version:
        """
        try:
            response = self.llm.complete(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error using LLM: {e}. Original email: {email_draft}"
    def _create_agent(self) -> ReActAgent:
        def improve_email_wrapper(email_draft: str) -> str:
            return self._improve_email_with_llm(email_draft)
        email_tool = FunctionTool.from_defaults(
            fn=improve_email_wrapper,
            name="improve_email",
            description="Improve an email draft by making it more professional, clear, and effective using AI"
        )
        agent = ReActAgent.from_tools(
            tools=[email_tool],
            llm=self.llm,
            verbose=True
        )
        return agent
    def improve_email(self, email_draft: str) -> str:
        if not email_draft or not email_draft.strip():
            raise ValueError("Email draft cannot be empty")
        try:
            response = self.agent.chat(
                f"Please use the improve_email tool to enhance this email draft: '{email_draft}'. "
                "Make it more professional and well-formatted."
            )
            return response.response
        except Exception as e:
            raise RuntimeError(f"Failed to improve email: {e}")
'''
    write_file(agent_path, agent_code)
    
    extractor = CodeRegionExtractor(test_dir)
    entry_point = AgentEntryPoint(
        module="email_agent",
        class_name="EmailAgent",
        method="improve_email"
    )
    region_info = extractor.extract_region_by_entry_point(agent_path, entry_point)
    executor = CodeRegionExecutor(test_dir)
    
    
    try:
        result = executor.execute_region_with_tracking(
            region_info,
            input_data=["This is a test email draft."],
            tracked_variables=set(),
            framework="llamaindex"
        )
        print(f"   Execution result: {result['result']}")
        assert isinstance(result['result'], str), "Result should be a string (mocked or real)"
        print("✅ EmailAgent runner test passed!")
    except Exception as e:
        print(f"❌ EmailAgent runner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            agent_path.unlink()
            test_dir.rmdir()
        except Exception:
            pass
    return True

def main():
    print("🚀 Starting EmailAgent runner test...")
    print("=" * 60)
    success = test_email_agent_runner()
    print("\nResult:")
    if success:
        print("✅ PASS EmailAgent runner integration")
    else:
        print("❌ FAIL EmailAgent runner integration")
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main()) 