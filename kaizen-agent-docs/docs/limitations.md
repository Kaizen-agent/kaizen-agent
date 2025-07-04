---
sidebar_position: 6
---

# 🚧 Limitations & Future Plans

Kaizen Agent is evolving rapidly, but it's important to understand what it can and can't do today — and where it's going.

---

## 🧱 Current Limitations

- **Framework support**: Currently works only with:
  - Python agents
  - Mastra (a TypeScript agent framework)
- **Single-agent only**: Kaizen Agent supports testing only one agent at a time.
- **No multi-turn interactions**: It's designed for single-call agent methods, not ongoing conversations.
- **Evaluation is limited to return values**:
  - You must define evaluation targets on the return of a single function.
  - It cannot evaluate intermediate variables or multi-method outputs.
- **Input types supported**:
  - `string`
  - `dict`
  - `object` (with constructor args)
- **No browser or tool-based agent support** (yet)
- **Not suitable for production** environments — it's for development & improvement only

---

## 🚀 Future Plans

We're building toward a general-purpose debugging agent for any LLM application. Planned features include:

- 🔄 **Multi-turn support**: Debug conversational agents that span multiple steps
- 👥 **Multi-agent scenarios**: Handle coordination, failures, and optimization across agents
- 🧠 **Complex workflows**: Support for:
  - Browser agents
  - Tool-using agents
  - Toolformer-style LLMs
- 📦 **Framework compatibility**: Add support for popular frameworks like:
  - LangChain
  - CrewAI
  - Autogen
  - OpenAgents
- 📊 **API comparison testing**: Automatically evaluate which LLM or endpoint performs better
- 🎯 **Production-grade fine-tuning**: Help teams go from 80% to 90%+ accuracy for real-world use cases
- 🛠️ **Project-level automation**: Let Kaizen Agent fix and refactor full agent workflows across files and modules

---

Our long-term vision is to create an **AI development teammate** that accelerates LLM development automatically, so humans can focus on building features — and Kaizen Agent handles everything else to reach production-level reliability.

---

💬 **Want to help?**  
Join our [Discord](https://discord.gg/2A5Genuh) or contribute on [GitHub](https://github.com/Kaizen-agent/kaizen-agent). 