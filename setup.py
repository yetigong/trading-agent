from setuptools import setup, find_packages

setup(
    name="trading-agent",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "schedule",
        "python-dotenv",
        "alpaca-trade-api",
        "anthropic",
        "google-generativeai",
        "openai"
    ],
    python_requires=">=3.9",
) 