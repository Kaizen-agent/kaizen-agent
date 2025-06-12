from setuptools import setup, find_packages

setup(
    name="kaizen-agent",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv>=0.19.0",
        "click>=8.0.0",
        "pyyaml>=6.0.0",
    ],
    entry_points={
        'console_scripts': [
            'kaizen=kaizen.cli:cli',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A CLI tool for testing AI agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/kaizen-agent",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
) 