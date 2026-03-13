Preciso corrigir dois bugs no restore.py do bspwm-layout-manager:

─── BUG 1 — regra temporária não sobrescreve a permanente ───────────────────

_apply_desktop_rule adiciona desktop=N mas não remove as regras permanentes
antes. O bspwm aplica todas as regras que existem para aquela classe, então
a permanente (desktop=^3) prevalece sobre a temporária (desktop=4).

SOLUÇÃO: em _apply_desktop_rule, REMOVER as regras existentes antes de
aplicar a temporária:

    existing = _get_existing_rules(win_class)
    run(["bspc", "rule", "-r", win_class])   # remove todas primeiro
    run(["bspc", "rule", "-a", win_class, f"desktop={desktop}"])
    return existing

─── BUG 2 — programas com state=floating na regra permanente ────────────────

Programas como Thunar têm: Thunar:*:* => desktop=^3 state=floating
Mesmo forçando a desktop correta, o state=floating ainda é aplicado.

Ao restaurar uma janela que foi salva como TILED (win não está em
floating_windows, está em windows), a regra temporária deve incluir
state=tiled para sobrescrever o floating permanente:

    run(["bspc", "rule", "-a", win_class, f"desktop={desktop}", "state=tiled"])

Ao restaurar uma janela que foi salva como FLOATING (está em
floating_windows), manter state=floating na regra temporária:

    run(["bspc", "rule", "-a", win_class, f"desktop={desktop}", "state=floating"])

Então _apply_desktop_rule precisa de um parâmetro extra:
    def _apply_desktop_rule(win_class: str, desktop: int, state: str = "") -> list[tuple[str, str]]:
    
Onde state pode ser "tiled", "floating" ou "" (sem forçar state).

─── ARQUIVO ATUAL ────────────────────────────────────────────────────────────

restore.py: /home/samuelh/Documentos/projects/bspwm-layout-manager/bspwm_layout_manager/restore.py

Entregue o arquivo completo corrigido.
