"""Zap 実行記録管理クラス"""

import json
import os
from datetime import datetime
from pathlib import Path

_DEFAULT_FILEPATH = Path(__file__).parent.parent / "data" / "zap_records.json"


class ZapRecorder:
    """Zap 実行を JSON ファイルに記録・統計管理するクラス"""

    def __init__(self, filepath=None):
        """
        初期化

        Args:
            filepath (str): JSON ファイルの保存パス
        """
        self.filepath = Path(filepath) if filepath else _DEFAULT_FILEPATH
        self.session_records = []  # メモリ内セッション記録

        # ディレクトリを自動作成
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

        # ファイルから既存記録を読み込み
        self.load_records()

    def record_zap(self, display_intensity, actual_intensity, min_stimulus_value, max_stimulus_value):
        """
        Zap 実行を記録

        Args:
            display_intensity (int): 表示強度（20～100%）
            actual_intensity (int): 実際の Zap 値（内部値）
            min_stimulus_value (int): 当時の MIN_STIMULUS_VALUE 設定値
            max_stimulus_value (int): 当時の MAX_STIMULUS_VALUE 設定値

        Returns:
            dict: 記録されたレコード
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "display_intensity": display_intensity,
            "actual_intensity": actual_intensity,
            "min_stimulus_value": min_stimulus_value,
            "max_stimulus_value": max_stimulus_value
        }
        self.session_records.append(record)
        self.save_records()
        return record

    def load_records(self):
        """
        JSON ファイルから既存レコードを読み込み

        存在しない場合は空の記録で初期化
        """
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # ファイルには全レコードが保存されているが、
                    # セッション記録はリセット（メモリのみ）
                    # - ファイルの全レコードは get_total_stats() で読み込む
                    self.session_records = []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {self.filepath}: {e}. Starting with empty records.")
            self.session_records = []

    def save_records(self):
        """
        セッション記録をファイルに追記保存

        既存ファイルを読み込んで、新しいレコードを追加して保存
        """
        try:
            # 既存ファイルがあれば読み込み
            existing_records = []
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        existing_records = data.get("records", [])
                except (json.JSONDecodeError, IOError):
                    existing_records = []

            # セッション記録を既存レコードに追加
            all_records = existing_records + self.session_records

            # JSON ファイルに保存
            data = {
                "records": all_records,
                "metadata": {
                    "last_updated": datetime.now().isoformat(),
                    "total_records": len(all_records)
                }
            }

            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except IOError as e:
            print(f"Error saving {self.filepath}: {e}")

    def get_session_stats(self):
        """
        セッション記録（メモリ）から統計を計算

        Returns:
            dict: 統計情報
                - total_zaps (int): 総 Zap 回数
                - avg_display_intensity (float): 平均表示強度（%）
                - avg_actual_intensity (float): 平均実際強度（内部値）
                - max_display_intensity (int): 最大表示強度（%）
                - max_actual_intensity (int): 最大実際強度（内部値）
        """
        if not self.session_records:
            return {
                "total_zaps": 0,
                "avg_display_intensity": 0.0,
                "avg_actual_intensity": 0.0,
                "max_display_intensity": 0,
                "max_actual_intensity": 0
            }

        display_intensities = [r["display_intensity"] for r in self.session_records]
        actual_intensities = [r.get("actual_intensity", 0) for r in self.session_records]

        return {
            "total_zaps": len(self.session_records),
            "avg_display_intensity": sum(display_intensities) / len(display_intensities),
            "avg_actual_intensity": sum(actual_intensities) / len(actual_intensities),
            "max_display_intensity": max(display_intensities),
            "max_actual_intensity": max(actual_intensities)
        }

    def get_total_stats(self):
        """
        ファイル内のすべてのレコードから統計を計算

        Returns:
            dict: 統計情報
                - total_zaps (int): 累計 Zap 回数
                - avg_display_intensity (float): 累計平均表示強度（%）
                - avg_actual_intensity (float): 累計平均実際強度（内部値）
                - max_display_intensity (int): 累計最大表示強度（%）
                - max_actual_intensity (int): 累計最大実際強度（内部値）
                - session_avg_zaps (float): セッション当たりの平均 Zap 数
        """
        try:
            if not os.path.exists(self.filepath):
                return {
                    "total_zaps": 0,
                    "avg_display_intensity": 0.0,
                    "avg_actual_intensity": 0.0,
                    "max_display_intensity": 0,
                    "max_actual_intensity": 0,
                    "session_avg_zaps": 0.0
                }

            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                records = data.get("records", [])

            if not records:
                return {
                    "total_zaps": 0,
                    "avg_display_intensity": 0.0,
                    "avg_actual_intensity": 0.0,
                    "max_display_intensity": 0,
                    "max_actual_intensity": 0,
                    "session_avg_zaps": 0.0
                }

            # 日付ベースのセッション数を計算
            unique_dates = set()
            for record in records:
                timestamp_str = record.get("timestamp", "")
                if timestamp_str:
                    date_part = timestamp_str.split("T")[0]  # ISO形式から日付部分を抽出
                    unique_dates.add(date_part)

            session_count = max(len(unique_dates), 1)  # 最低1セッション

            display_intensities = [r["display_intensity"] for r in records]
            actual_intensities = [r.get("actual_intensity", 0) for r in records]

            return {
                "total_zaps": len(records),
                "avg_display_intensity": sum(display_intensities) / len(display_intensities),
                "avg_actual_intensity": sum(actual_intensities) / len(actual_intensities),
                "max_display_intensity": max(display_intensities),
                "max_actual_intensity": max(actual_intensities),
                "session_avg_zaps": len(records) / session_count
            }

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error reading stats from {self.filepath}: {e}")
            return {
                "total_zaps": 0,
                "avg_display_intensity": 0.0,
                "avg_actual_intensity": 0.0,
                "max_display_intensity": 0,
                "max_actual_intensity": 0,
                "session_avg_zaps": 0.0
            }

    def reset_records(self):
        """
        記録をリセット（ファイルを削除）
        """
        try:
            if os.path.exists(self.filepath):
                os.remove(self.filepath)
            self.session_records = []
        except IOError as e:
            print(f"Error deleting {self.filepath}: {e}")
