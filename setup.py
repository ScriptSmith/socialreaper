from setuptools import setup, find_packages

setup(
    name='socialreaper',
    version='1.0.3',
    packages=find_packages(),
    package_dir={'socialreaper': 'socialreaper'},
    install_requires=['requests>=2.11.1', 'requests-oauthlib>=0.7.0',
                      'oauthlib>=2.0.1'],
    url='https://github.com/ScriptSmith/socialreaper',
    license='MIT',
    author='Adam Smith',
    author_email='adamdevsmith@gmail.com',
    description=
    'Social media scraping for Facebook, Twitter, Reddit, Youtube, Pinterest,'
    ' and Tumblr',
    keywords='social media socialmedia facebook twitter reddit youtube '
             'pinterest tumblr data scrape'
)
