# Estado do projeto — 02/10/2026

- Versão compartilhada de playtest: `main`, `bd1df00`.
- Referência recuperável: tag `web-local-pre-online-2026-10-02`.
- Terminal/Hotseat: motor e atualizador consolidados; 454 testes Python,
  cinco testes Node e comparação independente de 125 ações/dez noites aprovados.
- Online: `codex/online-rooms`; API autenticada e lobby ligados ao cliente completo,
  sem handoff, identidade fixa e retorno após recarregar. WebSocket/reconexão
  implementados com fallback HTTP. 468 testes Python (nove HTTP/cinco WebSocket)
  e seis testes Node aprovados. WebSocket verificado no navegador em duas abas,
  com escolha sincronizada e identidade/reconexão preservadas após recarregar.
  Nenhuma regra alterada; terminal/hotseat de referência permanecem na `main`.
- Próxima integração: persistência no servidor e testes de interrupção em aparelhos. Recuperação
  após fechar aba, testes móveis/aparelhos físicos, Wi-Fi e hospedagem pendentes.

Contratos/limites: [ONLINE_AUDITORIA.md](ONLINE_AUDITORIA.md).
Atualização comum: [FLUXO_ATUALIZACAO.md](FLUXO_ATUALIZACAO.md).
