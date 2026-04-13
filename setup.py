"""
RAVER Sentinel System Setup Script
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="raver-sentinel",
    version="0.1.0",
    author="RAVER Team",
    author_email="team@raver.ai",
    description="Secure AI Assistant System with Sentinel Protection",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/raver-ai/raver-sentinel",
    packages=find_packages(where="packages"),
    package_dir={"": "packages"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Security",
        "Topic :: System :: Systems Administration",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn[standard]>=0.24.0",
        "websockets>=12.0",
        "pydantic>=2.5.0",
        "cryptography>=41.0.8",
        "python-multipart>=0.0.6",
        "sqlalchemy>=2.0.23",
        "aiofiles>=23.2.1",
        "psutil>=5.9.6",
    ],
    extras_require={
        "windows": ["pywin32>=306", "wmi>=1.5.1"],
        "automation": ["playwright>=1.40.0", "selenium>=4.15.2", "pillow>=10.1.0"],
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "raver-api=apps.api.main:main",
            "raver-ui=apps.ui.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json", "*.yaml", "*.yml"],
    },
)
