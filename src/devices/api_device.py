"""API デバイス実装（Pavlok Cloud API 経由）"""

import logging
import requests

logger = logging.getLogger(__name__)


class APIDevice:
    """Cloud API 経由の Pavlok デバイス。PavlokDevice Protocol に準拠。

    API 接続は stateless なので connect/disconnect は何もしない。
    """

    def __init__(self, api_key: str, api_url: str, use_vibration: bool = False):
        self._api_key = api_key
        self._api_url = api_url
        self._use_vibration = use_vibration

    # ------------------------------------------------------------------ #
    # PavlokDevice インターフェース                                        #
    # ------------------------------------------------------------------ #

    def connect(self) -> bool:
        """API は常時接続不要。キーが設定されていれば True を返す。"""
        if not self._api_key:
            logger.error("PAVLOK_API_KEY が設定されていません（.env を確認してください）")
            return False
        logger.info("Pavlok API モードで起動（スマートフォンアプリが必要です）")
        return True

    def disconnect(self) -> None:
        pass

    def send_zap(self, intensity: int) -> bool:
        """Zap または Vibration を送信する（use_vibration フラグで切り替え）。"""
        stimulus_type = "vibe" if self._use_vibration else "zap"
        return self._send(stimulus_type, intensity)

    def send_vibration(self, intensity: int, count: int = 1, ton: int = 10, toff: int = 10) -> bool:
        """バイブレーションを送信する（API は count/ton/toff を無視）。"""
        return self._send("vibe", intensity)

    # ------------------------------------------------------------------ #
    # 内部送信                                                             #
    # ------------------------------------------------------------------ #

    def _send(self, stimulus_type: str, intensity: int) -> bool:
        payload = {
            "stimulus": {
                "stimulusType": stimulus_type,
                "stimulusValue": intensity,
            }
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(self._api_url, json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                logger.info(f"API {stimulus_type} sent: intensity={intensity}")
                return True
            else:
                logger.error(f"Pavlok API error: {response.status_code} - {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed ({stimulus_type}): {e}")
            return False
