import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))


# Servidor HTTP simples para o Render
class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot funcionando!")

    def log_message(self, format, *args):
        return


def iniciar_servidor():
    servidor = HTTPServer(("0.0.0.0", PORT), HealthHandler)
    servidor.serve_forever()


def botoes():
    teclado = [
        [
            InlineKeyboardButton(
                "✅ Publicar agora",
                callback_data="publicar"
            ),
            InlineKeyboardButton(
                "📅 Agendar",
                callback_data="agendar"
            ),
        ],
        [
            InlineKeyboardButton(
                "✏️ Editar",
                callback_data="editar"
            ),
            InlineKeyboardButton(
                "❌ Cancelar",
                callback_data="cancelar"
            ),
        ],
    ]

    return InlineKeyboardMarkup(teclado)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "👋 Oi! Sou seu bot de achadinhos!\n\n"
        "📸 Envie uma foto ou vídeo do produto.\n"
        "🔗 Coloque o link do produto na legenda.\n\n"
        "Exemplo:\n"
        "Foto do produto\n"
        "https://s.shopee.com.br/seulink"
    )


async def receber_conteudo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    mensagem = update.message

    texto = mensagem.caption or ""

    # Procura um link
    palavras = texto.split()

    link = None

    for palavra in palavras:
        if palavra.startswith("http://") or palavra.startswith("https://"):
            link = palavra
            break

    if not link:

        await mensagem.reply_text(
            "🔗 Não encontrei o link.\n\n"
            "Envie a foto com o link do produto "
            "na legenda da foto."
        )

        return

    # Guarda o conteúdo
    context.user_data["link"] = link

    # Legenda inicial
    legenda = (
        "🛍️ ACHADINHO DO DIA!\n\n"
        "✨ Olha só esse achadinho que encontrei!\n\n"
        "💰 Confira o preço e todos os detalhes:\n"
        f"🔗 {link}\n\n"
        "#achadinhos #ofertas #shopee #comprinhas"
    )

    context.user_data["legenda"] = legenda

    await mensagem.reply_text(
        "✨ PRÉVIA DA PUBLICAÇÃO\n\n"
        + legenda,
        reply_markup=botoes()
    )


async def botoes_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    acao = query.data

    if acao == "publicar":

        await query.edit_message_text(
            "🚀 Publicação aprovada!\n\n"
            "📲 O Instagram será conectado na próxima etapa."
        )

    elif acao == "agendar":

        await query.edit_message_text(
            "📅 Agendamento selecionado!\n\n"
            "Na próxima etapa vamos permitir "
            "que você escolha data e horário."
        )

    elif acao == "editar":

        await query.edit_message_text(
            "✏️ Edição selecionada!\n\n"
            "Na próxima versão você poderá "
            "editar a legenda antes de publicar."
        )

    elif acao == "cancelar":

        context.user_data.clear()

        await query.edit_message_text(
            "❌ Publicação cancelada."
        )


def main():

    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN não foi configurado."
        )

    # Inicia servidor para o Render
    thread = threading.Thread(
        target=iniciar_servidor,
        daemon=True
    )

    thread.start()

    # Cria o bot
    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receber_conteudo
        )
    )

    app.add_handler(
        MessageHandler(
            filters.VIDEO,
            receber_conteudo
        )
    )

    app.add_handler(
        CallbackQueryHandler(botoes_handler)
    )

    print("🤖 Bot iniciado!")

    app.run_polling()


if __name__ == "__main__":
    main()
