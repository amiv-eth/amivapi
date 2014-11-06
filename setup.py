from setuptools import setup, find_packages

setup(
    name="amivapi",
    version="0.0",
    url="https://www.amiv.ethz.ch",
    author="AMIV IT Team",
    author_email="it@amiv.ethz.ch",
    description=("The REST API behind most of AMIV's web services."),
    packages=find_packages(),
)
