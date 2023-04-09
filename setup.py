import setuptools

with open("VERSION", 'r') as f:
    version = f.read().strip()

with open("README.md", 'r') as f:
    long_description = f.read()

setuptools.setup(
   name='xtouchmini',
   version=version,
   description='Library to control Berhinger X-Touch Mini devices.',
   author='Pierre M',
   author_email='pierre@devleaks.be',
   url='https://github.com/devleaks/python-berhinger-xtouchmini',
   package_dir={'': 'src'},
   packages=setuptools.find_packages(where='src'),
   install_requires=[
     "mido==1.2.10",
     "python-rtmidi==1.4.9"
   ],
   license="MIT",
   long_description=long_description,
   long_description_content_type="text/markdown",
   include_package_data=True,
   python_requires=">=3.8,<3.11",
)
