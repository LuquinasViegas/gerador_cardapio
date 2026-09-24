# -*- coding: utf-8 -*-
"""
menu_render.py
Motor de geração da arte "Almoço do Dia" (Empório do Nono) em PIL,
replicando fielmente o layout, cores e tipografia do modelo de referência.
"""

import os
import re
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
    "playfair_light_italic": "PlayfairDisplay-Italic.ttf",
    "archivo_regular": "Archivo-Regular.ttf",
    "archivo_bold": "Archivo-Bold.ttf",
}

# fallbacks: primeiro tenta fontes reserva empacotadas dentro do próprio
# projeto (fonts/_bundled/, sempre disponíveis independente do ambiente/SO,
# incluindo a Vercel), depois tenta fontes do sistema operacional (útil em
# ambientes que já as tenham, como esta máquina de desenvolvimento).
def _bundled(filename):
    return os.path.join(FONTS_DIR, "_bundled", filename)


# Fonte reserva unica, sempre empacotada dentro do proprio projeto
# (fonts/_bundled/DejaVuSans.ttf), usada para qualquer papel que nao tenha
# a fonte oficial (Special Elite / Playfair Display / Archivo) instalada
# em fonts/. Mantem tudo legivel e no lugar certo em qualquer ambiente,
# inclusive a Vercel, sem depender de fontes do sistema operacional.
_UNICA = _bundled("DejaVuSans.ttf")
_SISTEMA = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

