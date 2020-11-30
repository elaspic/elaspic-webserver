from setuptools import setup


def read_file(file):
    with open(file) as fin:
        return fin.read()


setup(
    name="elaspic-webserver",
    version="0.0.10",
    author="kimlab",
    author_email="alex.strokach@utoronto.ca",
    url="http://elaspic.kimlab.org",
    description="Webserver for running ELASPIC",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    license="MIT",
    packages=["mum", "web_pipeline"],
    package_data={
        "web_pipeline": [
            "migrations/*",
            "sql/*",
            "static/*",
            "static/css/*",
            "static/fonts/*",
            "static/images/*",
            "static/js/*",
            "static/jsmol/*",
            "templates/*",
            "tests/*",
        ],
    },
    scripts=["manage.py"],
)
