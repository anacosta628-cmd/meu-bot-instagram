import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from google import genai
from google.genai import types

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
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=120000)
)
PORT = int(os.getenv("PORT", "10000"))

client = genai.Client(api_key=GEMINI_API_KEY)


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
        "📸 Envie uma foto do produto.\n"
        "🔗 Coloque o link do produto na legenda.\n\n"
        "A IA vai analisar a imagem e criar uma legenda para você! ✨"
    )


async def receber_conteudo(update, context):

    mensagem = update.message
    texto = mensagem.caption or ""

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
            "na legenda."
        )

        return

    await mensagem.reply_text(
        "🤖 Analisando o produto e criando sua legenda...\n"
        "⏳ Só um instante!"
    )

    try:

        foto = mensagem.photo[-1]

        arquivo = await context.bot.get_file(
            foto.file_id
        )

        caminho = f"/tmp/{foto.file_id}.jpg"

        await arquivo.download_to_drive(caminho)

        with open(caminho, "rb") as imagem:

            imagem_bytes = imagem.read()

        prompt = f"""
Você é especialista em criar conteúdo para Instagram de achadinhos e afiliados.

Analise a imagem do produto e crie uma legenda curta, chamativa e natural para Instagram.

REGRAS:
- Não invente preço.
- Não invente desconto.
- Não invente características que não aparecem na imagem.
- Use emojis.
- Comece com uma chamada atraente.
- Incentive a pessoa a conferir o produto pelo link.
- Termine com hashtags relevantes.
- Não diga que você é uma IA.

Link do produto:
{link}
"""

        resposta = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents=[
                types.Part.from_bytes(
                    data=imagem_bytes,
                    mime_type="image/jpeg"
                ),
                prompt
            ]
        )

        legenda = resposta.text.strip()

        legenda_final = f"{legenda}\n\n🔗 Confira aqui:\n{link}"

        context.user_data["link"] = link
        context.user_data["legenda"] = legenda_final
        context.user_data["photo_file_id"] = foto.file_id

        await mensagem.reply_text(
    "✨ PRÉVIA DA PUBLICAÇÃO\n\n"
    + legenda_final,
    reply_markup=botoes()
        
        )

        os.remove(caminho)

    except Exception as erro:

        print("ERRO GEMINI:", erro)

        await mensagem.reply_text(
            "⚠️ Não consegui gerar a legenda com a IA.\n\n"
            "Vou verificar a conexão do Gemini."
        )


async def botoes_handler(update, context):

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
            "que você escolha o dia e o horário."
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

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY não foi configurada."
        )

    thread = threading.Thread(
        target=iniciar_servidor,
        daemon=True
    )

    thread.start()

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
