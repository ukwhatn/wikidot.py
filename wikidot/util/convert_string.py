import re
from .table import char_table


def to_unix(target_str: str) -> str:
    """Convert string to unix style.

    Parameters
    ----------
    target_str: str
        string to convert

    Returns
    -------
    str
        converted string
    """
    # MEMO: legacy wikidotの実装に合わせている

    # create translation table
    table = str.maketrans(char_table.special_char_map)
    # translate
    target_str = target_str.translate(table)

    # to lowercase
    target_str = target_str.lower()

    # convert to ascii
    target_str = re.sub(r'[^a-z0-9\-:_]', '-', target_str)
    target_str = re.sub(r'^_', ':_', target_str)
    target_str = re.sub(r'(?<!:)_', '-', target_str)
    target_str = re.sub(r'^-*', '', target_str)
    target_str = re.sub(r'-*$', '', target_str)
    target_str = re.sub(r'-{2,}', '-', target_str)
    target_str = re.sub(r':{2,}', ':', target_str)
    target_str = target_str.replace(':-', ':')
    target_str = target_str.replace('-:', ':')
    target_str = target_str.replace('_-', '_')
    target_str = target_str.replace('-_', '_')

    # remove colon at the beginning and end
    target_str = re.sub(r'^:', '', target_str)
    target_str = re.sub(r':$', '', target_str)

    return target_str
