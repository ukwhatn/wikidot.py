# wikidot.py - A Python library for making requests to the Wikidot sites.

## Installation
```bash
pip install wikidot
```

## Usage
> [!NOTE]
> You can use this library without logging in, but you can only use the features that do not require logging in.
```python
import wikidot

# Create a new Client class and logging in with the credentials of your wikidot account
# If you don't want to log in : with wikidot.Client() as client:
with wikidot.Client(username='input-your-name', password='input-your-password') as client:
    # ------
    # user features
    # ------
    # Get the user object of the user
    user = client.user.get('input-a-username')
    # Bulk execution by asynchronous request
    users = client.user.get_bulk(['input-a-username', 'input-another-username'])

    # ------
    # site features
    # ------
    # Get the site object of the SCP Foundation
    site = client.site.get('scp-wiki')

    # invite a user to the site
    site.invite_user(user)

    # Get all unprocessed applications for the site
    applications = site.get_applications()

    # process an application
    for application in applications:
        application.accept()
        # or 
        application.reject()

    # ------
    # page features
    # ------
    # Search pages by some criteria
    # NOTE: The search criteria are the same as in the ListPages module
    pages = site.pages.search(
        category="_default",
        tags=["tag1", "tag2"],  # You can also use the "tag1 -tag2" syntax
        order="created_at desc desc",
        limit=10,
    )

    # Get the page object of the SCP-001
    page = site.page.get('scp-001')

    # destroy a page
    page.destroy()

    # ------
    # private message features
    # ------
    # Get messages in your inbox
    received_messages = client.private_message.get_inbox()

    # Get messages in your sent box
    sent_messages = client.private_message.get_sentbox()

    # Get message by id
    # NOTE: You can only get the message that you have received or sent
    message = client.private_message.get(123456)
    # Bulk execution by asynchronous request
    messages = client.private_message.get_messages([123456, 123457])

    # Send a message to a user
    client.private_message.send(
        recipient=user,
        subject='Hello',
        body='Hello, world!'
    )
```