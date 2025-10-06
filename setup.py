from setuptools import setup, find_packages
from pathlib import Path

about = {}
exec((Path("gdscript_to_docs") / "__init__.py").read_text(), about)

setup(
    name="gdscript-to-docs",
    version=about["__version__"],
    description="Export Godot 4.5 GDScript doc-comments to Markdown.",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/phaseLineStudios/gdscript_to_docs",
    author="Eirik",
    author_email="tapwingo.actual@pm.me",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.9",
    install_requires=[],
    extras_require={
        "dev": [ "pytest>=7", "pytest-cov>=4", "python-coveralls" ],
    },
    entry_points={
        "console_scripts": [
            "gdscript_to_docs=gdscript_to_docs.cli:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Documentation",
        "Environment :: Console",
    ],
    include_package_data=True,
    zip_safe=False,
)
