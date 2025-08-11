"""
Setup configuration for tunnel-cli
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="tunnel-cli",
    version="1.0.0",
    author="Tunnel Team",
    author_email="support@tunnel.ovream.com",
    description="Terminal User Interface for managing tunnels",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tunnel/tunnel-cli",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=[
        "textual>=0.47.0",
        "aiohttp>=3.9.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "tunnel=tunnel_cli.__main__:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)