# -*- coding: utf-8 -*-
"""
app.py - Gerador de Cardápio "Almoço do Dia" (Empório do Nono)

Rode com:
    python app.py

Depois acesse http://127.0.0.1:5000 no navegador.

Observação técnica: tudo roda num único endpoint ("/" localmente e também
registrado como "/api/index"), porque o runtime Python da Vercel, ao usar
"rewrites", entrega ao Flask o caminho de destino ("/api/index") em vez do
caminho original que o navegador pediu. Registrando as duas rotas para a
mesma função, o app funciona igual nos dois ambientes. A imagem gerada é
devolvida embutida na própria página (data URI em base64), então não
precisamos gravar nada em disco — o que também evita problemas com o
sistema de arquivos somente-leitura do ambiente serverless da Vercel.
"""

import os
import io
import base64

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import Flask, render_template, request

from menu_parser import parse_menu
from menu_render import gerar_cardapio, fonts_status

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", fontes=fonts_status())

    texto_menu = request.form.get("menu", "").strip()

    if not texto_menu:
        return render_template(
            "index.html",
            fontes=fonts_status(),
            erro="Cole os pratos do dia no campo O MENU antes de gerar.",
        )

    pratos, metodo = parse_menu(texto_menu)

    img = gerar_cardapio(pratos)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    data_uri = f"data:image/png;base64,{b64}"

    return render_template(
        "index.html",
        fontes=fonts_status(),
        imagem_gerada=data_uri,
        texto_menu=texto_menu,
        metodo=metodo,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
