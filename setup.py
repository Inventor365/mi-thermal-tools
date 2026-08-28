from setuptools import setup, find_packages

setup(
    name="mi-thermal-editor",
    version="1.0.0",
    description="Linux GUI and CLI suite for decrypting, analyzing, editing, and injecting Xiaomi/HyperOS thermal configurations.",
    packages=find_packages(),
    install_requires=[
        "cryptography>=38.0.0",
        "PySide6>=6.0.0",
    ],
    entry_points={
        "console_scripts": [
            "mi-thermal-editor=mi_thermal_editor.cli:main",
        ],
    },
    python_requires=">=3.8",
)
