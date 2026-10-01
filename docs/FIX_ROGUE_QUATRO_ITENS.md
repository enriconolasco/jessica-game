# Rogue: seleção de Bases com quatro itens — 01/10/2026

O combate já autorizava Rogue com Capa, Adaga, Relógio e Bracelete a atacar
Bases, mas `main.find_targets` não oferecia o alvo. Corrigido o seletor usando
`core.peoples.rogue_can_attack_base`, também reutilizado por `core.combat`.
Nenhum custo, dano, recompensa ou regra de balanceamento mudou.

Regressão: `python -B tests/test_rogue_four_items.py`; quatro itens permitem
selecionar/atacar a Base, enquanto qualquer item ausente continua impedindo.
Suíte terminal: **306 testes aprovados, zero falhas**.
