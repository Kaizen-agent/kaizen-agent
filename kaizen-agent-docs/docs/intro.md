---
sidebar_position: 1
---

# Introduction to Kaizen Agent

**The AI Agent That Improves Your LLM App**

Kaizen Agent autonomously tests your app using input and ideal output pairs, detects failures, suggests fixes, and opens PRs — so your LLM gets better with every iteration.

## What is Kaizen Agent?

Kaizen Agent is your AI development teammate that levels up your LLM applications. Instead of manually testing and iterating on your agents, you simply:

1. Define your test inputs and evaluation criteria in YAML
2. Run `kaizen test-all --auto-fix`
3. Let Kaizen automatically test, analyze, and improve your code

Think of Kaizen Agent not as QA, but as a dev teammate that accelerates your development by automating what slows you down.

## Watch Kaizen Agent in Action

<iframe
  src="https://www.loom.com/embed/d3d8a5c344dc4108906d60e5c209962e"
  frameBorder="0"
  webkitallowfullscreen
  mozallowfullscreen
  allowFullScreen
  style={{width: '100%', height: '400px'}}>
</iframe>

**[Watch the full demo video](https://www.loom.com/share/d3d8a5c344dc4108906d60e5c209962e)**

## How It Works

![Kaizen Agent Architecture](https://raw.githubusercontent.com/Kaizen-agent/kaizen-agent/main/kaizen_agent_workflow.png)

Kaizen Agent works by:

1. **Running your AI agent** with various test inputs
2. **Analyzing the results** using AI-powered evaluation
3. **Identifying improvement opportunities** in code, prompts, or logic
4. **Automatically implementing fixes** by improving prompts and code
5. **Re-testing** to ensure improvements work

## When to Use Kaizen Agent

**Kaizen Agent is most valuable when you want to ship reliable LLM features faster.**

### Perfect Timing: Accelerate Your Development Cycle

After writing your agent code, you typically need to:
- **Test with various inputs** to ensure reliability
- **Tweak prompts** for better performance  
- **Handle edge cases** and failure scenarios
- **Optimize code** based on test results

**Kaizen Agent automates this entire process, so you can focus on building features instead of debugging.**

### Ideal Use Cases

- **🚀 Rapid Development**: Test and improve agents during development cycles
- **⚡ Pre-Deployment Validation**: Ensure your agent works reliably before going live
- **🔧 Continuous Improvement**: Continuously enhance prompts and code based on test results
- **🛡️ Quality Assurance**: Maintain high standards as your agent evolves
- **📈 Performance Optimization**: Level up your agent's capabilities systematically

### When NOT to Use

- **Production environments** - Kaizen is for development/testing, not live systems
- **Simple, stable agents** - If your agent is already working perfectly, you might not need it
- **Non-AI applications** - Kaizen is specifically designed for AI agents and LLM applications

## Key Benefits

### 🎯 No Test Code Required
Kaizen Agent uses YAML configuration instead of traditional test files:
- **❌ Traditional approach**: Write test files with `unittest`, `pytest`, or `jest`
- **✅ Kaizen approach**: Define tests in YAML - no test code needed!

### 🤖 AI-Powered Testing
- Automatically generates test cases based on your agent's purpose
- Uses AI to evaluate responses for quality, accuracy, and relevance
- Identifies edge cases you might miss

### 🔧 Automatic Fixes
- Improves prompts based on test failures
- Fixes code issues automatically
- Creates pull requests with improvements

### 📊 Detailed Analytics
- Comprehensive test reports
- Before/after comparisons
- Performance metrics and trends

## Get Started

Ready to accelerate your LLM development? Check out our [Quick Start Guide](./quickstart.md) to get up and running in minutes!

## Community & Support

💬 **Questions? Need help?** Join our [Discord community](https://discord.gg/2A5Genuh) to ask questions, share your experiences, and get support from other developers using Kaizen Agent!

## Open Source

Kaizen Agent is open source and available on GitHub. Check out the [repository](https://github.com/Kaizen-agent/kaizen-agent) for source code, issues, and contributions.

## 🧠 Traditional Software Engineering vs. AI Agent Development

### 🛠 Traditional Software Engineering
- You write deterministic code.
- Then you write test code (e.g., unit tests, integration tests).
- You run the tests to check pass/fail status.
- If a test fails, you debug the logic, fix the code, and re-run the tests.

> 🔁 This is a structured, predictable feedback loop.

---

### 🤖 AI Agent / LLM Application Development
- You build non-deterministic agents using prompts and LLM calls.
- You can't write traditional test code — behavior varies.
- Instead, you:
  1. Prepare a test dataset (inputs + expected outputs)
  2. Manually run the agent
  3. Evaluate the outputs yourself
  4. Tweak the prompt or agent logic
  5. Repeat

> ❌ This is time-consuming and subjective — like debugging a black box.

---

### 🔧 Kaizen Agent: Your AI Development Teammate
Kaizen Agent automates the test-and-improve loop, acting like a reinforcement learning system for AI agents.

- Define test inputs, expected outputs, and evaluation criteria in YAML.
- Kaizen runs your agent and evaluates the result using LLMs.
- If the result fails:
  - It auto-fixes the code or prompt.
  - Re-runs the test until it passes.
- (Optionally) creates a pull request with the improvements.

---

## ✅ Summary Comparison

|                     | Traditional Software  | AI Agent Development       | Kaizen Agent Workflow       |
|---------------------|------------------------|-----------------------------|------------------------------|
| Code Type           | Deterministic logic    | Non-deterministic (prompt-based) | Prompt + code (LLM-driven)     |
| Testing Method      | Unit tests             | Manual test datasets        | YAML-defined + auto-eval     |
| Evaluation          | Pass/Fail              | Subjective human review     | LLM-based criteria scoring   |
| Feedback Loop       | Manual fix + re-run    | Manual tweak + re-run       | Auto-fix + auto-retry        |
| Automation Level    | High                   | Low                         | Very High                    |

---

**_Diagram: Testing Workflows — Traditional vs AI Agents vs Kaizen Agent_**
(Insert visual diagram here)
