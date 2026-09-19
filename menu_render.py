# -*- coding: utf-8 -*-
"""
menu_render.py
Motor de geração da arte "Almoço do Dia" (Empório do Nono) em PIL,
replicando fielmente o layout, cores e tipografia do modelo de referência.
"""

import os
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ---------------------------------------------------------------------------
# Paleta de cores (extraída/definida a partir da arte de referência)
# ---------------------------------------------------------------------------
COR_FUNDO = (245, 239, 224)       # #F5EFE0
COR_BORDA = (139, 38, 53)         # #8B2635
COR_TEXTO = (26, 24, 21)          # #1A1815
COR_VINHO = (139, 38, 53)         # #8B2635 ("do" no título)
COR_AMARELO = (242, 183, 5)       # #F2B705

CANVAS_W, CANVAS_H = 1080, 1920

# ---------------------------------------------------------------------------
# Fontes esperadas (baixe gratuitamente em fonts.google.com e salve com
# esses nomes exatos dentro da pasta /fonts). Se algum arquivo não existir,
# o sistema usa uma fonte parecida já disponível, para nunca quebrar.
# ---------------------------------------------------------------------------
FONT_FILES = {
    "special_elite": "SpecialElite-Regular.ttf",
    "playfair_black": "PlayfairDisplay-Black.ttf",
    "playfair_black_italic": "PlayfairDisplay-BlackItalic.ttf",
    "playfair_light_italic": "PlayfairDisplay-LightItalic.ttf",
    "archivo_regular": "Archivo-Regular.ttf",
    "archivo_bold": "Archivo-Bold.ttf",
}

# fallbacks já presentes no ambiente, usados só se a fonte "de verdade"
# ainda não tiver sido colocada na pasta /fonts
_FALLBACK_CANDIDATES = {
    "special_elite": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
    ],
    "playfair_black": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ],
    "playfair_black_italic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf",
    ],
    "playfair_light_italic": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf",
    ],
    "archivo_regular": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "archivo_bold": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}

_font_cache = {}


def _resolve_font_path(key):
    real_path = os.path.join(FONTS_DIR, FONT_FILES[key])
    if os.path.exists(real_path):
        return real_path
    for candidate in _FALLBACK_CANDIDATES.get(key, []):
        if os.path.exists(candidate):
            return candidate
    return None


def get_font(key, size):
    cache_key = (key, size)
    if cache_key in _font_cache:
        return _font_cache[cache_key]
    path = _resolve_font_path(key)
    try:
        if path:
            font = ImageFont.truetype(path, size)
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    _font_cache[cache_key] = font
    return font


def fonts_status():
    """Retorna quais fontes 'oficiais' já estão instaladas e quais estão
    faltando (para avisar o usuário na interface)."""
    status = {}
    for key, filename in FONT_FILES.items():
        status[key] = {
            "filename": filename,
            "instalada": os.path.exists(os.path.join(FONTS_DIR, filename)),
        }
    return status


