'''
The setup.py file is an essential part of packaging and 
distributing Python projects. It is used by setuptools 
(or distutils in older Python versions) to define the configuration 
of your project, such as its metadata, dependencies, and more
'''
from setuptools import find_packages,setup
from typing import List

def get_requirements()->List[str]: 
    """
    Thiss function will return list of requirements
    
    """ 
    requirement_lst:List[str]=[]
    try:
        with open('requirements.txt' , 'r') as file:
            lines=file.readlines()

            for line in lines :
                requirements=line.strip()

                if requirements and requirements!= '.e .':
                    requirement_lst.append(requirements)

    except FileNotFoundError :
        print("requirements not found")

    return requirement_lst


setup(
    name="Network security",
    version="0.0.1",
    author="amit mehta",
    author_email="mehtamit8406@gmail.com",
    packages=find_packages(),
    install_requires=get_requirements(),
)