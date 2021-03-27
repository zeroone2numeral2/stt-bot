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
from bot.utilities import utilities
from config import config

logger = logging.getLogger(__name__)

DISCLAIMER_TEXT = """Questo è un disclaimer affinchè tu possa prendere \
coscienza di come questo bot elabora, gestisce e condivide i dati necessari al suo funzionamento.
Se lo desideri, puoi utilizzare il comando /optout per fare in modo che il bot ignori i tuoi messaggi vocali, \
anche quando vengono inoltrati da altri utenti. Potrai comunque continuare ad utilizzare il bot. \
I messaggi vocali inviati da te in questa chat verranno comunque trascritti.

<b>Dati identificativi dell'utente Telegram</b>
Il bot salva l'ID univoco degli utenti telegram che lo avviano, o che incontra nelle chat di gruppo, al \
fine di verificare il numero di utenti che lo utilizzano e di salvare alcune impostazioni \
associate all'utente (ad esempio: whitelist di utenti che possono aggiungere il bot ai gruppi).

<b>Memorizzazione dei file audio salvati per la trascrizione</b>
Il bot scarica da Telegram i messaggi vocali che riceve affinchè possano essere trascritti, a meno che il mittente \
del vocale non abbia deciso di farsi ignorare utilizzando il comando /optout. I file audio vengono rimossi non \
appena il processo di trascrizione è terminato. <b>Non</b> vengono rimossi i file audio che generano un errore.

<b>Condivizione dei file audio da trascrivere con Google</b> 
Questo bot utilizza <a href="https://cloud.google.com/speech-to-text/">l'API di Google per la trascrizione vocale</a>. \
Tutti i messaggi vocali trascritti da questo bot vengono inviati in forma anonima ai servizi di Google, \
affinchè possano essere processati e trascritti. Il bot non fornisce a Google nessuna informazione sul mittente \
originale di un singolo vocale da trascrivere - inoltre, \
<a href="https://cloud.google.com/speech-to-text/docs/data-logging">in base a quanto scritto nella \
documentazione</a>, l'API non logga nè gli audio che riceve nè le trascrizioni che genera. Tuttavia, \
nel caso in cui ciò non fosse vero, sulla carta Google potrebbe utilizzare dati già in suo possesso per \
identificare più o meno precisamente le persone fisiche la cui voce compare nei file audio.

Ricordo nuovamente che puoi utilizzare /optout (oppure il tasto qui sotto) \
se desideri che i tuoi messaggi vocali non vengano trattati"""

OPTOUT_TEXT = """D'ora in avanti ignorerò i vocali che invii nei gruppi ed i tuoi vocali che altri utenti inoltrano.

<b>Nota riguardo i messaggi inoltrati:</b> se le tue impostazioni della privacy sui messaggi inoltrati \
sono più restrittive del normale (ovvero <i>"i miei contatti"</i> o <i>"nessuno"</i>, nel menu <i>"Privacy e sicurezza" -> \
"Messaggi inoltrati"</i>) ed altri utenti al di fuori di questi due insiemi inoltrano i tuoi vocali, \
non potrò sapere che tu sei il mittente originale del messaggio vocale - di conseguenza verrà trascritto

Se ci ripensi, usa /optin"""

OPTOUT_DEEPLINK_TEXT = """Se desideri che il bot ignori i tuoi messaggi vocali \
(anche quando vengono inoltrati da altri utenti), usa il tasto qui sotto. \
Potrai comunque continuare ad utilizzare il bot. \
I messaggi vocali inviati da te in questa chat verranno comunque trascritti.

Nel caso in cui cambiassi idea in futuro, puoi utilizzare il comando /optin"""

OPTIN_TEXT = """Ok, non ignorerò più i tuoi vocali. Se ci ripensi, usa /optout"""


@decorators.catchexceptions()
def on_disclaimer_command(update: Update, _):
    logger.info('/disclaimer')

    update.message.reply_html(
        DISCLAIMER_TEXT,
        reply_markup=InlineKeyboard.OPTOUT,
        disable_web_page_preview=True
    )


@decorators.catchexceptions()
@decorators.pass_session(pass_user=True)
def on_optout_command(update: Update, _, session: [Session, None], user: [User, None]):
    logger.info('/optout')

    user.opt_out()

    update.message.reply_html(
        OPTOUT_TEXT,
        reply_markup=InlineKeyboard.DISCLAIMER_SHOW,
        disable_web_page_preview=True
    )


@decorators.catchexceptions()
def on_optout_deeplink(update: Update, _):
    logger.info('optout deeplink')

    update.message.reply_html(
        OPTOUT_DEEPLINK_TEXT,
        reply_markup=utilities.combine_inline_keyboards(InlineKeyboard.DISCLAIMER_SHOW, InlineKeyboard.OPTOUT),
        disable_web_page_preview=True
    )


@decorators.catchexceptions()
@decorators.pass_session(pass_user=True)
def on_optin_command(update: Update, _, session: [Session, None], user: [User, None]):
    logger.info('/optin')

    user.opted_out = False

    update.message.reply_html(
        OPTIN_TEXT,
        reply_markup=InlineKeyboard.DISCLAIMER_SHOW,
        disable_web_page_preview=True
    )


@decorators.catchexceptions()
@decorators.pass_session(pass_user=True)
def on_opt_command(update: Update, _, session: [Session, None], user: [User, None]):
    logger.info('/opt')

    update.message.reply_html("Opted-in" if not user.opted_out else "Opted-out")


@decorators.catchexceptions()
def on_disclaimer_show_button(update: Update, _):
    logger.info('show disclaimer button')

    update.callback_query.message.edit_text(
        DISCLAIMER_TEXT,
        reply_markup=InlineKeyboard.OPTOUT,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )


@decorators.catchexceptions()
@decorators.pass_session(pass_user=True)
def on_optout_button(update: Update, _, session: [Session, None], user: [User, None]):
    logger.info('optout button')

    user.opt_out()

    update.callback_query.message.edit_text(
        OPTOUT_TEXT,
        reply_markup=InlineKeyboard.DISCLAIMER_SHOW,
        disable_web_page_preview=True,
        parse_mode=ParseMode.HTML
    )


sttbot.add_handler(CommandHandler('disclaimer', on_disclaimer_command, filters=Filters.chat_type.private))
sttbot.add_handler(CommandHandler('optout', on_optout_command, filters=Filters.chat_type.private))
sttbot.add_handler(CommandHandler('start', on_optout_deeplink, filters=Filters.chat_type.private & Filters.regex("optout")))
sttbot.add_handler(CommandHandler('optin', on_optin_command, filters=Filters.chat_type.private))
sttbot.add_handler(CommandHandler('opt', on_opt_command, filters=Filters.chat_type.private))
sttbot.add_handler(CallbackQueryHandler(on_disclaimer_show_button, pattern=r"disclaimer:show"))
sttbot.add_handler(CallbackQueryHandler(on_optout_button, pattern=r"optout"))
