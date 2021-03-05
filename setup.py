import setuptools

setuptools.setup(
    name='wikidot',
    version='0.1.61',
    description='Wikidot AMC utility',
    author='ukwhatn',
    author_email='ukwhatn@gmail.com',
    url='https://github.com/SCP-JP/ukwhatn_wikidot.py',
    packages=setuptools.find_packages(),
    python_requires='>=3.9',
    install_requires=[
        "bs4==0.0.1",
        "feedparser==6.0.2",
        "httpx==0.16.1",
        "lxml==4.6.2"
    ]
)
