import logging
import time
import threading
from datetime import datetime
from pathlib import Path
from queue import Queue

from osc.receiver import OSCReceiver
from osc.sender import OSCSender
from state_machine import GrabStateMachine
from handlers import StimulusHandler, ChatboxHandler, RecorderHandler, GUIUpdater, SpeedModeHandler
from zap_recorder import ZapRecorder
from gui import QueueHandler

# ===== ログ設定 =====
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _setup_file_logging() -> logging.FileHandler | None:
    """settings.debug.log_to_file が True のときファイルハンドラを追加する"""
    from settings import settings as _s
    if not _s.debug.log_to_file:
        return None
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = log_dir / f"pavlok_{timestamp}.log"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(handler)
    return handler


def main():
    """メインプログラム"""
    status_queue: Queue = Queue()
    log_queue: Queue = Queue()

    queue_handler = QueueHandler(log_queue)
    queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(queue_handler)

    file_handler = _setup_file_logging()

    logger.info("===== VRChat Pavlok Connector Starting =====")

    # ------------------------------------------------------------------ #
    # デバイス生成（接続は GUI から行う）                                  #
    # ------------------------------------------------------------------ #
    from devices.factory import create_device
    from pavlok_controller import initialize_device
    device = create_device()
    initialize_device(device)

    # ------------------------------------------------------------------ #
    # 状態機械とハンドラの組み立て                                         #
    # ------------------------------------------------------------------ #
    machine = GrabStateMachine()
    zap_recorder = ZapRecorder()
    machine.zap_recorder = zap_recorder  # tab_stats.py からのアクセス用

    # ハンドラを生成してイベントを購読
    from settings import settings as _s
    if _s.device.zap_mode == "speed":
        SpeedModeHandler(machine, status_queue)
        logger.info("Zap mode: speed")
    else:
        StimulusHandler(machine, status_queue)
        logger.info("Zap mode: stretch")
    ChatboxHandler(machine, OSCSender())
    RecorderHandler(machine, zap_recorder)
    GUIUpdater(machine, status_queue)

    # ------------------------------------------------------------------ #
    # OSC 受信                                                             #
    # ------------------------------------------------------------------ #
    osc_receiver = OSCReceiver()
    osc_receiver.on_stretch_change = machine.on_stretch_change
    osc_receiver.on_grabbed_change = machine.on_grabbed_change

    listener_thread = threading.Thread(target=osc_receiver.start, daemon=True)
    listener_thread.start()
    logger.info("Listening for OSC messages...")

    # ------------------------------------------------------------------ #
    # GUI（メインスレッドで実行）                                           #
    # ------------------------------------------------------------------ #
    try:
        from gui import PavlokGUI
        gui = PavlokGUI()
        gui.status_queue = status_queue
        gui.log_queue = log_queue
        gui.grab_state = machine  # tab_test.py / tab_stats.py が参照
        gui.set_device(device)

        original_on_close = gui.on_close
        def on_close_wrapper():
            logger.info("Shutting down...")
            gui.is_running = False
            osc_receiver.stop()
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
            osc_receiver.stop()

    finally:
        osc_receiver.stop()
        device.disconnect()
        logger.info("===== VRChat Pavlok Connector Stopped =====")
        if file_handler:
            file_handler.close()
            logging.getLogger().removeHandler(file_handler)


if __name__ == "__main__":
    main()
