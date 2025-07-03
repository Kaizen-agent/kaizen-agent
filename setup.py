import setuptools

setuptools.setup(
    name="kaizen-agent",
    version="0.1.3",
    author="Yuto Suzuki",
    author_email="mokkumokku99@gmail.com",
    description="An AI debugging engineer that continuously tests, analyzes, and improves your AI agents and LLM applications",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",    
    python_requires=">=3.8",
    packages=setuptools.find_packages(include=["kaizen", "kaizen.*"]),
) 