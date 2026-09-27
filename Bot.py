
import os
import threading
import json
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from google import genai
from google.genai import types

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# =========================
# CONFIGURAÇÕES
# =========================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

PORT = int(os.getenv("PORT", "10000"))

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=120000),
)


# =========================
# SERVIDOR PARA O INSTAGRAM
# =========================

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

    def log_message(self, format, *args):
        return


def iniciar_servidor():

    servidor = HTTPServer(
        ("0.0.0.0", PORT),
        HealthHandler
    )

    servidor.serve_forever()


# =========================
# BOTÕES
# =========================

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


# =========================
# COMANDO START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "👋 Oi! Sou seu bot de achadinhos!\n\n"
        "📸 Envie uma foto do produto.\n"
        "🔗 Coloque o link do produto na legenda da foto.\n\n"
        "🤖 A IA vai analisar a imagem e criar uma legenda "
        "com a sua cara! ✨"
    )


# =========================
# RECEBER PRODUTO
# =========================

async def receber_conteudo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    mensagem = update.message

    texto = mensagem.caption or ""

    link = None

    for palavra in texto.split():

        if palavra.startswith("http://") or palavra.startswith("https://"):

            link = palavra
            break

    if not link:

        await mensagem.reply_text(
            "🔗 Não encontrei o link do produto.\n\n"
            "Envie a foto novamente colocando o link "
            "do produto na legenda."
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

        caminho = "/tmp/foto_file_id.jpg"

        await arquivo.download_to_drive(
            caminho
        )

        with open(caminho, "rb") as imagem:

            imagem_bytes = imagem.read()


        # =========================
        # PROMPT DA IA
        # =========================

        prompt = f"""
Você cria legendas para posts de achadinhos de compras,
no estilo de uma criadora de conteúdo brasileira.

Seu estilo deve ser:

- Divertido, espontâneo e próximo.
- Parecer uma indicação de amiga, não uma propaganda formal.
- Começar com uma chamada curta e chamativa.
- Usar emojis naturalmente.
- Criar curiosidade e vontade de conferir o produto.
- Usar frases curtas e fáceis de ler.
- Ser direto.
- Não usar linguagem muito formal.
- Não dizer que é uma IA.

ESTRUTURA:

1. Comece com uma chamada chamativa.

Exemplos:

"Olha que achadinho! 😍"

"Eu já quero! 🛍️✨"

"Que achado foi esse?! 😱"

"Se eu fosse você, já espiava! 👀"

"Achadinho que vale a pena conferir! 🛒✨"


2. Explique rapidamente o produto.

Destaque somente características que possam ser vistas
na imagem ou estejam claramente informadas.

3. Termine com uma chamada para ação.

Exemplos:

"🛍️ Corre conferir!"

"👀 Dá uma espiadinha!"

"✨ Já salva esse achadinho!"

"🛒 Garanta o seu!"


4. Coloque de 4 a 6 hashtags relevantes.

IMPORTANTE:

- Nunca invente preço.
- Nunca invente desconto.
- Nunca invente características.
- Nunca diga "link na bio".
- Nunca diga "link nos Stories".
- Nunca diga "link nos comentários".
- Não coloque o link dentro da legenda criada.
- O link será acrescentado separadamente pelo bot.

Link do produto:
{link}
"""


        # =========================
        # GEMINI
        # =========================

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


        # =========================
        # SALVAR DADOS
        # =========================

        legenda_instagram = (
            f"{legenda}\n\n"
            f"🔗 Confira aqui:\n"
            f"{link}"
        )

        context.user_data["link"] = link

        context.user_data["legenda"] = legenda_instagram

        context.user_data["photo_file_id"] = foto.file_id


        # =========================
        # PRÉVIA NO TELEGRAM
        # =========================

        await mensagem.reply_photo(

            photo=foto.file_id,

            caption=(
                "✨ PRÉVIA DA PUBLICAÇÃO\n\n"
                + legenda
            ),

            reply_markup=botoes()
        )


        # Link separado
        # Sem cartão/preview da Shopee

        await mensagem.reply_text(

            "🔗 Confira aqui:\n" + link,

            link_preview_options=LinkPreviewOptions(
                is_disabled=True
            )
        )


    except Exception as erro:

        print(
            "ERRO GEMINI:",
            erro
        )

        await mensagem.reply_text(

            "⚠️ Não consegui gerar a legenda com a IA.\n\n"
            "Vou verificar a conexão do Gemini."
        )


# =========================
# BOTÕES DE PUBLICAÇÃO
# =========================

async def botoes_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    acao = query.data


    # =========================
    # PUBLICAR
    # =========================

    if acao == "publicar":

        try:

            await query.edit_message_caption(
                caption="🚀 Publicando no Instagram... ⏳"
            )


            if not INSTAGRAM_ACCESS_TOKEN:

                raise RuntimeError(
                    "INSTAGRAM_ACCESS_TOKEN não foi configurado."
                )


            token = INSTAGRAM_ACCESS_TOKEN


            # =========================
            # PEGAR ID DO INSTAGRAM
            # =========================

            dados_me = urllib.parse.urlencode({

                "fields": "id,username",

                "access_token": token,

            })


            url_me = (
                "https://graph.instagram.com/v24.0/me?"
                + dados_me
            )


            with urllib.request.urlopen(
                url_me,
                timeout=30
            ) as resposta:

                conta = json.loads(
                    resposta.read().decode()
                )


            ig_user_id = conta["id"]


            # =========================
            # URL DA FOTO
            # =========================

            foto_url = (
                "https://meu-bot-instagram-7jy8.onrender.com/foto.jpg"
            )


            legenda_instagram = context.user_data.get(
                "legenda",
                ""
            )


            # =========================
            # CRIAR PUBLICAÇÃO
            # =========================

            dados_media = urllib.parse.urlencode({

                "image_url": foto_url,

                "caption": legenda_instagram,

                "access_token": token,

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
                requisicao,
                timeout=60
            ) as resposta:

                media = json.loads(
                    resposta.read().decode()
                )


            creation_id = media["id"]


            # =========================
            # PUBLICAR NO INSTAGRAM
            # =========================

            dados_publicar = urllib.parse.urlencode({

                "creation_id": creation_id,

                "access_token": token,

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
                requisicao_publicar,
                timeout=60
            ) as resposta:

                resultado = json.loads(
                    resposta.read().decode()
                )


            print(
                "PUBLICADO:",
                resultado
            )


            await query.edit_message_caption(

                caption=(
                    "🎉 Publicado no Instagram com sucesso!\n\n"
                    "📲 Seu achadinho já está no ar! ❤️"
                )
            )


        except Exception as erro:

            print(
                "ERRO INSTAGRAM:",
                erro
            )


            await query.edit_message_caption(

                caption=(
                    "⚠️ Não consegui publicar no Instagram.\n\n"
                    "Vou verificar a conexão e o token."
                )
            )


    # =========================
    # AGENDAR
    # =========================

    elif acao == "agendar":

        await query.edit_message_caption(

            caption=(
                "📅 Agendamento selecionado!\n\n"
                "Na próxima etapa vamos permitir que "
                "você escolha o dia e o horário."
            )
        )


    # =========================
    # EDITAR
    # =========================

    elif acao == "editar":

        await query.edit_message_caption(

            caption=(
                "✏️ Edição selecionada!\n\n"
                "Na próxima versão você poderá editar "
                "a legenda antes de publicar."
            )
        )


    # =========================
    # CANCELAR
    # =========================

    elif acao == "cancelar":

        context.user_data.clear()

        await query.edit_message_caption(

            caption="❌ Publicação cancelada."
        )


# =========================
# INICIAR BOT
# =========================

def main():

    if not TOKEN:

        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN não foi configurado."
        )


    if not GEMINI_API_KEY:

        raise RuntimeError(
            "GEMINI_API_KEY não foi configurada."
        )


    # Servidor para disponibilizar a imagem
    # para o Instagram

    thread = threading.Thread(

        target=iniciar_servidor,

        daemon=True
    )

    thread.start()


    # =========================
    # APLICATIVO TELEGRAM
    # =========================

    app = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )


    # Receber somente fotos por enquanto

    app.add_handler(
        MessageHandler(
            filters.PHOTO,
            receber_conteudo
        )
    )


    app.add_handler(
        CallbackQueryHandler(
            botoes_handler
        )
    )


    print(
        "🤖 Bot iniciado!"
    )


    app.run_polling()


# =========================
# EXECUTAR
# =========================

if __name__ == "__main__":

    main()
