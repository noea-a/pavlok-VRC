import logging
import time
import threading
from datetime import datetime
from queue import Queue
from osc_listener import OSCListener
from zap_recorder import ZapRecorder
from config import (
    MIN_GRAB_DURATION, USE_VIBRATION,
    GRAB_START_VIBRATION_INTENSITY, GRAB_START_VIBRATION_COUNT,
    GRAB_START_VIBRATION_TON, GRAB_START_VIBRATION_TOFF,
    VIBRATION_ON_STRETCH_INTENSITY, VIBRATION_ON_STRETCH_COUNT,
    VIBRATION_ON_STRETCH_TON, VIBRATION_ON_STRETCH_TOFF,
    VIBRATION_ON_STRETCH_THRESHOLD, VIBRATION_HYSTERESIS_OFFSET,
    OSC_SEND_INTERVAL, SEND_REALTIME_CHATBOX,
    MIN_STIMULUS_VALUE, MAX_STIMULUS_VALUE,
)
import pavlok_controller as stimulus_controller
from pavlok_controller import calculate_zap_intensity as calculate_intensity
from pavlok_controller import normalize_intensity_for_display

logger_prefix = "[Pavlok]"

# ===== ログハンドラ =====
class QueueHandler(logging.Handler):
    """ログメッセージをキューに送信するカスタムハンドラ"""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.queue.put((record.levelname, msg))
        except Exception:
            pass


# ===== ログ設定 =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===== 状態管理 =====
class GrabState:
    def __init__(self, osc_sender=None, status_queue=None, log_queue=None):
        self.is_grabbed = False
        self.grab_start_time = None
        self.current_stretch = 0.0
        self.stretch_above_threshold = False  # ヒステリシス用：Stretch超過状態
        self.last_osc_send_time = 0.0  # Chatbox送信のスロットル用
        self.osc_sender = osc_sender  # OSC送信用リファレンス
        self.status_queue = status_queue  # GUI ステータス更新用
        self.log_queue = log_queue  # GUI ログ用
        self.zap_recorder = ZapRecorder()  # Zap記録管理
        self.is_test_mode = False  # テストモードフラグ
        self.last_zap_display_intensity = 0  # 最終 Zap 表示強度（%）
        self.last_zap_actual_intensity = 0   # 最終 Zap 内部値

    def reset(self):
        """状態をリセット"""
        self.stretch_above_threshold = False

    def send_status_update(self):
        """GUI へステータス更新を送信"""
        if self.status_queue:
            try:
                intensity = calculate_intensity(self.current_stretch) if self.is_grabbed else 0
                self.status_queue.put({
                    'is_grabbed': self.is_grabbed,
                    'stretch': self.current_stretch,
                    'intensity': intensity,
                    'last_zap_display_intensity': self.last_zap_display_intensity,
                    'last_zap_actual_intensity': self.last_zap_actual_intensity,
                })
            except Exception:
                pass

    def on_stretch_change(self, value):
        """Stretch値が変更された"""
        self.current_stretch = value
        self.send_status_update()
        if self.is_grabbed:
            logger.debug(f"Stretch updated: {value:.3f}")

            # リアルタイム Chatbox 送信（スロットル付き）
            if SEND_REALTIME_CHATBOX and self.osc_sender and time.time() - self.last_osc_send_time > OSC_SEND_INTERVAL:
                intensity = calculate_intensity(value)
                if intensity > 0:
                    display_intensity = normalize_intensity_for_display(intensity)
                    self.osc_sender.send_chatbox_message(f"Zap: {display_intensity}%", send_immediately=True)
                    self.last_osc_send_time = time.time()

            # Stretch超過時のバイブレーション（ヒステリシス付き）
            if value > VIBRATION_ON_STRETCH_THRESHOLD:
                if not self.stretch_above_threshold:
                    self.stretch_above_threshold = True
                    intensity = calculate_intensity(value)
                    logger.info(f"{logger_prefix} [STRETCH THRESHOLD EXCEEDED (VIBRATION)] Value: {value:.3f}, Intensity: {intensity}")
                    stimulus_controller.send_vibration(intensity, VIBRATION_ON_STRETCH_COUNT, VIBRATION_ON_STRETCH_TON, VIBRATION_ON_STRETCH_TOFF)
            elif value < VIBRATION_ON_STRETCH_THRESHOLD - VIBRATION_HYSTERESIS_OFFSET:
                if self.stretch_above_threshold:
                    self.stretch_above_threshold = False
                    logger.info(f"{logger_prefix} [STRETCH BELOW HYSTERESIS] Value: {value:.3f}")

    def on_grabbed_change(self, value):
        """IsGrabbed状態が変更された"""
        old_state = self.is_grabbed
        self.is_grabbed = value
        self.send_status_update()

        if not old_state and value:
            # false → true: Grab開始
            self.grab_start_time = time.time()
            self.reset()
            logger.info(f"{logger_prefix} [GRAB START] Time: {datetime.now().strftime('%H:%M:%S')}")
            logger.info(f"{logger_prefix} [GRAB START VIBRATION] Intensity: {GRAB_START_VIBRATION_INTENSITY}")
            stimulus_controller.send_vibration(GRAB_START_VIBRATION_INTENSITY, GRAB_START_VIBRATION_COUNT, GRAB_START_VIBRATION_TON, GRAB_START_VIBRATION_TOFF)

        elif old_state and not value:
            # true → false: Grab終了
            if self.grab_start_time:
                elapsed_time = time.time() - self.grab_start_time
                logger.info(f"{logger_prefix} [GRAB END] Elapsed: {elapsed_time:.1f}s, Stretch: {self.current_stretch:.3f}")

                if elapsed_time >= MIN_GRAB_DURATION:
                    intensity = calculate_intensity(self.current_stretch)
                    if intensity > 0:
                        stimulus_type = "Vibration" if USE_VIBRATION else "Zap"
                        logger.info(f"{logger_prefix} [GRAB END {stimulus_type.upper()}] Intensity: {intensity}")
                        stimulus_controller.send_zap(intensity)

                        if not USE_VIBRATION:
                            display_intensity = normalize_intensity_for_display(intensity)
                            self.last_zap_display_intensity = display_intensity
                            self.last_zap_actual_intensity = intensity
                            self.send_status_update()

                        if not USE_VIBRATION and not self.is_test_mode:
                            display_intensity = normalize_intensity_for_display(intensity)
                            self.zap_recorder.record_zap(
                                display_intensity=display_intensity,
                                actual_intensity=intensity,
                                min_stimulus_value=MIN_STIMULUS_VALUE,
                                max_stimulus_value=MAX_STIMULUS_VALUE
                            )

                        if self.osc_sender:
                            display_intensity = normalize_intensity_for_display(intensity)
                            self.osc_sender.send_chatbox_message(f"Zap: {display_intensity}% [Final]", send_immediately=True)
                    else:
                        logger.info(f"{logger_prefix} [STIMULUS SKIPPED] Intensity too low (gentle touch)")
                else:
                    logger.info(f"{logger_prefix} [STIMULUS SKIPPED] Too short ({elapsed_time:.1f}s < {MIN_GRAB_DURATION}s)")

                self.grab_start_time = None
                self.current_stretch = 0.0

            self.reset()


