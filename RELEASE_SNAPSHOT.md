# Jéssica v5.11.0 — mecânicas estáveis

- Data: 2026-09-21
- Testes: 238 passaram, 0 falharam
- Escopo: motor, povos, heróis, feitiços, artefatos, combate e serialização
- Tag Git: `v5.11.0`
- Excluídos do histórico: `backups/`, `fixes/` e caches gerados

## Recuperação segura

Inspecionar a versão congelada sem alterar a versão atual:

```text
git switch --detach v5.11.0
```

Continuar trabalho a partir dela em outra ramificação:

```text
git switch -c restauracao-v5.11 v5.11.0
```

Restaurar o repositório usando o bundle independente:

```text
git clone releases/jessica-v5.11.0.bundle jessica-restaurada
```

