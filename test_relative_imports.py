import os
from pathlib import Path
from kaizen.autofix.test.code_region import CodeRegionExecutor, RegionInfo, AgentEntryPoint, RegionType

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

def test_relative_imports():
    # Create package structure
    package_dir = Path("test_package")
    package_dir.mkdir(exist_ok=True)
    
    # Create __init__.py for the package
    init_path = package_dir / "__init__.py"
    write_file(init_path, "# Package init file\n")
    
    # Create utils.py in the package
    utils_path = package_dir / "utils.py"
    utils_code = '''
def helper(x):
    return x * 2
'''
    write_file(utils_path, utils_code)
    
    # Create agent.py with relative import
    agent_path = package_dir / "agent.py"
    agent_code = '''
from . import utils

class MyAgent:
    def run(self, x):
        return utils.helper(x)
'''
    write_file(agent_path, agent_code)
    
    # Prepare region info
    region_info = RegionInfo(
        type=RegionType.MODULE,
        name="agent",
        code=agent_code,
        start_line=1,
        end_line=1,
        imports=[],
        dependencies=frozenset(),
        file_path=agent_path,
        entry_point=AgentEntryPoint(
            module="agent",
            class_name="MyAgent",
            method="run"
        )
    )
    
    # Test with package directory as workspace root
    executor = CodeRegionExecutor(package_dir)
    
    try:
        result = executor._execute_llamaindex_agent(region_info, [21], set())
        print("Result:", result['result'])
        assert result['result'] == 42, f"Expected 42, got {result['result']}"
        print("✅ Relative import test passed!")
    except Exception as e:
        print(f"❌ Relative import test failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    try:
        agent_path.unlink()
        utils_path.unlink()
        init_path.unlink()
        package_dir.rmdir()
    except Exception:
        pass

if __name__ == "__main__":
    test_relative_imports() 