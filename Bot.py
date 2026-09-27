import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from google import genai
from google.genai import types

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", "10000"))
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=120000)
)
PORT = int(os.getenv("PORT", "10000"))

client = genai.Client(api_key=GEMINI_API_KEY)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/foto.jpg" and os.path.exists("/tmp/foto_file_id.jpg"):
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.end_headers()

            with open("/tmp/foto_file_id.jpg", "rb") as arquivo:
                self.wfile.write(arquivo.read())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Bot funcionando!")


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
Você cria legendas para posts de achadinhos de compras, no estilo de uma criadora de conteúdo brasileira.

Seu estilo deve ser:
- Divertido, espontâneo e próximo.
- Parecer uma indicação de amiga, não uma propaganda formal.
- Começar com uma chamada curta e chamativa.
- Usar emojis de forma natural.
- Criar curiosidade e vontade de conferir o produto.
- Usar frases curtas e fáceis de ler.
- Ser direto, sem textos longos.
- Não usar linguagem muito formal.
- Não dizer que é uma IA.

ESTRUTURA:

1. Uma chamada chamativa, como:
"Olha que achadinho! 😍"
"Eu já quero! 🛍️✨"
"Que achado foi esse?! 😱"
"Se eu fosse você, já espiava! 👀"
"Achadinho que vale a pena conferir! 🛒✨"

2. Explique rapidamente o produto e destaque apenas características que possam ser vistas na imagem ou estejam claramente informadas.

3. Termine com uma chamada para ação, por exemplo:
"🛍️ Corre conferir!"
"👀 Dá uma espiadinha!"
"✨ Já salva esse achadinho!"
"🛒 Garanta o seu!"

4. Depois coloque de 4 a 6 hashtags relevantes.

IMPORTANTE:
- Nunca invente preço.
- Nunca invente desconto.
- Nunca invente características.
- Nunca diga "link na bio".
- Nunca diga "link nos Stories".
- Nunca diga "link nos comentários".
- Não coloque o link dentro da legenda criada.
- O link será acrescentado separadamente pelo bot.

Produto/link:
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

        await mensagem.reply_photo(
    photo=foto.file_id,
    caption="✨ PRÉVIA DA PUBLICAÇÃO\n\n" + legenda,
    reply_markup=botoes()
)

        await mensagem.reply_photo(
            photo=foto.file_id,
            caption="✨ PRÉVIA DA PUBLICAÇÃO\n\n" + legenda,
            reply_markup=botoes()
        )

        await mensagem.reply_text(
            "🔗 Confira aqui:\n" + link,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

    except Exception as erro:

        print("ERRO GEMINI:", erro)

        await mensagem.reply_text(
            "⚠️ Não consegui gerar a legenda com a IA.\n\n"
            "Vou verificar a conexão do Gemini."
        )
    async def botoes_handler(update,
    context):
        query = update.callback_query
    await query.answer()

    acao = query.data

    if acao == "publicar":
    try:
        await query.edit_message_text(
            "📲 Publicando no Instagram... ⏳"
            )

            import urllib.request
            import urllib.parse
            import json

            token = INSTAGRAM_ACCESS_TOKEN

            dados_me = urllib.parse.urlencode({
                "fields": "id,username",
                "access_token": token
            })

            url_me = (
                "https://graph.instagram.com/v24.0/me?"
                + dados_me
            )

            with urllib.request.urlopen(url_me) as resposta:
                conta = json.loads(
                    resposta.read().decode()
                )

            ig_user_id = conta["id"]

            foto_url = (
                "https://meu-bot-instagram-7jy8.onrender.com/foto.jpg"
            )

            legenda_instagram = context.user_data.get(
                "legenda",
                ""
            )

            dados_media = urllib.parse.urlencode({
                "image_url": foto_url,
                "caption": legenda_instagram,
                "access_token": token
            }).encode()

            url_media = (
                f"https://graph.instagram.com/v24.0/"
                f"{ig_user_id}/media"
            )

            requisicao = urllib.request.Request(
                url_media,
                data=dados_media,
                method="POST"
            )

            with urllib.request.urlopen(
                requisicao
            ) as resposta:
                media = json.loads(
                    resposta.read().decode()
                )

            creation_id = media["id"]

            dados_publicar = urllib.parse.urlencode({
                "creation_id": creation_id,
                "access_token": token
            }).encode()

            url_publicar = (
                f"https://graph.instagram.com/v24.0/"
                f"{ig_user_id}/media_publish"
            )

            requisicao_publicar = urllib.request.Request(
                url_publicar,
                data=dados_publicar,
                method="POST"
            )

            with urllib.request.urlopen(
                requisicao_publicar
            ) as resposta:
                resultado = json.loads(
                    resposta.read().decode()
                )

            await query.edit_message_text(
                "🎉 Publicado no Instagram com sucesso!\n\n"
                "📲 Seu achadinho já está no ar! ❤️"
            )

        except Exception as erro:
            print("ERRO INSTAGRAM:", erro)

            await query.edit_message_text(
                "⚠️ Não consegui publicar no Instagram.\n\n"
                "Vou verificar a conexão e o token."
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
