from setuptools import find_packages, setup


setup(
    name="agent-context-score",
    version="0.1.1",
    description="Score AI context instruction files for clarity, safety, and anti-abuse risk.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="alexzhu0",
    license="MIT",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.9",
    entry_points={"console_scripts": ["agent-context-score=agent_context_score.cli:main"]},
)
