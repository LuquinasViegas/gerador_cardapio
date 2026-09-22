# -*- coding: utf-8 -*-
"""
menu_parser.py
Transforma o texto cru colado pelo usuário (do jeito que o restaurante manda,
com erros de digitação, abreviações, etc.) em uma lista estruturada de pratos:

    [{"nome": "Robalo grelhado", "descricao": "ao molho de maracujá..."}, ...]

Duas estratégias:
  1) Se houver uma ANTHROPIC_API_KEY configurada, usa a IA (Claude) para
     revisar o texto e separar nome/descrição com a mesma qualidade do
     cardápio de referência (corrige digitação, expande abreviações óbvias
     como "PF" -> "P.F.", etc).
  2) Caso contrário, usa um parser local baseado em regras simples, que
     funciona bem para o formato mais comum (nome do prato seguido de
     " - " ou de uma vírgula/preposição introduzindo os acompanhamentos).
"""

import os
import re
import json

ANTHROPIC_MODEL = "claude-sonnet-4-6"

CONECTORES = [" ao ", " à ", " no ", " na ", " com "]


def _parse_local(texto):
    """Parser baseado em regras, sem depender de internet/API."""
    pratos = []
    for linha in texto.splitlines():
        linha = linha.strip(" \t-•\u2022")
        if not linha:
            continue

        nome, descricao = None, None

        # 1) Padrão "Nome - descrição" ou "Nome — descrição" ou "Nome: descrição"
        m = re.split(r"\s+[-–—:]\s+", linha, maxsplit=1)
        if len(m) == 2:
            nome, descricao = m[0].strip(), m[1].strip()
        elif "," in linha:
            # 2) Regra principal: o nome do prato (negrito) vai até a
            #    primeira vírgula; o resto (acompanhamentos) fica normal.
            pos = linha.find(",")
            nome, descricao = linha[:pos].strip(), linha[pos:].strip()
        else:
            # 2) Procura o primeiro conector (" ao ", " com ", " no "...) que
            #    normalmente introduz a descrição do acompanhamento, desde
            #    que haja conteúdo substancial depois dele (evita cortar
            #    nomes curtos como "Lasanha à bolonhesa").
            melhor_pos = None
            for conector in CONECTORES:
                pos = linha.lower().find(conector)
                if pos > 0:
                    antes = linha[:pos].strip()
                    resto = linha[pos + len(conector):]
                    # só considera divisor de descrição se: o nome antes do
                    # conector já tem pelo menos 2 palavras (evita cortar
                    # "Virado" sozinho) e o resto parece uma lista de
                    # acompanhamentos (razoavelmente longo ou com vírgulas)
                    if len(antes.split()) >= 2 and (len(resto) > 18 or "," in resto):
                        if melhor_pos is None or pos < melhor_pos:
                            melhor_pos = pos
            if melhor_pos is not None:
                nome = linha[:melhor_pos].strip()
                descricao = linha[melhor_pos:].strip()
            else:
                nome, descricao = linha, ""

        pratos.append({"nome": nome, "descricao": descricao})
    return pratos


def _parse_com_ia(texto, api_key):
    """Usa a API da Anthropic para separar nome/descrição com mais qualidade."""
    import urllib.request

    system_prompt = (
        "Você organiza o cardápio do dia de um restaurante brasileiro (Empório do Nono) "
        "para virar uma arte visual. Você recebe um texto cru, informal, com possíveis "
        "erros de digitação e abreviações (ex.: 'PF' deve virar 'P.F.'). Para cada prato, "
        "separe em 'nome' (fica em NEGRITO na arte final) e 'descricao' (fica em peso "
        "normal). REGRA PRINCIPAL para essa separação: 'nome' é o texto até a PRIMEIRA "
        "VÍRGULA da linha (sem incluir a vírgula); tudo a partir da primeira vírgula "
        "(incluindo ela) vai para 'descricao'. Se a linha não tiver nenhuma vírgula, "
        "'nome' é a linha inteira e 'descricao' fica como string vazia — NÃO invente uma "
        "vírgula nem corte a frase por conta própria nesse caso. Exemplo: 'Filé mignon "
        "suíno ao molho madeira, acompanha arroz e feijão tropeiro' vira nome='Filé mignon "
        "suíno ao molho madeira' e descricao=', acompanha arroz e feijão tropeiro'. Corrija "
        "erros óbvios de português e digitação, mas NÃO invente ingredientes e NÃO mude a "
        "pontuação além do necessário. Responda APENAS com um JSON válido, um array de "
        "objetos com as chaves 'nome' e 'descricao', sem nenhum texto antes ou depois, sem "
        "markdown."
    )

    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": texto}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    texto_resposta = "".join(
        bloco.get("text", "") for bloco in data.get("content", []) if bloco.get("type") == "text"
    ).strip()

    texto_resposta = re.sub(r"^```(json)?|```$", "", texto_resposta.strip(), flags=re.MULTILINE).strip()
    pratos = json.loads(texto_resposta)
    # normaliza chaves
    return [{"nome": p.get("nome", "").strip(), "descricao": p.get("descricao", "").strip()} for p in pratos]


def parse_menu(texto):
    """Ponto de entrada usado pelo app. Tenta IA (se houver chave), com
    fallback automático e silencioso para o parser local em caso de erro."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if api_key:
        try:
            return _parse_com_ia(texto, api_key), "ia"
        except Exception as e:
            print(f"[menu_parser] Falha ao usar IA ({e}); usando parser local.")
    return _parse_local(texto), "local"
