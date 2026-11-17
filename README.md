# Izakami Risk Calculator

A lightweight, offline-first position-size calculator with a floating desktop interface. Izakami calculates position size, trade direction, take-profit, position value, estimated margin, potential loss and potential profit from your account settings and Entry / Stop Loss prices.

The application source code is in the **[`izakami/`](./izakami)** folder.

## Features

- Risk-based position sizing using percentage risk or a fixed risk amount.
- Automatic LONG / SHORT direction from Entry and Stop Loss.
- Risk-to-reward take-profit calculation.
- Editable instruments and contract specifications.
- Estimated margin and leverage information.
- Light and dark themes.
- Global shortcuts for capturing Entry and Stop Loss prices and copying position size.
- Offline-first operation; no account or API key required.

## Run on Windows

1. Install **Python 3.11 or newer** from [python.org](https://www.python.org/). During setup, enable **Add python.exe to PATH**.
2. Open the **[`izakami/`](./izakami)** folder.
3. Double-click **`INSTALL_AND_RUN.bat`**. It prepares the local environment, installs the required dependencies and launches Izakami.
4. For later launches, use **`RUN_IZAKAMI.bat`**. You can also use **`INSTALL_AND_RUN.vbs`** to launch without a console window.

If setup fails, check `install.log` in the `izakami/` folder. See the [project README](./izakami/README.md) for troubleshooting and additional details.

## Build a standalone Windows executable

After setting up the project, run **`BUILD_EXE.bat`** from the `izakami/` folder. The build output is:

```
izakami/dist/IzakamiRiskCalculator/IzakamiRiskCalculator.exe
```

This is a portable folder build. The project README also includes an optional one-file PyInstaller command.

## Accuracy and trading risk

Instrument presets are examples, not broker-provided specifications. Before using a result, verify each instrument's contract size, tick value, quantity step, limits, leverage and margin rules with your broker. Estimated margin may differ from the amount your broker actually requires.

Izakami is a calculator only. It does not place orders or connect to a broker.

## Development

Source code, tests, setup scripts and detailed technical documentation are in [`izakami/`](./izakami).