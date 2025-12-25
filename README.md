# wikidot.py

[![Documentation Status](https://github.com/ukwhatn/wikidot.py/actions/workflows/docs.yml/badge.svg)](https://ukwhatn.github.io/wikidot.py/)

A Python library for easily interacting with Wikidot sites.

## Key Features

- Retrieve and manipulate sites, pages, users, forums, and more
- Create, edit, and delete pages
- Get, create, and reply to forum threads
- User management and site membership
- Send and receive private messages
- Supports both no-login features and authenticated features

## Installation

```bash
pip install wikidot
```

## Basic Usage

```python
import wikidot

# Use without login
client = wikidot.Client()

# Get site and page information
site = client.site.get("scp-jp")
page = site.page.get("scp-173")

print(f"Title: {page.title}")
print(f"Rating: {page.rating}")
print(f"Author: {page.created_by.name}")
```

## Documentation

For detailed usage, API reference, and examples, please see the official documentation:

**[Official Documentation](https://ukwhatn.github.io/wikidot.py/)**

- [Installation](https://ukwhatn.github.io/wikidot.py/installation.html)
- [Quickstart](https://ukwhatn.github.io/wikidot.py/quickstart.html)
- [Examples](https://ukwhatn.github.io/wikidot.py/examples.html)
- [API Reference](https://ukwhatn.github.io/wikidot.py/reference/index.html)

## Building Documentation

To build the documentation locally:

```bash
# Install packages required for documentation generation
make docs-install

# Build the documentation
make docs-build

# View documentation on local server (optional)
make docs-serve
```

## Contribution

- [Roadmap](https://ukwhatn.notion.site/wikidot-py-roadmap?pvs=4)
- [Issue](https://github.com/ukwhatn/wikidot.py/issues)
