from setuptools import setup, find_packages

setup(
    name="mega_buddies_bot",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot==13.15",  # Используем стабильную версию 13.x
        "python-dotenv",
    ],
    python_requires=">=3.7",
) 