# Email Improvement Agent

This is an AI-powered email improvement agent that uses OpenAI's GPT-3.5 to enhance email drafts, making them more professional and effective.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/kaizen-agent.git
cd kaizen-agent
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install the package in development mode:
```bash
pip install -e .
```

4. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

5. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Using Kaizen CLI

The Kaizen CLI provides several commands for testing and improving code:

1. Run tests on a specific file:
```bash
kaizen test path/to/your/file.py --config path/to/test.yaml
```

2. Run an interactive test session:
```bash
kaizen interactive "your code here" --language python --turns 5
```

3. Run a specific test file:
```bash
kaizen run-test path/to/test.yaml
```

### Using Email Agent

You can use the email agent in two ways:

1. Directly provide the email draft:
```bash
python test_agent/email_agent.py --draft "Your email draft here"
```

2. Provide a file containing the email draft:
```bash
python test_agent/email_agent.py --file path/to/your/email.txt
```

## Example

```bash
python test_agent/email_agent.py --draft "hey, i need to schedule a meeting next week to discuss the project timeline. let me know when you're free."
```

The agent will return an improved version of your email draft.

## Testing

To run the test suite:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=kaizen

# Run specific test file
pytest test_kaizen.py
```

For more detailed test examples and configurations, check the `test-examples/` directory and `test.yaml` file.