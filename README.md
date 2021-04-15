### Comandi per admin

```
- /r [sample rate]: rispondi ad un messaggio vocale per forzarne la trascrizione, possibile forzare un certo sample rate
- /parse: rispondi ad un messaggio vocale per ottenerne le info di base, non esegue la trascrizione
- /mediainfo: output mediainfo
- /superuser: permette di fare in modo che un certo utente possa aggiungere il bot ai gruppi. In chat privata va usato in risposta ad un messaggio inoltrato. Nei gruppi va usato in risposta ad un messaggio (ignora il mittente originale dei messaggi inoltrati)
- inoltro messaggio (non vocale) di un utente in chat privata: mostra la riga nel database
```

### superusers/admins

- aggiunta del bot nei gruppi: entrambi

### trascrizione nei gruppi

I vocali nei gruppi **non** vengono trascritti se:

- la chat è disabilitata
- il vocale non è inoltrato, ed il mittente ha richiesto l'opt-out
- il vocale è inoltrato, ed il mittente originale non ha nascosto il proprio account e ha richiesto l'opt-out
