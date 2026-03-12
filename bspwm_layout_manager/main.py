#!/usr/bin/env python3
"""
blm - bspwm Layout Manager
Save and restore your bspwm desktop layouts.

Usage:
  blm save <name>     Save the current desktop layout
  blm load <name>     Restore a saved layout
  blm list            List all saved layouts
  blm delete <name>   Delete a saved layout
  blm menu            Open the rofi menu (for sxhkd)
  blm info <name>     Show details about a layout
"""

import sys
from bspwm_layout_manager import storage, capture, restore, rofi as rofi_ui


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_save(name: str):
    print(f"Capturing current desktop layout...")
    layout = capture.capture_current_desktop()

    n = len(layout["windows"])
    if n == 0:
        print("No open windows found on current desktop.")
        sys.exit(1)

    storage.save_layout(name, layout)
    print(f"✓ Layout '{name}' saved with {n} window(s).")
    print(f"  Windows:")
    for w in layout["windows"]:
        print(f"    [{w['class']}] {w['cwd']}")


def cmd_load(name: str):
    layout = storage.get_layout(name)
    if not layout:
        print(f"Layout '{name}' not found.")
        print(f"Available: {', '.join(storage.list_layouts()) or 'none'}")
        sys.exit(1)

    n = len(layout.get("windows", []))
    print(f"Restoring layout '{name}' ({n} windows)...")
    restore.restore_layout(layout)
    print(f"✓ Done.")


def cmd_list():
    layouts = storage.load_all()
    if not layouts:
        print("No layouts saved yet.")
        print("Use: blm save <name>")
        return

    print(f"{'NAME':<25} {'WINDOWS':<10} {'SAVED AT'}")
    print("─" * 55)
    for name, layout in layouts.items():
        n = len(layout.get("windows", []))
        saved_at = layout.get("saved_at", "")[:16].replace("T", " ")
        print(f"{name:<25} {n:<10} {saved_at}")


def cmd_delete(name: str):
    if not storage.delete_layout(name):
        print(f"Layout '{name}' not found.")
        sys.exit(1)
    print(f"✓ Layout '{name}' deleted.")


def cmd_info(name: str):
    layout = storage.get_layout(name)
    if not layout:
        print(f"Layout '{name}' not found.")
        sys.exit(1)

    print(f"Layout: {name}")
    print(f"Desktop: {layout.get('desktop', '?')}")
    print(f"Saved at: {layout.get('saved_at', '?')[:16].replace('T', ' ')}")
    print(f"Windows ({len(layout.get('windows', []))}):")
    for w in layout.get("windows", []):
        print(f"  [{w['class']}]")
        print(f"    Directory : {w['cwd']}")
        print(f"    Command   : {w['command'][:60]}")


def cmd_menu():
    """Opens the rofi menu for interactive layout management."""
    layouts = storage.load_all()

    ACTIONS = {
        "load":   "▶  Load layout",
        "save":   "＋  Save current layout",
        "delete": "✕  Delete layout",
    }

    action_label = rofi_ui.rofi_menu(
        list(ACTIONS.values()),
        prompt="blm",
        message="bspwm Layout Manager"
    )

    if not action_label:
        return

    # Map label back to action key
    action = next((k for k, v in ACTIONS.items() if v == action_label), None)

    if action == "load":
        if not layouts:
            rofi_ui.rofi_error("No layouts saved yet.\nUse: blm save <name>")
            return
        items = rofi_ui.format_layout_list(layouts)
        selection = rofi_ui.rofi_menu(items, prompt="Load layout")
        if selection:
            name = rofi_ui.parse_selection(selection)
            layout = storage.get_layout(name)
            restore.restore_layout(layout)
            rofi_ui.rofi_notify(f"Layout '{name}' restored!")

    elif action == "save":
        name = rofi_ui.rofi_input("Layout name")
        if name:
            layout = capture.capture_current_desktop()
            storage.save_layout(name, layout)
            n = len(layout["windows"])
            rofi_ui.rofi_notify(f"Layout '{name}' saved! ({n} windows)")

    elif action == "delete":
        if not layouts:
            rofi_ui.rofi_error("No layouts saved yet.")
            return
        items = rofi_ui.format_layout_list(layouts)
        selection = rofi_ui.rofi_menu(items, prompt="Delete layout")
        if selection:
            name = rofi_ui.parse_selection(selection)
            if rofi_ui.rofi_confirm(f"Delete '{name}'?"):
                storage.delete_layout(name)
                rofi_ui.rofi_notify(f"Layout '{name}' deleted.")


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "save":
        if len(args) < 2:
            print("Usage: blm save <name>")
            sys.exit(1)
        cmd_save(args[1])

    elif cmd == "load":
        if len(args) < 2:
            print("Usage: blm load <name>")
            sys.exit(1)
        cmd_load(args[1])

    elif cmd == "list":
        cmd_list()

    elif cmd == "delete":
        if len(args) < 2:
            print("Usage: blm delete <name>")
            sys.exit(1)
        cmd_delete(args[1])

    elif cmd == "info":
        if len(args) < 2:
            print("Usage: blm info <name>")
            sys.exit(1)
        cmd_info(args[1])

    elif cmd == "menu":
        cmd_menu()

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