_FALLBACK_CANDIDATES = {
    "special_elite": [_UNICA, _SISTEMA],
    "playfair_black": [_UNICA, _SISTEMA],
    "playfair_black_italic": [_UNICA, _SISTEMA],
    "playfair_light_italic": [_UNICA, _SISTEMA],
    "archivo_regular": [_UNICA, _SISTEMA],
    "archivo_bold": [_UNICA, _SISTEMA],
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
    nome_palavras = nome.split() if nome else []
    desc = descricao or ""
    # gruda pontuação que abre a descrição (ex.: ", arroz...") direto no
    # fim do nome, sem espaço antes — evita o "grelhado , arroz" estranho
    m = re.match(r"^([,;:.!?])\s*(.*)$", desc)
    if m and nome_palavras:
        nome_palavras[-1] = nome_palavras[-1] + m.group(1)
        desc = m.group(2)
    for w in nome_palavras:
        runs.append((w, True))
    if desc:
        for w in desc.split():
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
BANNER_TOP_TARGET = 1400
BANNER_HEIGHT = 110
MIN_GAP_BEFORE_BANNER = 20
LOGO_GAP_AFTER_BANNER = 34

# tamanhos "nominais" (tamanho de referência com o menu de 6 pratos)
NOM_BODY_SIZE = 33
NOM_LINE_HEIGHT = 46
NOM_DISH_GAP_EXTRA = 10
MIN_BODY_SIZE = 22  # nunca encolhe além disso; deixa transbordar com elegância
MAX_BODY_SIZE = 46  # nunca cresce além disso, mesmo com poucos pratos


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
    draw_centered_tracked(draw, center_x, SUBTITULO_TOP, selo, f_selo, COR_TEXTO, tracking=3)

    # ---- Título "Almoço" / "do Dia" -----------------------------------
    f_tit_black = get_font("playfair_black", 104)

    y = TITULO_TOP
    w1 = draw.textlength(titulo_linha1, font=f_tit_black)
    draw.text((center_x - w1 / 2, y), titulo_linha1, font=f_tit_black, fill=COR_TEXTO)
    # espaço até a linha 2 calculado pela métrica real da fonte (ascent),
    # bem mais compacto do que usar a caixa de texto inteira (que reserva
    # espaço de descendente raramente usado, deixando tudo "solto")
    ascent, descent = f_tit_black.getmetrics()
    y = TITULO_TOP + ascent + int(descent * 0.15)

    # tamanho do "do" calibrado pela altura real do glifo de "Dia" nesta
    # fonte (evita depender de que a fonte italica tenha as mesmas
    # proporcoes/tamanho nominal da fonte black - cada família de fonte
    # escala diferente no mesmo tamanho em pontos). Começa do mesmo
    # tamanho do "Dia" e ajusta por algumas rodadas até bater a proporção
    # desejada (letra minúscula com ascendente costuma medir menos que
    # a maiúscula, então o alvo é ~82% da altura de "Dia", não 100%).
    w_dia = draw.textlength(titulo_linha2, font=f_tit_black)
    bbox_dia = draw.textbbox((0, 0), titulo_linha2, font=f_tit_black)
    altura_dia = bbox_dia[3] - bbox_dia[1]
    alvo = altura_dia * 0.82

    tam_italic = 92
    for _ in range(4):
        f_tit_light_italic = get_font("playfair_light_italic", tam_italic)
        bbox_do = draw.textbbox((0, 0), titulo_conector, font=f_tit_light_italic)
        altura_do = max(bbox_do[3] - bbox_do[1], 1)
        if abs(altura_do - alvo) <= altura_dia * 0.04:
            break
        tam_italic = max(20, round(tam_italic * (alvo / altura_do)))
    f_tit_light_italic = get_font("playfair_light_italic", tam_italic)

    w_do = draw.textlength(titulo_conector, font=f_tit_light_italic)
    espaco = draw.textlength(" ", font=f_tit_black)
    total_w = w_do + espaco + w_dia
    x_line2 = center_x - total_w / 2

    # alinha "do" e "Dia" pela base (independente de metricas de cada fonte)
    bbox_dia_pos = draw.textbbox((x_line2 + w_do + espaco, y), titulo_linha2, font=f_tit_black)
    base_dia = bbox_dia_pos[3]
    bbox_do_trial = draw.textbbox((x_line2, y), titulo_conector, font=f_tit_light_italic)
    y_do = y + (base_dia - bbox_do_trial[3])

    draw.text((x_line2, y_do), titulo_conector, font=f_tit_light_italic, fill=COR_VINHO)
    draw.text((x_line2 + w_do + espaco, y), titulo_linha2, font=f_tit_black, fill=COR_TEXTO)

    # ---- Linha divisória (posição calculada pela altura real do título,
    # em vez de um número fixo, pra nunca mais cruzar por cima do texto) --
    fundo_titulo = max(bbox_dia_pos[3], y_do + (bbox_do_trial[3] - bbox_do_trial[1]))
    divider_y = int(fundo_titulo + 34)
    dishes_top = divider_y + 29
    draw.line([(DIVIDER_LEFT, divider_y), (DIVIDER_RIGHT, divider_y)], fill=COR_BORDA, width=2)

    # ---- Lista de pratos (encolhe se for grande, aumenta se for pequeno,
    # sempre tentando preencher bem o espaço disponível) ------------------
    available_height = BANNER_TOP_TARGET - dishes_top - MIN_GAP_BEFORE_BANNER

    body_size = NOM_BODY_SIZE
    line_height = NOM_LINE_HEIGHT
    dish_gap_extra = NOM_DISH_GAP_EXTRA

    for _ in range(8):  # poucas iterações bastam para convergir
        f_body_reg = get_font("archivo_regular", body_size)
        f_body_bold = get_font("archivo_bold", body_size)
        altura = _medir_altura_conteudo(draw, pratos, f_body_reg, f_body_bold, line_height, dish_gap_extra, content_width)
        preenchimento = altura / available_height if available_height else 1
        no_teto = body_size >= MAX_BODY_SIZE
        no_piso = body_size <= MIN_BODY_SIZE
        if (0.82 <= preenchimento <= 1.0) or (preenchimento > 1.0 and no_piso) or (preenchimento < 0.82 and no_teto):
            break
        fator = (available_height * 0.9) / altura
        novo_tam = int(round(body_size * fator))
        body_size = max(MIN_BODY_SIZE, min(MAX_BODY_SIZE, novo_tam))
        line_height = max(int(NOM_LINE_HEIGHT * (body_size / NOM_BODY_SIZE)), body_size + 8)
        dish_gap_extra = max(int(NOM_DISH_GAP_EXTRA * (body_size / NOM_BODY_SIZE)), 6)

    f_body_reg = get_font("archivo_regular", body_size)
    f_body_bold = get_font("archivo_bold", body_size)

    # ---- Distribui o espaço sobrando igualmente entre os pratos ---------
    # (em vez de um espaço fixo, o "respiro" entre pratos estica ou encolhe
    # para que o conteúdo sempre preencha bonito o espaço até a tarja,
    # como no modelo original, em vez de deixar uma sobra só no final)
    total_linhas = 0
    for prato in pratos:
        runs = dish_to_runs(prato.get("nome", ""), prato.get("descricao", ""))
        total_linhas += len(wrap_runs(draw, runs, f_body_reg, f_body_bold, content_width))
    altura_so_linhas = total_linhas * line_height
    num_gaps = max(len(pratos) - 1, 0)
    if num_gaps > 0:
        gap_ideal = (available_height - altura_so_linhas) / num_gaps
        dish_gap_extra = max(dish_gap_extra, min(gap_ideal, dish_gap_extra * 4))

    y = dishes_top
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
    banner_top = int(max(BANNER_TOP_TARGET, y + MIN_GAP_BEFORE_BANNER))

    # ---- Tarja amarela no rodapé ---------------------------------------
    f_rodape = get_font("archivo_regular", 25)
    tracking_rodape = 1.6
    banner_bottom = banner_top + BANNER_HEIGHT
    draw.rectangle(
        [DIVIDER_LEFT, banner_top, DIVIDER_RIGHT, banner_bottom],
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
        try:
            logo = Image.open(logo_path).convert("RGBA")
            logo_w = 300
            ratio = logo_w / logo.width
            logo_h = int(logo.height * ratio)

            # se não couber no espaço abaixo da tarja, encolhe a logo em vez
            # de empurrá-la pra cima (o que antes fazia ela sobrepor a tarja)
            espaco_disponivel = (CANVAS_H - MARGIN - 10) - (banner_bottom + LOGO_GAP_AFTER_BANNER)
            if logo_h > espaco_disponivel > 0:
                fator = espaco_disponivel / logo_h
                logo_w = max(80, int(logo_w * fator))
                ratio = logo_w / logo.width
                logo_h = int(logo.height * ratio)

            logo = logo.resize((logo_w, logo_h), Image.LANCZOS)
            logo_x = center_x - logo_w // 2
            logo_y = banner_bottom + LOGO_GAP_AFTER_BANNER
            # garante que a logo nunca ultrapasse a moldura inferior
            max_logo_y = CANVAS_H - MARGIN - logo_h - 10
            logo_y = min(logo_y, max_logo_y)
            img.paste(logo, (int(logo_x), int(logo_y)), logo)
        except Exception:
            # logo ausente ou corrompida: segue sem travar a geracao da imagem
            pass

    if output_path:
        img.save(output_path, "PNG")

    return img
