from setuptools import setup, find_packages

setup(
    name="deriv-backtesting",
    version="0.1.0",
    packages=find_packages(include=['src', 'src.*', 'backtesting', 'backtesting.*']),
    install_requires=[
        "pandas",
        "numpy",
        "python-deriv-api",
        "pytest",
        "pytest-asyncio",
        "pytest-cov"
    ],
    python_requires=">=3.8",
)