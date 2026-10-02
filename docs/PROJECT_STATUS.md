# Estado do projeto — 02/10/2026

- Versão compartilhada de playtest: `main`, `bd1df00`.
- Referência recuperável: tag `web-local-pre-online-2026-10-02`.
- Terminal/Hotseat: motor e atualizador consolidados; 454 testes Python,
  cinco testes Node e comparação independente de 125 ações/dez noites aprovados.
- Online: `codex/online-rooms`; API autenticada e lobby ligados ao cliente completo,
  sem handoff, identidade fixa e retorno após recarregar. WebSocket/reconexão
  implementados com fallback HTTP. Persistência SQLite implementada no servidor;
  dez testes de recuperação/durabilidade aprovados, incluindo reinício real.
  Suíte completa: 486 testes Python e seis testes Node aprovados.
  WebSocket verificado no navegador em duas abas,
  com escolha sincronizada e identidade/reconexão preservadas após recarregar.
  Nenhuma regra alterada; terminal/hotseat de referência permanecem na `main`.
- Acesso LAN opcional preparado (`JOGAR_REDE_LOCAL.cmd`), com bind/origem restritos
  e oito testes próprios aprovados. Nenhuma interface LAN/firewall ativada nesta entrega.
- Próxima integração: partida completa e interrupções em aparelhos físicos na mesma rede. Recuperação
  da credencial após fechar aba, pausa/abandono, backups automáticos e hospedagem pendentes.

Contratos/limites: [ONLINE_AUDITORIA.md](ONLINE_AUDITORIA.md).
Atualização comum: [FLUXO_ATUALIZACAO.md](FLUXO_ATUALIZACAO.md).
Roteiro de rede: [ONLINE_REDE_LOCAL.md](ONLINE_REDE_LOCAL.md).
