# bspwm Layout Manager (blm)

Save and restore your bspwm desktop layouts — with a rofi menu.

## What it does

- **Saves** the current desktop state: open windows, working directories, split ratios
- **Restores** layouts with a single command or keypress
- **Rofi menu** for quick access: `Super + l`

## Dependencies

- `bspwm`
- `rofi`
- `xorg-xprop`
- `python >= 3.10`

## Installation

### Arch Linux / Archcraft (AUR)
```bash
yay -S bspwm-layout-manager
```

### Manual (pipx — recommended)
```bash
git clone https://github.com/samuelh/bspwm-layout-manager
cd bspwm-layout-manager
pipx install .
```

### Manual (pip)
```bash
git clone https://github.com/samuelh/bspwm-layout-manager
cd bspwm-layout-manager
pip install . --break-system-packages
```

## Usage

```bash
# Save the current desktop layout
blm save my-project

# Restore a saved layout
blm load my-project

# List all saved layouts
blm list

# Delete a layout
blm delete my-project

# Show layout details
blm info my-project

# Open rofi menu
blm menu
```

## Rofi menu (recommended)

Add to your `~/.config/sxhkd/sxhkdrc`:

```
super + l
    blm menu
```

Then reload sxhkd:
```bash
pkill -USR1 sxhkd
```

Now `Super + L` opens:

```
▶  Load layout
＋  Save current layout
✕  Delete layout
```

## How it works

1. `blm save` reads the bspwm tree with `bspc query -T -d`, collects each window's
   PID via `xprop`, then reads `/proc/{pid}/cwd` and `/proc/{pid}/cmdline`
   to capture working directories and running commands.

2. Layouts are stored as JSON in `~/.config/bspwm-layout-manager/layouts.json`.

3. `blm load` launches each app in the correct directory and uses
   `bspc node -p` to reproduce the original split structure.

## Supported terminals

- Alacritty
- Kitty
- Foot
- WezTerm
- URxvt / XTerm / st

## Limitations

- **Floating windows** are not restored (only tiled windows)
- **Terminal content** (history, scrollback) is not restored — only the working
  directory and the foreground command (e.g. `nvim`, `npm run dev`)
- Applications that don't expose their PID via `_NET_WM_PID` may not restore correctly

## License

MIT
