import logging

from sqlalchemy.orm import Session
# noinspection PyPackageRequirements
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    Filters, CallbackQueryHandler
)
# noinspection PyPackageRequirements
from telegram import (
    ChatAction,
    Update, ParseMode
)

from bot import sttbot
from bot.markups import InlineKeyboard
from bot.database.models.user import User
from bot.decorators import decorators
from config import config

logger = logging.getLogger(__name__)

TOS_ACCEPT = """Questo è un disclaimer affinchè l'utente possa prendere \
coscienza di come questo bot elabora, gestisce e condivide i dati necessari al suo funzionamento.
Al termine della lettura, sarà necessario acconsentire al trattamento dei propri dati affinchè il bot possa fornire \
il propro servizio. I messaggi vocali degli utenti che non hanno acconsentito al trattamento dei dati verranno ignorati.

<b>Dati identificativi dell'utente Telegram</b>
Il bot salva l'ID univoco degli utenti telegram che lo avviano, o che incontra nelle chat di gruppo, al \
fine di verificare la presa visione/accettazione di questo disclaimer e di salvare alcune impostazioni \
associate all'utente (ad esempio: whitelist di utenti che possono aggiungere il bot ai gruppi).

<b>Memorizzazione dei file audio salvati per la trascrizione</b>
Il bot scarica da Telegram i messaggi vocali che riceve solo nel caso in cui il mittente originale del messaggio \
abbia acconsentito al trattamento dei propri dati. I file audio vengono rimossi non \
appena il processo di trascrizione è terminato. <b>Non</b> vengono rimossi i file audio che generano un errore.

<b>Condivizione dei file audio da trascrivere con Google</b> 
Questo bot utilizza <a href="https://cloud.google.com/speech-to-text/">l'API di Google per la trascrizione vocale</a>. \
Tutti i messaggi vocali trascritti da questo bot vengono inviati in forma anonima ai servizi di Google, \
affinchè possano essere processati e trascritti. Il bot non fornisce a Google nessuna informazione sul mittente \
originale di un singolo vocale da trascrivere - inoltre, \
<a href="https://cloud.google.com/speech-to-text/docs/data-logging">in base a quanto scritto nella \
documentazione</a>, l'API non logga nè gli audio che riceve nè le trascrizioni che genera. Tuttavia, \
nel caso in cui ciò non fosse vero vero, sulla carta Google potrebbe utilizzare dati già in suo possesso per \
identificare più o meno precisamente le persone fisiche la cui voce compare nei file audio.

Utilizzando il tasto "accetta" qui sotto si conferma di aver letto e compreso questo disclaimer, e si acconsente alla \
manipolazione dei dati così come descritto. Sarà possibile revocare il proprio consenso utilizzando il comando /tos"""

TOS_REVOKE = """<b>Termini di Servizio, TL;DR:</b>
- il bot salva il tuo ID utente Telegram (per memorizzare il consenso al trattamento dei tuoi dati)
- il bot scarica i file vocali il cui mittente ha fornito il proprio consenso al trattamento dati, per poi \
eliminarli non appena il processo di trascrizione viene completato
- il bot utilizza un'API di Google per la trascrizione, quindi i file audio vengono inviati in forma anonima a Goolge

Per revocare il tuo consenso, usa il tasto qui sotto"""


@decorators.failwithmessage
@decorators.pass_session(pass_user=True)
def on_tos_command(update: Update, _, session: [Session, None], user: [User, None]):
    logger.info('/tos')

    if not user.tos_accepted:
        update.message.reply_html(TOS_ACCEPT, reply_markup=InlineKeyboard.TOS_AGREE, disable_web_page_preview=True)
    else:
        update.message.reply_html(TOS_REVOKE, reply_markup=InlineKeyboard.TOS_REVOKE, disable_web_page_preview=True)


@decorators.failwithmessage
def on_tos_show_button(update: Update, _):
    logger.info('show tos button')

    update.callback_query.message.edit_text(
        TOS_ACCEPT,
        reply_markup=InlineKeyboard.TOS_AGREE,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )


@decorators.failwithmessage
@decorators.pass_session(pass_user=True)
def on_tos_agree_button(update: Update, _, session: [Session, None], user: [User, None]):
    logger.info('agree tos button')

    user.tos_accepted = True

    update.callback_query.message.edit_text(
        "Ottimo, adesso il bot potrà trascrivere i tuoi messaggi vocali. "
        "Ricordati che puoi usare /tos per revocare il tuo consenso",
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )


@decorators.failwithmessage
@decorators.pass_session(pass_user=True)
def on_tos_revoke_button(update: Update, _, session: [Session, None], user: [User, None]):
    logger.info('revoke tos button')

    user.revoke_tos()

    update.callback_query.message.edit_text(
        "Consenso revocato. D'ora in avanti il bot ignorerà i tuoi messaggi vocali",
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )


sttbot.add_handler(CommandHandler('tos', on_tos_command, filters=Filters.private))
sttbot.add_handler(CallbackQueryHandler(on_tos_show_button, pattern=r"tos:show"))
sttbot.add_handler(CallbackQueryHandler(on_tos_agree_button, pattern=r"tos:agree"))
sttbot.add_handler(CallbackQueryHandler(on_tos_revoke_button, pattern=r"tos:revoke"))
