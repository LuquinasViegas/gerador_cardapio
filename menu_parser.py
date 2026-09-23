# -*- coding: utf-8 -*-
"""
menu_parser.py
Transforma o texto cru colado pelo usuário (do jeito que o restaurante manda,
com erros de digitação, abreviações, etc.) em uma lista estruturada de pratos:

    [{"nome": "Robalo grelhado", "descricao": "ao molho de maracujá..."}, ...]

Estratégias (nessa ordem de prioridade):
  1) GEMINI_API_KEY configurada -> usa o Google Gemini (tem camada gratuita).
  2) ANTHROPIC_API_KEY configurada -> usa a Claude da Anthropic (paga).
  3) Nenhuma chave -> usa um parser local baseado em regras simples.

As duas IAs recebem exatamente o mesmo prompt/instruções, então o resultado
é equivalente não importa qual delas você configurar.
"""

import os
import re
import json

ANTHROPIC_MODEL = "claude-sonnet-4-6"
GEMINI_MODEL = "gemini-2.0-flash"

CONECTORES = [" ao ", " à ", " no ", " na ", " com "]

SYSTEM_PROMPT = (
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
            # 3) Procura o primeiro conector (" ao ", " com ", " no "...) que
            #    normalmente introduz a descrição do acompanhamento, desde
            #    que haja conteúdo substancial depois dele (evita cortar
            #    nomes curtos como "Lasanha à bolonhesa").
            melhor_pos = None
            for conector in CONECTORES:
                pos = linha.lower().find(conector)
                if pos > 0:
                    antes = linha[:pos].strip()
                    resto = linha[pos + len(conector):]
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


def _limpar_json(texto_resposta):
    texto_resposta = texto_resposta.strip()
    texto_resposta = re.sub(r"^```(json)?|```$", "", texto_resposta, flags=re.MULTILINE).strip()
    pratos = json.loads(texto_resposta)
    return [{"nome": p.get("nome", "").strip(), "descricao": p.get("descricao", "").strip()} for p in pratos]


def _parse_com_anthropic(texto, api_key):
    """Usa a API da Anthropic (Claude) — paga."""
    import urllib.request

    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 2000,
        "system": SYSTEM_PROMPT,
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
    )
    return _limpar_json(texto_resposta)


def _parse_com_gemini(texto, api_key):
    """Usa a API do Google Gemini — tem camada gratuita (aistudio.google.com)."""
    import urllib.request

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": texto}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    texto_resposta = data["candidates"][0]["content"]["parts"][0]["text"]
    return _limpar_json(texto_resposta)


def parse_menu(texto):
    """Ponto de entrada usado pelo app. Ordem de prioridade: Gemini (grátis)
    -> Anthropic (paga) -> regras locais. Se a IA configurada falhar por
    qualquer motivo, cai automaticamente para o parser local, sem travar."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            return _parse_com_gemini(texto, gemini_key), "ia (gemini)"
        except Exception as e:
            print(f"[menu_parser] Falha ao usar Gemini ({e}); tentando próxima opção.")

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if anthropic_key:
        try:
            return _parse_com_anthropic(texto, anthropic_key), "ia (claude)"
        except Exception as e:
            print(f"[menu_parser] Falha ao usar Anthropic ({e}); usando parser local.")

    return _parse_local(texto), "local"
