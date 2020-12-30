import glob
import os.path as op

from setuptools import setup


def read_file(file):
    with open(file) as fin:
        return fin.read()


def find_all_file(starting_path, *pattern):
    return [
        op.relpath(f, starting_path)
        for f in glob.glob(op.join(starting_path, *pattern, "**"), recursive=True)
    ]


setup(
    name="elaspic-webserver",
    version="0.2.3",
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
        "web_pipeline": (
            [
                "migrations/*",
                "sql/*",
                "templates/*",
            ]
            + find_all_file("web_pipeline", "static")
            + find_all_file("web_pipeline", "tests")
        )
    },
    scripts=["manage.py"],
)