# ---------------------------------------------------------------------------
# Utilidades de texto com letter-spacing e mistura de fontes (negrito/regular)
# ---------------------------------------------------------------------------
def draw_text_tracked(draw, xy, text, font, fill, tracking=0):
    """Desenha texto com espaçamento extra entre letras (tracking, em px)."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        w = draw.textlength(ch, font=font)
        x += w + tracking
    return x


def tracked_text_width(draw, text, font, tracking=0):
    if not text:
        return 0
    total = 0
    for ch in text:
        total += draw.textlength(ch, font=font) + tracking
    return total - tracking


def draw_centered_tracked(draw, center_x, y, text, font, fill, tracking=0):
    w = tracked_text_width(draw, text, font, tracking)
    x = center_x - w / 2
    draw_text_tracked(draw, (x, y), text, font, fill, tracking)


# ---------------------------------------------------------------------------
# Quebra de linha "rich text": cada prato é uma lista de "runs"
# [(texto, negrito?), (texto, negrito?), ...] que é distribuída em linhas
# respeitando a largura máxima, trocando de fonte no meio da linha quando
# necessário (ex.: nome do prato em negrito + descrição em regular).
# ---------------------------------------------------------------------------
def wrap_runs(draw, runs, font_regular, font_bold, max_width):
    """runs: list of (word, is_bold) already split into WORDS (não frases).
    Retorna uma lista de linhas, cada linha é uma lista de (word, is_bold)."""
    lines = []
    current = []
    current_width = 0
    space_w = draw.textlength(" ", font=font_regular)

    for word, is_bold in runs:
        font = font_bold if is_bold else font_regular
        word_w = draw.textlength(word, font=font)
        extra = (space_w if current else 0)
        if current and current_width + extra + word_w > max_width:
            lines.append(current)
            current = [(word, is_bold)]
            current_width = word_w
        else:
            current.append((word, is_bold))
            current_width += extra + word_w
    if current:
        lines.append(current)
    return lines


def draw_rich_line(draw, x, y, line, font_regular, font_bold, fill):
    space_w = draw.textlength(" ", font=font_regular)
    cur_x = x
    for i, (word, is_bold) in enumerate(line):
        font = font_bold if is_bold else font_regular
        draw.text((cur_x, y), word, font=font, fill=fill)
        cur_x += draw.textlength(word, font=font)
        if i < len(line) - 1:
            cur_x += space_w
    return cur_x


def dish_to_runs(nome, descricao):
    runs = []
    if nome:
        for w in nome.split():
            runs.append((w, True))
    if descricao:
        for w in descricao.split():
            runs.append((w, False))
    return runs


# ---------------------------------------------------------------------------
# Geração da arte final
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Constantes de layout calibradas em cima da arte de referência original
# (medidas em pixel diretamente na imagem de 1080x1920)
# ---------------------------------------------------------------------------
MARGIN = 34                # moldura vermelha
DIVIDER_LEFT, DIVIDER_RIGHT = 109, 971      # linha divisória e tarja amarela
TEXT_LEFT, TEXT_RIGHT = 185, 895            # coluna de texto dos pratos
SUBTITULO_TOP = 141
TITULO_TOP = 189
DIVIDER_Y = 412
DISHES_TOP = 441
BANNER_TOP_TARGET = 1535
BANNER_HEIGHT = 110
MIN_GAP_BEFORE_BANNER = 20
LOGO_GAP_AFTER_BANNER = 11

# tamanhos "nominais" (tamanho de referência com o menu de 6 pratos)
NOM_BODY_SIZE = 33
NOM_LINE_HEIGHT = 53
NOM_DISH_GAP_EXTRA = 16
MIN_BODY_SIZE = 22  # nunca encolhe além disso; deixa transbordar com elegância


def _medir_altura_conteudo(draw, pratos, font_regular, font_bold, line_height, dish_gap_extra, content_width):
    total = 0
    for i, prato in enumerate(pratos):
        runs = dish_to_runs(prato.get("nome", ""), prato.get("descricao", ""))
        lines = wrap_runs(draw, runs, font_regular, font_bold, content_width)
        total += len(lines) * line_height
        if i < len(pratos) - 1:
            total += dish_gap_extra
    return total


def gerar_cardapio(
    pratos,
    destaque=None,
    subtitulo="DESDE 1999 · BARÃO GERALDO",
    titulo_linha1="Almoço",
    titulo_conector="do",
    titulo_linha2="Dia",
    rodape_linha1="TODOS OS PRATOS ACOMPANHAM SALADA",
    rodape_linha2="E CESTA DE PÃES FEITOS NA CASA",
    logo_path=None,
    output_path=None,
):
    """
    pratos: lista de dicts {"nome": str, "descricao": str}
    Retorna a imagem PIL gerada (e salva em output_path, se informado).
    """
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), COR_FUNDO)
    draw = ImageDraw.Draw(img)

    center_x = CANVAS_W // 2
    content_width = TEXT_RIGHT - TEXT_LEFT

    # ---- Moldura -----------------------------------------------------
    draw.rectangle(
        [MARGIN, MARGIN, CANVAS_W - MARGIN, CANVAS_H - MARGIN],
        outline=COR_BORDA,
        width=2,
    )

    # ---- Selo "DESDE 1999 · BARÃO GERALDO" ----------------------------
    f_selo = get_font("special_elite", 26)
    selo = f"— {subtitulo} —"
    draw_centered_tracked(draw, center_x, SUBTITULO_TOP, selo, f_selo, COR_TEXTO, tracking=1)

    # ---- Título "Almoço" / "do Dia" -----------------------------------
    f_tit_black = get_font("playfair_black", 92)
    f_tit_light_italic = get_font("playfair_light_italic", 76)

    y = TITULO_TOP
    w1 = draw.textlength(titulo_linha1, font=f_tit_black)
    draw.text((center_x - w1 / 2, y), titulo_linha1, font=f_tit_black, fill=COR_TEXTO)
    y += 100

    espaco = draw.textlength(" ", font=f_tit_black)
    w_do = draw.textlength(titulo_conector, font=f_tit_light_italic)
    w_dia = draw.textlength(titulo_linha2, font=f_tit_black)
    total_w = w_do + espaco + w_dia
    x_line2 = center_x - total_w / 2
    draw.text((x_line2, y + 12), titulo_conector, font=f_tit_light_italic, fill=COR_VINHO)
    draw.text((x_line2 + w_do + espaco, y), titulo_linha2, font=f_tit_black, fill=COR_TEXTO)

    # ---- Linha divisória ----------------------------------------------
    draw.line([(DIVIDER_LEFT, DIVIDER_Y), (DIVIDER_RIGHT, DIVIDER_Y)], fill=COR_BORDA, width=2)

    # ---- Lista de pratos (com auto-encolhimento se o menu for grande) ----
    available_height = BANNER_TOP_TARGET - DISHES_TOP - MIN_GAP_BEFORE_BANNER

    body_size = NOM_BODY_SIZE
    line_height = NOM_LINE_HEIGHT
    dish_gap_extra = NOM_DISH_GAP_EXTRA

    for _ in range(6):  # poucas iterações bastam para convergir
        f_body_reg = get_font("archivo_regular", body_size)
        f_body_bold = get_font("archivo_bold", body_size)
        altura = _medir_altura_conteudo(draw, pratos, f_body_reg, f_body_bold, line_height, dish_gap_extra, content_width)
        if altura <= available_height or body_size <= MIN_BODY_SIZE:
            break
        fator = max(available_height / altura, MIN_BODY_SIZE / body_size)
        body_size = max(MIN_BODY_SIZE, int(body_size * fator))
        line_height = max(int(NOM_LINE_HEIGHT * (body_size / NOM_BODY_SIZE)), body_size + 8)
        dish_gap_extra = max(int(NOM_DISH_GAP_EXTRA * (body_size / NOM_BODY_SIZE)), 6)

    f_body_reg = get_font("archivo_regular", body_size)
    f_body_bold = get_font("archivo_bold", body_size)

    y = DISHES_TOP
    for i, prato in enumerate(pratos):
        nome = prato.get("nome", "").strip()
        descricao = prato.get("descricao", "").strip()
        runs = dish_to_runs(nome, descricao)
        lines = wrap_runs(draw, runs, f_body_reg, f_body_bold, content_width)
        for line in lines:
            draw_rich_line(draw, TEXT_LEFT, y, line, f_body_reg, f_body_bold, COR_TEXTO)
            y += line_height
        if i < len(pratos) - 1:
            y += dish_gap_extra

    # se o conteúdo terminou bem antes do alvo, a tarja desce até o alvo
    # (igual à referência); se passou do alvo (menu grande mesmo após
    # encolher), a tarja é empurrada para logo abaixo do texto.
    banner_top = max(BANNER_TOP_TARGET, y + MIN_GAP_BEFORE_BANNER)

    # ---- Tarja amarela no rodapé ---------------------------------------
    f_rodape = get_font("archivo_regular", 25)
    tracking_rodape = 0.5
    banner_bottom = banner_top + BANNER_HEIGHT
    draw.rectangle(
        [MARGIN, banner_top, CANVAS_W - MARGIN, banner_bottom],
        fill=COR_AMARELO,
    )
    l1_w = tracked_text_width(draw, rodape_linha1, f_rodape, tracking_rodape)
    l2_w = tracked_text_width(draw, rodape_linha2, f_rodape, tracking_rodape)
    ty = banner_top + BANNER_HEIGHT / 2 - (f_rodape.size * 1.15)
    draw_text_tracked(draw, (center_x - l1_w / 2, ty), rodape_linha1, f_rodape, COR_TEXTO, tracking_rodape)
    ty += f_rodape.size * 1.5
    draw_text_tracked(draw, (center_x - l2_w / 2, ty), rodape_linha2, f_rodape, COR_TEXTO, tracking_rodape)

    # ---- Logo ------------------------------------------------------------
    logo_path = logo_path or os.path.join(STATIC_DIR, "logo.png")
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo_w = 260
        ratio = logo_w / logo.width
        logo_h = int(logo.height * ratio)
        logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
        logo_x = center_x - logo_w // 2
        logo_y = banner_bottom + LOGO_GAP_AFTER_BANNER
        # garante que a logo nunca ultrapasse a moldura inferior
        max_logo_y = CANVAS_H - MARGIN - logo_h - 10
        logo_y = min(logo_y, max_logo_y)
        img.paste(logo, (logo_x, logo_y), logo)

    if output_path:
        img.save(output_path, "PNG")

    return img
