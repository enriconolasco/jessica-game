# P0 — baseline técnica

## Estado registrado

- Projeto: `C:\Users\UsuarioPc\Downloads\jessica`
- Python: 3.12.14
- Comando: `python tests/run_all.py`
- Resultado: 238 aprovações, 0 falhas
- Duração observada: aproximadamente 2,89 segundos
- Branch principal: `main`
- Tag funcional: `v5.11.0`
- Tag da baseline: `baseline-v0.1`

O total histórico era 230. A baseline atual possui 238 porque o patch v5.11
adicionou oito testes sistêmicos.

## Auditoria

- Nenhum token, senha, chave privada ou arquivo de credenciais foi encontrado.
- Nenhum arquivo individual maior que 5 MB foi encontrado.
- `backups/` e `fixes/` foram preservados e versionados conforme o plano P0.
- Caches, ambientes virtuais, temporários e bundles locais são ignorados.
- Aviso conhecido: `tests/apply_fix_v5b2c.py` é um aplicador histórico com
  sintaxe inválida; `tests/run_all.py` não o trata como teste.

## Referências reproduzíveis

Seeds em `seeds/reference_seeds.json`:

- 20260916 — regressão histórica;
- 20260921 — sistemas v5.11;
- 51100 — saves da baseline.

Saves em `saves/reference/`:

- turno 6 intermediário;
- combate com Lua Cheia e feitiço;
- turno 12 próximo do encerramento.

Regeneração: `python tools/generate_reference_saves.py`.

## Fluxo obrigatório para patches

```text
alterar poucos itens
→ executar testes relevantes
→ executar a suíte completa quando necessário
→ revisar git diff
→ criar commit descritivo
```
