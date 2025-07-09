import os
from pathlib import Path
from kaizen.autofix.test.code_region import CodeRegionExecutor, RegionInfo, AgentEntryPoint, RegionType

def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

def test_llamaindex_agent_with_utils():
    test_dir = Path("test_agent_with_utils")
    test_dir.mkdir(exist_ok=True)
    agent_path = test_dir / "agent.py"
    utils_path = test_dir / "utils.py"

    # Write utils.py
    utils_code = '''
def helper(x):
    return x * 2
'''
    write_file(utils_path, utils_code)

    # Write agent.py
    agent_code = '''
import utils

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

    executor = CodeRegionExecutor(test_dir)
    result = executor._execute_llamaindex_agent(region_info, [21], set())
    print("Result:", result['result'])
    assert result['result'] == 42, f"Expected 42, got {result['result']}"
    print("✅ Test passed!")

    # Cleanup
    try:
        agent_path.unlink()
        utils_path.unlink()
        test_dir.rmdir()
    except Exception:
        pass

if __name__ == "__main__":
    test_llamaindex_agent_with_utils() 