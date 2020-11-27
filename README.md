### Comandi per admin

```
- /r [sample rate]: rispondi ad un messaggio vocale per forzarne la trascrizione, possibile forzare un certo sample rate
- /ignoretos: se usato in una chat di gruppo, fa in modo che il bot ignori, in quella chat, le preferenze degli utenti e trascriva ogni messaggio vocale inviato
- /superuser: permette di fare in modo che un certo utente possa aggiungere il bot ai gruppi e inoltrare vocali da trascrivere senza che il mittente originario abbia accettato i ToS. In chat privata va usato in risposta ad un messaggio inoltrato. Nei gruppi va usato in risposta ad un messaggio (ignora il mittente originale dei messaggi inoltrati)
- inoltro messaggio (non vocale) di un utente in chat privata: mostra la riga nel database
```

### superusers/admins

- aggiunta del bot nei gruppi: entrambi
- trascrizione di qualsiasi vocale inoltrato in privato: entrambi

### transcription logic in groups (to-do)

- non-forwarded voice message: only if sender accepted tos
- forwarded voice message from user who hid their account: always
- forwarded voice message (forwarder: superuser or admin): check original sender's tos
- forwarded voice message (forwarder: normal user): check original sender's tos
