import setuptools

with open("README.md", "r", encoding='utf8') as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="bmtools",
    version="0.1.0",
    author="OpenBMB",
    author_email="shengdinghu@gmail.com",
    description="API library for big models to use tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/OpenBMB/BMTools",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    #install_requires=requirements
)
