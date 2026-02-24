# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VRChat Pavlok Connector**: A Python application that integrates VRChat PhysBone interactions with the Pavlok haptic feedback device. When other players grab and stretch a designated PhysBone in VRChat, the application triggers corresponding haptic feedback (vibration or electrical stimulation).

## Architecture

### Core Data Flow
```
VRChat OSC Parameters → OSCListener → GrabState Logic → Pavlok Control
    ├─ Stretch (0-1)
    ├─ IsGrabbed (bool)
    ├─ Angle (float)
    └─ IsPosed (bool)
```

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| `main.py` | Event loop, GrabState management, OSC-to-stimulus coordination |
| `osc_listener.py` | Receives VRChat parameters via UDP/OSC on port 9001 |
| `config.py` | Centralized configuration, constants, and thresholds |
| `pavlok_controller.py` | API-based stimulus control (cloud/smartphone relay) |
| `gui.py` | Tkinter-based dashboard UI (status, settings, logs, statistics) |
| `zap_recorder.py` | Zap execution logging and statistics (JSON persistence) |

### Control Flow Details

**GrabState** (`main.py`) manages three main events:

1. **Grab Start** (IsGrabbed: false → true)
   - Triggers immediate vibration at `GRAB_START_VIBRATION_INTENSITY`
   - Resets internal state

2. **Grab Duration** (while IsGrabbed: true)
   - Monitors Stretch value
   - If `Stretch > VIBRATION_ON_STRETCH_THRESHOLD`: sends vibration
   - Hysteresis prevents re-triggering until `Stretch < VIBRATION_HYSTERESIS_THRESHOLD`

3. **Grab End** (IsGrabbed: true → false)
   - If duration ≥ `MIN_GRAB_DURATION` (e.g., 1.0s)
   - Calculates intensity from final Stretch value
   - Sends final stimulus (type depends on `USE_VIBRATION` config)

### Stimulus Intensity Calculation

**Non-linear mapping with two-slope piecewise function**:
1. **Stretch < MIN_STRETCH_THRESHOLD**: 0 (no stimulus)
2. **Stretch ≤ MIN_STRETCH_PLATEAU**: MIN_STIMULUS_VALUE fixed plateau (low plateau)
3. **Stretch MIN_STRETCH_PLATEAU to switch point**: First linear segment
   - Switch point position: `NONLINEAR_SWITCH_POSITION_PERCENT` of range
   - Intensity at switch: `INTENSITY_AT_SWITCH_PERCENT` of [MIN, MAX] range
4. **Stretch switch point to MAX_STRETCH_FOR_CALC**: Second linear segment (steeper slope)
5. **Stretch ≥ MAX_STRETCH_FOR_CALC**: MAX_STIMULUS_VALUE (high plateau)

This creates a smooth piecewise-linear curve with adjustable transition point. Both thresholds and slopes are configurable via config.py.

### Control Mode

Currently uses API-based control:

| Implementation | Advantage | Requirement |
|---|---|---|
| `pavlok_controller.py` (API) | Stable, proven, cloud-based | Smartphone with Pavlok app |

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run Application
```bash
# Start the main connector with GUI dashboard
python src/main.py

# OR run headless (no GUI)
python src/main.py --no-gui
```

### Testing
```bash
# Test piecewise-linear intensity calculation
python tools/test_nonlinear_intensity.py
```

### Debugging
- Enable logging: Modify `DEBUG_LOG_*` settings in `config.py`
- Monitor OSC packets: Set `DEBUG_LOG_ALL_OSC = True`
- Check Grab events: Set `DEBUG_LOG_IS_GRABBED = True`
- Verify Stretch sensitivity: Set `DEBUG_LOG_STRETCH = True`

## Configuration

All settings are in `src/config.py`. Key parameters (see config.py for current values):

