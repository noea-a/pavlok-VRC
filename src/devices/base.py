"""デバイス抽象化 Protocol"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class PavlokDevice(Protocol):
    """Pavlok デバイスの共通インターフェース。

    BLE / API など接続方式の違いを隠蔽する。
    すべてのメソッドは同期呼び出し（内部で非同期処理をする場合はラップする）。
    """

    def connect(self) -> bool:
        """デバイスに接続する。成功時 True を返す。"""
        ...

    def disconnect(self) -> None:
        """デバイスとの接続を切断する。"""
        ...

    def send_zap(self, intensity: int) -> bool:
        """Zap（電気刺激）を送信する。

        Args:
            intensity: 強度（MIN_STIMULUS_VALUE〜MAX_STIMULUS_VALUE）
        Returns:
            送信成功時 True
        """
        ...

    def send_vibration(self, intensity: int, count: int = 1, ton: int = 10, toff: int = 10) -> bool:
        """バイブレーションを送信する。

        Args:
            intensity: 強度（0〜100）
            count: 反復回数（1〜127）
            ton: ON 時間（0〜255）
            toff: OFF 時間（0〜255）
        Returns:
            送信成功時 True
        """
        ...
