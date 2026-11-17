# Izakami Risk Calculator

A lightweight, offline-first, floating position-size calculator for Windows (Python + PySide6).
Enter Entry and Stop Loss and Izakami works out the direction, position size, take-profit,
position value, estimated margin, potential loss and potential profit.

## Install and run (no terminal needed)

1. Install **Python 3.11 or newer** from python.org (tick *Add python.exe to PATH*).
2. Open the **`izakami`** project folder and double-click **`INSTALL_AND_RUN.bat`**.
   It creates a private `.venv` inside the folder, installs PySide6 and starts Izakami.
3. Next time double-click **`RUN_IZAKAMI.bat`**, or **`INSTALL_AND_RUN.vbs`** for a launch with no
   console window at all. If setup fails, see `install.log` in the same folder.

Setup first tries a private `.venv`. If that environment cannot start (for example the error
`failed to locate pyvenv.cfg`, seen with some Microsoft Store / Python install-manager builds), it
automatically falls back to installing PySide6 into a local `libs` folder instead. Either way the
launchers write a small `launch.cmd`. If you move the folder, the next launch rebuilds everything.

**If setup still fails:** delete the `.venv` and `libs` folders, run `INSTALL_AND_RUN.bat` again, and
look at `install.log` - it records which Python was used.

Your data (SQLite database, log) lives in `%APPDATA%\Izakami` - not in the program folder.

## Using it

| What | How |
|---|---|
| Direction | Automatic: Stop below Entry = LONG, above = SHORT, equal = error |
| Risk | `%` button switches between percentage of balance and a fixed amount |
| Take-profit | `Entry ± distance × RR`, rounded toward entry to the tick grid |
| Capture Entry | highlight a price anywhere, press **Ctrl+Shift+E** |
| Capture Stop Loss | highlight a price, press **Ctrl+Shift+S** |
| Copy size | **Ctrl+Shift+C** (or the button) copies only the number, e.g. `0.020` |
| Reset | clears Entry and Stop Loss |
| Up / Down keys | step the value in a focused field |

Shortcuts are configurable in Settings. A global shortcut takes that key combination away from other
programs (Ctrl+Shift+C opens developer tools in Chrome/Edge, for example) - change it if that bothers you.

### How capture works, and its limits
Izakami waits for you to release the shortcut keys, sends Ctrl+C to the active window, checks that the
clipboard really changed, validates that it holds a single positive number, and only then fills the
field. Otherwise the field is left untouched. Your previous clipboard text is restored afterwards
(Settings can turn that off).

**Many TradingView chart labels are drawn on a canvas and cannot be selected or copied.** Capture only
works where normal Windows copying works (text fields, tables, the order panel, etc.).

## Accuracy notes

* All money maths uses Python `Decimal`; position size is always rounded **down** to the quantity step.
* A size below the minimum, above the maximum, or below the minimum notional is shown as an **error**,
  never as a plausible-looking number.
* Estimated margin = position value ÷ leverage (or value × margin rate if the instrument sets one). It is
  an estimate; brokers differ.
* **Currency conversion:** the instrument's *Conversion rate* converts its P&L currency into your
  *account* currency. USD, USDT and USDC are treated as equal; anything else uses your manual rate and
  the result is flagged as an estimate. The starter presets contain placeholder rates (e.g. JPY, CAD,
  EUR) - **update them**, and re-check them if you change your account currency.
* **Starter instruments are examples, not broker data.** Verify contract size, steps and limits with
  your broker and edit them in Settings -> Manage instruments.

## Instrument models

* **Linear** - P&L per price unit = contract size (forex lots, CFDs, crypto, stocks).
* **Tick value** - P&L = ticks moved × tick value (futures). Contract size is then only used for the
  position value / margin estimate.

## Project layout

```
src/izakami/core       calculator, sizing models, currency conversion, validation (no Qt, no I/O)
src/izakami/models     Instrument, AccountSettings, CalculationResult
src/izakami/services   calculation, instruments, settings, hotkeys, clipboard capture
src/izakami/database   SQLite connection, versioned migrations, repositories, presets
src/izakami/platform   Windows hotkeys / clipboard / startup (ctypes) behind small interfaces
src/izakami/integrations  optional data-provider interface (no providers included)
src/izakami/ui         main window, settings, instrument manager, themes
tests/                 pytest suite
```

## Tests

```
INSTALL_AND_RUN.bat                       (once, to create .venv)
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

The tests cover the engine, database/migrations, instruments, shortcut parsing and the capture logic
(with a fake clipboard), and the GUI (headless Qt). The real Windows hotkey and clipboard code
(`platform/windows`) cannot run in that headless environment - test it on your PC (see below).

## Build a standalone .exe (optional)

Run `BUILD_EXE.bat` after the first install. It produces
`dist\IzakamiRiskCalculator\IzakamiRiskCalculator.exe` (a folder build: faster start, fewer antivirus
false positives). For a single file:

```
.venv\Scripts\python -m PyInstaller --noconfirm --clean --windowed --onefile --name IzakamiRiskCalculator --paths src run.py
```

Unsigned one-file executables are sometimes flagged by antivirus software; a code-signing certificate
fixes that. The `.bat` installation remains fully supported.

## Not included (by design)

Order execution, trade management, journaling, analytics, signals, copy trading, account sync.
Optional API integrations are architecture only: no providers ship, and nothing ever touches the network.