| Setting | Purpose |
|---------|---------|
| `USE_VIBRATION` | Stimulus type (vibration vs electrical zap) |
| `MIN_GRAB_DURATION` | Minimum grab time before sending final stimulus |
| `MIN_STRETCH_THRESHOLD` | Ignore Stretch values below this threshold |
| `MIN_STRETCH_PLATEAU` | Fixed stimulus plateau zone (low end) |
| `GRAB_START_VIBRATION_INTENSITY` | Intensity when grab starts |
| `VIBRATION_ON_STRETCH_THRESHOLD` | Trigger vibration when Stretch exceeds this |
| `VIBRATION_HYSTERESIS_THRESHOLD` | Reset vibration trigger below this Stretch |
| `NONLINEAR_SWITCH_POSITION_PERCENT` | Piecewise function slope switch point (% of range) |
| `INTENSITY_AT_SWITCH_PERCENT` | Intensity at switch point (% of MIN-MAX range) |
| `MIN_STIMULUS_VALUE` | Minimum output stimulus value |
| `MAX_STIMULUS_VALUE` | Maximum output stimulus value |
| `MIN_STRETCH_FOR_CALC` | Input range lower bound for intensity calculation |
| `MAX_STRETCH_FOR_CALC` | Input range upper bound for intensity calculation |

### Environment Variables

Create `.env` file (not version-controlled):
```
PAVLOK_API_KEY=your_api_key_here
LIMIT_PAVLOK_ZAP_VALUE=50  # Optional intensity cap
```

## Common Development Tasks

### Add a New OSC Parameter
1. Add handler method to `OSCListener` class in `osc_listener.py`
2. Add config constant for the parameter path
3. Register handler in `OSCListener.start()`
4. Add callback in `main.py` if state tracking needed

### Modify Stimulus Intensity
Edit intensity calculation in `pavlok_controller.py`:
- `calculate_zap_intensity()`: Maps Stretch values to stimulus intensity
- Piecewise-linear function with configurable switch point and slopes
- Adjust `NONLINEAR_SWITCH_POSITION_PERCENT` and `INTENSITY_AT_SWITCH_PERCENT` in config.py for tuning

### Debug Grab Events
Enable these in `config.py`:
```python
DEBUG_LOG_IS_GRABBED = True
DEBUG_LOG_STRETCH = True
DEBUG_LOG_ALL_OSC = True
```

Monitor `main.py` console output for state transitions.

## Key Implementation Details

### Hysteresis Logic
Prevents vibration re-triggering while Stretch oscillates near threshold:
- Triggers when `Stretch > VIBRATION_ON_STRETCH_THRESHOLD` (0.7)
- Won't re-trigger until `Stretch < VIBRATION_HYSTERESIS_THRESHOLD` (0.55)
- Prevents rapid, jarring multiple activations

### Thread Safety
- OSC listener runs in daemon thread
- State reads/writes in `GrabState` are atomic (single-threaded concern)
- No explicit locking required (Python GIL + simple value assignments)

### Graceful Shutdown
- Ctrl+C triggers `signal_handler` in main.py
- OSC listener thread stopped
- GUI window closed (if running)
- Clean process exit

## Testing Notes

- **Intensity calculation**: `tools/test_nonlinear_intensity.py` verifies piecewise-linear intensity mapping
- **Visualization**: `tools/generate_intensity_graph.py` plots intensity curve based on current config values
- **Integration**: Full workflow requires VRChat with OSC enabled + Pavlok smartphone app
- **GUI testing**: Dashboard can simulate Grab/Stretch without VRChat (Test Send panel)

## Known Constraints

- OSC server listens on localhost (127.0.0.1:9001) - VRChat on same PC required
- Requires internet connection for Pavlok API calls via smartphone
- Non-linear intensity calculation applies to all stimulus events

## Development Guidelines

### Commit Messages
- **Always use Japanese** for commit messages
- Format: `修正/追加: わかりやすい説明`
- Example: `修正: Stretch < 0.07 のとき強度を0にする`

### Config.py Management
- User actively adjusts config.py values for tuning
- **Do NOT hardcode values** in scripts or documentation
- All scripts must read from config.py at runtime
- When documenting, describe the logic, not specific values

### Graph Generation
- Graph script located in `tools/generate_intensity_graph.py`
- Runs from `tools/` directory with relative imports (`../src`)
- Graph output: `tools/graphs/zap_intensity_curve.png`
- Dynamically generates based on current config values

## Last Updated

- **2026-02-24**: Documentation sync - Logic-focused descriptions, removed hardcoded values, removed obsolete BLE references
- **2026-02-23 (night)**: Zap recording & statistics, BLE test cleanup, documentation updates
- **2026-02-23**: Piecewise-linear intensity curve with adjustable switch point (NONLINEAR_SWITCH_POSITION_PERCENT)
- **2026-02-21**: Nonlinear intensity calculation, graph generation tool, GUI dashboard v1.0
- **2026-02-20**: Grab start vibration and Stretch-threshold vibration features
