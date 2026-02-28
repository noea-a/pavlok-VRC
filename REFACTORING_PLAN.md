# リファクタリング計画

## 目標
コードの安定性・保守性・拡張性を高める。動作は変えない。

---

## フェーズ一覧

### Phase 1: 設定管理の安全化（最優先）
**目的**: GUI から `config.py` を直接書き換えるリスクをなくす

- [x] **1-1** `config/default.toml` を作成し、現在の `config.py` の全設定値を移す
- [x] **1-2** `src/settings.py` を作成：TOML を読み込み、dataclass で型安全に保持
  - 秘密情報（API KEY, MAC アドレス）は引き続き `.env` から読む
  - `user.toml`（上書き用）が存在すれば `default.toml` にマージして読む
- [x] **1-3** `src/config.py` を `settings.py` への薄いラッパーに変更（既存コードの import を壊さない）
- [x] **1-4** `gui/tab_settings.py` の保存処理を `user.toml` 書き込みに変更
  - `ast` による config.py 書き換えを廃止
- [x] **1-5** `.gitignore` に `config/user.toml` を追加

---

### Phase 2: デバイス抽象化の完成
**目的**: BLE/API 切り替えの `if CONTROL_MODE` 分岐をコード全体から一掃する

- [x] **2-1** `src/devices/base.py` を作成：`PavlokDevice` Protocol を定義
- [x] **2-2** `src/devices/ble_device.py` を作成：`ble_controller.py` の `PavlokBLE` クラスを `PavlokDevice` に準拠させてラップ
- [x] **2-3** `src/devices/api_device.py` を作成：`pavlok_controller.py` の API 送信部分を `PavlokDevice` に準拠させてラップ
- [x] **2-4** `src/devices/factory.py` を作成：`CONTROL_MODE` を見てデバイスを返すファクトリ関数
- [x] **2-5** `main.py` と `pavlok_controller.py` の `CONTROL_MODE` 分岐を全て削除し、ファクトリ経由に変更

---

### Phase 3: 強度計算の分離
**目的**: デバイス制御コードから純粋計算ロジックを切り出し、テスト可能にする

- [ ] **3-1** `src/intensity.py` を作成：`calculate_intensity()` と `normalize_for_display()` を純粋関数として実装
  - 引数で設定値を受け取る（グローバル変数に依存しない）
- [ ] **3-2** `pavlok_controller.py` と `ble_controller.py` から計算関数を削除し、`intensity.py` を参照するように変更
- [ ] **3-3** `tools/test_nonlinear_intensity.py` を `tests/test_intensity.py` として pytest 形式に書き直す

---

### Phase 4: OSC 送受信の分離
**目的**: `OSCListener` が送信も担っている責務の混在を解消する

- [ ] **4-1** `src/osc/receiver.py` を作成：受信のみに特化（現 `OSCListener` のリスナー部分）
- [ ] **4-2** `src/osc/sender.py` を作成：送信のみに特化（`send_parameter`, `send_chatbox_message`）
- [ ] **4-3** `src/osc_listener.py` を削除し、参照箇所を更新

---

### Phase 5: GrabState の責務分離
**目的**: 状態機械から副作用（送信・記録・GUI更新）を切り出す

- [ ] **5-1** `src/state_machine.py` を作成：純粋な状態遷移ロジックのみ
  - `on_grab_start`, `on_grab_end`, `on_stretch_update` イベントを発行するコールバックリストを持つ
  - GUI キュー・OSC 送信・ZapRecorder への直接依存をなくす
- [ ] **5-2** `src/handlers/stimulus.py` を作成：Pavlok 刺激送信ハンドラ
- [ ] **5-3** `src/handlers/chatbox.py` を作成：Chatbox 送信ハンドラ（スロットル付き）
- [ ] **5-4** `src/handlers/recorder.py` を作成：Zap 記録ハンドラ
- [ ] **5-5** `main.py` でイベントにハンドラを接続する形に変更

---

### Phase 6: ディレクトリ整理と最終クリーンアップ
**目的**: 不要ファイルの削除と構成の整頓

- [ ] **6-1** 旧ファイルを削除：`src/osc_listener.py`, `src/ble_controller.py`（devices/ 配下に移行済み）
- [ ] **6-2** `src/pavlok_bleak_controller.py`（未使用と思われる）の確認と削除
- [ ] **6-3** 最終ディレクトリ構成を確認し `PROJECT_STRUCTURE.md` を更新

---

## 最終ディレクトリ構成（目標）

```
pavlok_vrc/
├── config/
│   ├── default.toml        # デフォルト設定（git管理）
│   └── user.toml           # ユーザー上書き分（gitignore）
├── src/
│   ├── app.py              # エントリポイント（旧 main.py）
│   ├── state_machine.py    # Grab状態機械（純粋ロジック）
│   ├── intensity.py        # 強度計算（純粋関数）
│   ├── settings.py         # 設定読み込み・保存
│   ├── devices/
│   │   ├── __init__.py
│   │   ├── base.py         # PavlokDevice Protocol
│   │   ├── ble_device.py   # BLE実装
│   │   ├── api_device.py   # API実装
│   │   └── factory.py      # デバイスファクトリ
│   ├── osc/
│   │   ├── __init__.py
│   │   ├── receiver.py     # OSC受信
│   │   └── sender.py       # OSC送信
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── stimulus.py     # 刺激送信ハンドラ
│   │   ├── chatbox.py      # Chatboxハンドラ
│   │   └── recorder.py     # Zap記録ハンドラ
│   └── gui/
│       ├── __init__.py
│       ├── app.py
│       ├── tab_dashboard.py
│       ├── tab_log.py
│       ├── tab_settings.py  # user.toml に書き込む方式に変更
│       ├── tab_stats.py
│       └── tab_test.py
├── tests/
│   ├── test_intensity.py
│   ├── test_state_machine.py
│   └── test_recorder.py
├── tools/
│   └── generate_intensity_graph.py
├── data/
│   └── zap_records.json
└── .env
```

---

## 作業ルール

- 各フェーズは**動作確認してから次へ**（フェーズをまたいだ大きな変更は避ける）
- 旧ファイルはフェーズ内で段階的に削除（いきなり消さない）
- コミットは各タスク完了ごとに行う
- コミットメッセージ形式：`リファクタ: [フェーズ番号] 説明`
