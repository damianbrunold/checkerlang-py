from setuptools import setup, find_packages

setup(
        name="ckl", 
        version="3.5.2",
        author="Damian Brunold",
        author_email="dab@dabsoft.ch",
        packages=find_packages(),
        package_data={"checkerlang-py": ["modules/*.ckl"]},
)
