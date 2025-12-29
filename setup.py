from setuptools import setup, find_packages
from capturemd import __version__

setup(
    name="capturemd",
    version=__version__,
    description="A tool for capturing web content into markdown files",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/capturemd",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4>=4.9.0",
        "pyperclip>=1.8.0",
        "pyyaml>=5.1",
        "requests>=2.25.0",
        "yt-dlp>=2023.0.0",
    ],
    entry_points={
        "console_scripts": [
            "capturemd=capturemd.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Utilities",
    ],
    python_requires=">=3.6",
)