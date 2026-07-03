# Wonderful Toolchain in a user directory (no sudo)

Wonderful Toolchain officially lives at `/opt/wonderful`. It *can* run from
a user directory (e.g. `~/wonderful`, set `WONDERFUL_TOOLCHAIN` accordingly),
but two kinds of paths inside the distribution are hardcoded to
`/opt/wonderful` and must be patched after installing packages:

## 1. Script shebangs

Package scripts in `bin/` start with `#!/opt/wonderful/bin/wf-lua`:

```sh
cd "$WONDERFUL_TOOLCHAIN"
grep -rl '^#!/opt/wonderful' bin thirdparty 2>/dev/null | while read -r f; do
    sed -i '' "1s|#!/opt/wonderful|#!$WONDERFUL_TOOLCHAIN|" "$f"
done
```

(While bootstrapping, `wf-config` itself may fail with "bad interpreter";
run it through the interpreter explicitly:
`"$WONDERFUL_TOOLCHAIN/bin/wf-lua" "$WONDERFUL_TOOLCHAIN/bin/wf-config" repo enable blocksds`.)

## 2. macOS dylib load paths

The GCC binaries reference `/opt/wonderful/lib/libzstd.1.dylib` in their
Mach-O load commands; without patching, `cc1` aborts with
`Library not loaded: /opt/wonderful/lib/libzstd.1.dylib`. Rewrite the load
commands and re-sign (ad-hoc):

```sh
find "$WONDERFUL_TOOLCHAIN" -type f \( -perm -u+x -o -name '*.dylib' \) -print0 |
while IFS= read -r -d '' f; do
    deps=$(otool -L "$f" 2>/dev/null | awk '/\/opt\/wonderful\//{print $1}') || continue
    [ -z "$deps" ] && continue
    args=()
    for d in $deps; do
        args+=(-change "$d" "${d/\/opt\/wonderful/$WONDERFUL_TOOLCHAIN}")
    done
    install_name_tool "${args[@]}" "$f" && codesign -f -s - "$f"
done
```

Re-run both patches after `wf-pacman` installs or upgrades packages.

Alternatively, if you can use sudo once, a symlink avoids all of this:

```sh
sudo ln -s "$WONDERFUL_TOOLCHAIN" /opt/wonderful
```
