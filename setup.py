import setuptools

setuptools.setup(
    name="kaizen-agent",
    version="0.1.9",
    author="Yuto Suzuki",
    author_email="mokkumokku99@gmail.com",
    description="An AI debugging engineer that continuously tests, analyzes, and improves your AI agents and LLM applications",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",    
    python_requires=">=3.8",
    packages=setuptools.find_packages(include=["kaizen", "kaizen.*"]),
    install_requires=[
        "click>=8.0.0",
        "rich>=10.0.0",
        "pyyaml>=6.0.0",
        "ruamel.yaml>=0.18.0",
        "openai>=1.0.0",
        "tenacity>=8.0.0",
        "pydantic>=1.10.0",
        "PyGithub>=1.59.0",
        "python-dotenv>=0.19.0",
        "google-generativeai>=0.3.2",
    ],
) 