
# Feelo

Feelo is a wellness check-in tracker for the **Game Boy Advance**. No phone, no account, no keyboard.

Pick how you feel on a 2D mood pad in ~3 seconds. Feelo saves the result with a timestamp to cartridge SRAM, where it can stay for long-term analysis.

Built with the [Butano](https://github.com/GValiente/butano) engine. Runs in emulators (mGBA) and on real hardware (EZ-Flash Omega DE).

## How a check-in works

1. **Home.** The mascot's face mirrors your 7-day average mood and shows the clock and your streak. Press **A**.
2. **Mood pad.** Move the mascot with the D-pad on a 2D grid:
   - **left ↔ right:** how unpleasant ↔ pleasant you feel (valence)
   - **down ↕ up:** how drained ↔ wired you are (energy)

   The mascot's face changes as you move through 9 expressions: stressed, wired, pumped, down, okay, happy, drained, sleepy, and cozy. Press **A**.
3. **Focus (optional).** How clear-headed are you today, from LOCKED IN to LOST? Pick with ◀ ▶ and **A**, or skip with **B**.
4. **Logged!** The mascot celebrates. The record is already saved.

Press **SELECT** on the home screen to see stats on the device: totals, streak, 7/30-day averages, your best time of day, and a sparkline of the last 32 check-ins. For a deeper look, export the save file to CSV as described below.

Each record takes 8 bytes and stores a timestamp (from the cartridge real-time clock), valence −100…+100, energy −100…+100, and focus 0…200 (or skipped). Storage uses a crash-safe ring buffer with ~4088 records, enough for 11+ years of daily check-ins. The full format is documented in [docs/DATA_FORMAT.md](docs/DATA_FORMAT.md).

## Building

Prerequisites for macOS or Linux (Wonderful Toolchain does not require sudo):

1. **Toolchain.** Choose one:
   - [Wonderful Toolchain](https://wonderful.asie.pl/docs/getting-started/):
     ```sh
     curl -L https://wonderful.asie.pl/bootstrap/wf-bootstrap-darwin-aarch64.tar.gz | tar xz -C ~/wonderful
     export WONDERFUL_TOOLCHAIN=~/wonderful PATH="$HOME/wonderful/bin:$PATH"
     wf-pacman -Syu --noconfirm wf-tools
     wf-config repo enable blocksds
     wf-pacman -Syu --noconfirm
     wf-pacman -S --noconfirm target-gba blocksds-toolchain
     ```
     *(pick the bootstrap tarball matching your OS/arch)*

     **If installed anywhere other than `/opt/wonderful`** (as above), two kinds of hardcoded paths need patching. See [docs/WONDERFUL_USER_INSTALL.md](docs/WONDERFUL_USER_INSTALL.md).
   - Or use [devkitPro](https://devkitpro.org/wiki/Getting_Started) with the `gba-dev` package group (`sudo dkp-pacman -S gba-dev`), then export `DEVKITARM=/opt/devkitpro/devkitARM`.
2. **Butano.** It is pinned as a git submodule:
   ```sh
   git submodule update --init
   ```
3. **Python 3 + Pillow** for the asset pipeline:
   ```sh
   python3 -m venv .venv && .venv/bin/pip install pillow
   ```

Then run:

```sh
.venv/bin/python tools/gen_assets.py   # regenerate pixel art + SFX (committed output)
make -j8                               # produces feelo.gba
```

## Running in mGBA

```sh
brew install --cask mgba-app   # or: brew install mgba
```

mGBA does **not** enable the real-time clock for homebrew by default. You can enable it in the GUI: load `feelo.gba`, open *Tools → Game overrides…*, uncheck *Autodetect*, check *Real-time clock*, set the save type to *SRAM*, and restart the game.

You can also add this block to mGBA's `config.ini` before the first launch:

```ini
[override.2FLO]
savetype=SRAM
hardware=1
```

Config locations are `~/.config/mgba/config.ini` for the Homebrew formula build and `~/Library/Application Support/mGBA/config.ini` for the official/cask app. Without the override, Feelo still works; the check-ins are simply undated.

mGBA writes SRAM to `feelo.sav` next to the ROM.

## Running on an EZ-Flash Omega DE

1. Copy `feelo.gba` to the microSD card.
2. In the Omega menu, make sure the global **GAME RTC** setting is **ON** (System settings) and the save type resolves to **SRAM** (AUTO works).
3. Launch Feelo and check that the home screen shows the correct time. Make a check-in, power-cycle the device, and confirm that the entry survived.

The cart writes a `.sav` file to the microSD in the same format as mGBA. `tools/parse_save.py` reads both.

## Analyzing your data

```sh
python3 tools/parse_save.py feelo.sav              # summary report
python3 tools/parse_save.py feelo.sav --csv out.csv
```

The summary includes averages, mood distribution, and valence by time of day and weekday. The CSV gives you one row per check-in with an ISO timestamp, weekday, valence, energy, focus, and mood zone.

## Development

- `tools/gen_assets.py` generates all pixel art and SFX deterministically with Pillow. Previews land in `build/`.
- `tests/host_test.cpp` tests the storage engine against a RAM-backed SRAM shim, including corruption recovery and ring wrap. It also dumps a `.sav` that cross-checks `tools/parse_save.py`:
  ```sh
  c++ -std=c++20 -Itests/shim -Iinclude tests/host_test.cpp src/fl_storage.cpp -o build/host_test
  ./build/host_test build/test.sav
  .venv/bin/python tools/parse_save.py build/test.sav
  ```
- Boot logs (`BN_LOG`) are available in mGBA's log viewer and log file.

## License

zlib. See [LICENSE](LICENSE). Butano and its example fonts are also zlib.
