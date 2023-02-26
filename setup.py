from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in mymb_ecommerce/__init__.py
from mymb_ecommerce import __version__ as version

setup(
	name="mymb_ecommerce",
	version=version,
	description="Mymb Ecommerce integrations",
	author="Crowdechain S.r.o",
	author_email="developers@crowdechain.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