def main():
    """メインプログラム"""
    status_queue = Queue()
    log_queue = Queue()

    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(queue_handler)

    logger.info(f"===== VRChat Pavlok Connector Starting =====")

    # デバイスをファクトリで生成・接続（CONTROL_MODE の分岐はここではなく factory.py が担う）
    from devices.factory import create_device
    device = create_device()
    logger.info(f"デバイス接続中: {type(device).__name__}")
    if not device.connect():
        logger.error("デバイス接続失敗。終了します。")
        return

    # pavlok_controller にデバイスを登録
    from pavlok_controller import initialize_device
    initialize_device(device)

    # OSCリスナー作成
    listener = OSCListener()

    # 状態管理オブジェクト作成
    grab_state = GrabState(osc_sender=listener, status_queue=status_queue, log_queue=log_queue)

    listener.on_stretch_change = grab_state.on_stretch_change
    listener.on_grabbed_change = grab_state.on_grabbed_change

    # OSCリスナーを daemon スレッドで起動
    listener_thread = threading.Thread(target=listener.start, daemon=True)
    listener_thread.start()
    logger.info("Listening for OSC messages...")

    # GUI を作成（メインスレッドで実行 - Tkinter の要件）
    try:
        from gui import PavlokGUI
        gui = PavlokGUI()
        gui.status_queue = status_queue
        gui.log_queue = log_queue
        gui.grab_state = grab_state

        original_on_close = gui.on_close
        def on_close_wrapper():
            logger.info("Shutting down...")
            gui.is_running = False
            listener.stop()
            device.disconnect()
            original_on_close()

        gui.on_close = on_close_wrapper

        logger.info("Starting GUI...")
        gui.run()

    except Exception as e:
        logger.error(f"GUI 起動に失敗しました: {e}")
        import traceback
        traceback.print_exc()
        try:
            logger.info("Running without GUI (console mode)...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            listener.stop()

    finally:
        listener.stop()
        device.disconnect()
        logger.info(f"===== VRChat Pavlok Connector Stopped =====")


if __name__ == "__main__":
    main()
