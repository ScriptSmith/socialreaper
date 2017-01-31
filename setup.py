from setuptools import setup

setup(
    name='socialreaper',
    version='',
    packages=['socialreaper'],
    package_dir={'socialreaper': 'socialreaper'},
    install_requires=['requests==2.11.1', 'requests-oauthlib', 'oauthlib'],
    url='https://github.com/ScriptSmith/socialreaper',
    license='MIT',
    author='Adam Smith',
    author_email='adamdevsmith@gmail.com',
    description=
        'Social media scraping for Facebook, Twitter, Reddit and Youtube'
)
