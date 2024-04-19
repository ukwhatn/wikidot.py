from dataclasses import dataclass


@dataclass(frozen=True)
class APIKeys:
    """APIキーのオブジェクト

    Attributes
    ----------
    ro_key: str
        Read Only Key
    rw_key: str
        Read-Write Key
    """

    ro_key: str
    rw_key: str
