# ---
# 基底クラス
# ---


class WikidotException(Exception):
    """
    wikidot.py独自の例外の基底クラス

    ライブラリ内で発生する全ての例外の親クラスとなる。
    具体的な例外は各サブクラスで定義される。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


# ---
# ワイルドカード
# ---


class UnexpectedException(WikidotException):
    """
    予期せぬ例外が発生したときに送出される例外

    特定のエラー状態に分類できない、予期しない状況で発生する。
    通常は内部エラーやバグを示す。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


# ---
# セッション関連
# ---


class SessionCreateException(WikidotException):
    """
    セッションの作成に失敗したときに送出される例外

    ログイン処理やセッション確立時に問題が発生した場合に使用される。
    通常は認証情報の誤りやサーバー側の問題が原因となる。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


class LoginRequiredException(WikidotException):
    """
    ログインが必要なメソッドを未ログイン状態で呼び出したときに送出される例外

    認証が必要な操作を実行する前に、ログイン状態をチェックする際に使用される。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


# ---
# AMC関連
# ---
class AjaxModuleConnectorException(WikidotException):
    """
    Ajax Module Connectorへのリクエストに関連する例外の基底クラス

    ajax-module-connector.phpへのAPIリクエスト処理中に発生する例外の親クラス。
    具体的なエラー状態は各サブクラスで表現される。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


class AMCHttpStatusCodeException(AjaxModuleConnectorException):
    """
    AMCのHTTPステータスコードが200以外だった場合に送出される例外

    Ajax Module ConnectorへのリクエストでHTTPレベルのエラーが発生した場合に使用される。

    Parameters
    ----------
    message : str
        例外メッセージ
    status_code : int
        エラーとなったHTTPステータスコード

    Attributes
    ----------
    status_code : int
        エラーとなったHTTPステータスコード
    """

    def __init__(self, message, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class WikidotStatusCodeException(AjaxModuleConnectorException):
    """
    AMCからのレスポンスのステータスが「ok」でなかった場合に送出される例外

    HTTP通信自体は成功したが、Wikidot側で処理エラーが発生した場合に使用される。
    HTTPステータスが200以外の場合は代わりにAMCHttpStatusCodeExceptionが使用される。

    Parameters
    ----------
    message : str
        例外メッセージ
    status_code : str
        Wikidotから返されたエラーステータスコード

    Attributes
    ----------
    status_code : str
        Wikidotから返されたエラーステータスコード
    """

    def __init__(self, message, status_code: str):
        super().__init__(message)
        self.status_code = status_code


class ResponseDataException(AjaxModuleConnectorException):
    """
    AMCからのレスポンスデータが不正だった場合に送出される例外

    レスポンスのパース失敗や、期待された形式と異なるデータが返された場合に使用される。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


# ---
# ターゲットエラー関連
# ---


class NotFoundException(WikidotException):
    """
    要求されたリソースが見つからない場合に送出される例外

    サイト、ページ、ユーザー、リビジョンなど、指定されたリソースが
    Wikidot上に存在しない場合に使用される。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


class TargetExistsException(WikidotException):
    """
    既に存在するリソースを作成しようとした場合に送出される例外

    新規作成操作が既存のリソースと衝突する場合に使用される。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


class TargetErrorException(WikidotException):
    """
    対象オブジェクトに操作を適用できない場合に送出される例外

    リソースは存在するが、現在の状態では要求された操作を
    実行できない場合に使用される（例：ロック中のページを編集しようとする）。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


class ForbiddenException(WikidotException):
    """
    権限不足により操作が拒否された場合に送出される例外

    ユーザーが操作に必要な権限を持っていない場合や、
    プライベートサイトへのアクセスが拒否された場合などに使用される。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)


# ---
# 処理エラー関連
# ---


class NoElementException(WikidotException):
    """
    必要な要素が見つからない場合に送出される例外

    HTML解析時に期待された要素が見つからない場合など、
    処理中に必要なデータが欠落している場合に使用される。

    Parameters
    ----------
    message : str
        例外メッセージ
    """

    def __init__(self, message):
        super().__init__(message)
