# Feelo

A wellness check-in tracker for the **Game Boy Advance**. No phone, no
account, no keyboard — pick how you feel on a 2D mood pad in ~3 seconds,
and Feelo logs it with a timestamp to cartridge SRAM for long-term analysis.

Built with the [Butano](https://github.com/GValiente/butano) engine.
Runs in emulators (mGBA) and on real hardware (EZ-Flash Omega DE).

## How a check-in works

1. **Home** — the mascot's face mirrors your 7-day average mood; shows the
   clock and your streak. Press **A**.
2. **Mood pad** — move the mascot with the D-pad on a 2D grid:
   - **left ↔ right**: how unpleasant ↔ pleasant you feel (valence)
   - **down ↕ up**: how drained ↔ wired you are (energy)

   The mascot's face morphs as you move (9 expressions: stressed, wired,
   pumped, down, okay, happy, drained, sleepy, cozy). Press **A**.
3. **Focus** *(optional)* — how clear-headed are you today, from LOCKED IN
   to LOST? Pick with ◀ ▶ and **A**, or skip with **B**.
4. **Logged!** — the mascot celebrates; the record is already saved.

Press **SELECT** on the home screen for on-device stats: totals, streak,
7/30-day averages, your best time of day, and a sparkline of the last 32
check-ins. For deeper analysis, export the save file to CSV (below).

Each record stores: timestamp (from the cartridge real-time clock),
valence −100…+100, energy −100…+100, focus 0…200 (or skipped) — 8 bytes,
~4088 records (11+ years daily) in a crash-safe ring buffer. Full spec:
[docs/DATA_FORMAT.md](docs/DATA_FORMAT.md).

## Building

Prerequisites (macOS/Linux; no sudo needed with Wonderful Toolchain):

1. **Toolchain** — either:
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

     **If installed anywhere other than `/opt/wonderful`** (as above), two
     kinds of hardcoded paths need patching — see
     [docs/WONDERFUL_USER_INSTALL.md](docs/WONDERFUL_USER_INSTALL.md).
   - or [devkitPro](https://devkitpro.org/wiki/Getting_Started) with the
     `gba-dev` package group (`sudo dkp-pacman -S gba-dev`), then export
     `DEVKITARM=/opt/devkitpro/devkitARM`.
2. **Butano** — pinned as a git submodule:
   ```sh
   git submodule update --init
   ```
3. **Python 3 + Pillow** (asset pipeline):
   ```sh
   python3 -m venv .venv && .venv/bin/pip install pillow
   ```

Then:

```sh
.venv/bin/python tools/gen_assets.py   # regenerate pixel art + SFX (committed output)
make -j8                               # produces feelo.gba
```

## Running in mGBA

```sh
brew install --cask mgba-app   # or: brew install mgba
```

mGBA does **not** enable the real-time clock for homebrew by default. Either
use the GUI (load `feelo.gba`, then *Tools → Game overrides…*: uncheck
Autodetect, check *Real-time clock*, set save type *SRAM*, restart the game)
or drop this into mGBA's `config.ini` before first launch:

```ini
[override.2FLO]
savetype=SRAM
hardware=1
```

Config locations: `~/.config/mgba/config.ini` (Homebrew formula build) or
`~/Library/Application Support/mGBA/config.ini` (official/cask app).
Without the override the app still works — check-ins are just undated.

mGBA writes the SRAM to `feelo.sav` next to the ROM.

## Running on an EZ-Flash Omega DE

1. Copy `feelo.gba` to the microSD card.
2. In the Omega menu, make sure the global **GAME RTC** setting is **ON**
   (System settings) and the save type resolves to **SRAM** (AUTO works).
3. Launch. Verify the home screen shows the correct clock, make a check-in,
   power-cycle, and confirm it survived.

The `.sav` the cart writes to the microSD is the same format mGBA writes —
`tools/parse_save.py` reads both.

## Analyzing your data

```sh
python3 tools/parse_save.py feelo.sav              # summary report
python3 tools/parse_save.py feelo.sav --csv out.csv
```

The summary includes averages, mood distribution, valence by time of day
and by weekday. The CSV has one row per check-in (ISO timestamp, weekday,
valence, energy, focus, mood zone) for any further analysis you like.

## Development

- `tools/gen_assets.py` — all pixel art and SFX are generated
  deterministically from this script (Pillow); previews land in `build/`.
- `tests/host_test.cpp` — host-side test of the storage engine against a
  RAM-backed SRAM shim, including corruption recovery and ring wrap; it
  also dumps a `.sav` that cross-checks `tools/parse_save.py`:
  ```sh
  c++ -std=c++20 -Itests/shim -Iinclude tests/host_test.cpp src/fl_storage.cpp -o build/host_test
  ./build/host_test build/test.sav
  .venv/bin/python tools/parse_save.py build/test.sav
  ```
- Boot logs (`BN_LOG`) are visible in mGBA's log viewer / log file.

## License

zlib — see [LICENSE](LICENSE). Butano and its example fonts are zlib as well.
