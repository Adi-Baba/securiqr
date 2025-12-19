from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="securiqr",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A dual-layer authenticated barcode system for secure product verification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Adi-Baba/securiqr",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
        "Topic :: Security :: Cryptography",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "securiqr-gen=securiqr.cli.generate:main",
            "securiqr-verify=securiqr.cli.verify:main",
            "securiqr-read=securiqr.cli.universal_reader:main",
        ],
    },
)