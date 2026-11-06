# Pratica 2 - a figurinha no SEU bucket (cole no lambda_function.py do console).
#
# Cole este arquivo inteiro no editor da Lambda, no console da AWS.
# Ele nao precisa de nenhuma biblioteca extra: so Python puro.
#
# O que ele faz:
#   1. Recebe o aviso do S3 de que chegou um arquivo em uploads/
#   2. Baixa a foto
#   3. Monta uma figurinha (um arquivo SVG, com a foto dentro)
#   4. Grava a figurinha em stickers/, no mesmo bucket (se ainda nao existir)
#
# stickers/ fica FORA de uploads/. Se a funcao gravasse em uploads/, cada
# figurinha nova dispararia a funcao de novo, sem fim.

import base64
import hashlib
import html
import re
import urllib.parse
from pathlib import PurePosixPath

import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")

LIMITE_BYTES = 5 * 1024 * 1024  # 5 MB


def lambda_handler(event, context):
    for record in event["Records"]:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        print(f"chegou: {key}")

        foto = s3.get_object(Bucket=bucket, Key=key)["Body"].read()

        if len(foto) > LIMITE_BYTES:
            print(f"ignorado: {len(foto)} bytes passa do limite de 5 MB")
            continue
        if image_mime(foto) is None:
            print("ignorado: o arquivo nao e uma imagem JPG, PNG ou WEBP")
            continue

        sid = sticker_id(foto)
        destino = "stickers/" + PurePosixPath(key).stem + ".svg"
        # Preserve figurinhas antigas ao publicar uma nova regra de raridade.
        try:
            s3.head_object(Bucket=bucket, Key=destino)
        except ClientError as err:
            if err.response["Error"]["Code"] not in ("404", "NoSuchKey", "NotFound"):
                raise
        else:
            print(f"figurinha existente mantida: {destino}")
            continue

        raridade = rarity_for(sid)
        nome = display_name(key)
        svg = make_sticker_svg(foto, nome, raridade, sticker_number(sid))

        s3.put_object(
            Bucket=bucket,
            Key=destino,
            Body=svg.encode("utf-8"),
            ContentType="image/svg+xml",
        )
        print(f"figurinha criada: {destino} ({raridade[1]})")

    return {"ok": True}


# ---------------------------------------------------------------------------
# Daqui para baixo: como a figurinha e desenhada. Quer personalizar? Veja palettes, silhouettes e os ornamentos abaixo.
# ---------------------------------------------------------------------------

# (nome, rotulo, cor)
COMMON = ("common", "COMUM", "#879196")
RARE = ("rare", "RARA", "#00A1C9")
LEGENDARY = ("legendary", "LENDARIA", "#FF9900")


def image_mime(content):
    """Descobre o tipo da imagem pelos primeiros bytes, nao pela extensao."""
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def sticker_id(content):
    """A mesma foto sempre gera o mesmo id."""
    return hashlib.sha256(content).hexdigest()[:16]


def rarity_for(sid):
    """Raridade estavel da foto: 25% lendaria, 25% rara, 50% comum."""
    roll = int(sid[:8], 16) / 0xFFFFFFFF
    if roll >= 0.75:
        return LEGENDARY
    if roll >= 0.50:
        return RARE
    return COMMON

def sticker_number(sid):
    return int(sid[8:14], 16) % 1000


def display_name(key):
    """'uploads/ana_maria-silva.jpg' vira 'Ana Maria Silva'."""
    raw = urllib.parse.unquote(PurePosixPath(key).stem)
    clean = re.sub(r"[_\-.]+", " ", raw).strip()
    clean = re.sub(r"\s+", " ", clean).title()
    return (clean or "Anonimo")[:18]

def make_sticker_svg(photo, name, rarity, number):
    """Três acabamentos desenhados em vetor, sem fontes ou imagens externas."""
    key, label = rarity[0], rarity[1]
    seed = hashlib.sha256(photo).hexdigest()
    safe_name = html.escape(name)
    data = base64.b64encode(photo).decode("ascii")
    mime = image_mime(photo) or "image/jpeg"
    name_size = min(42, 750 // max(1, len(name)))
    palettes = {
        "common": ("#eee4ca", "#a6b795", "#435e4c", "#182a24"),
        "rare": ("#e1fcff", "#64d9f4", "#4160c4", "#0d1734"),
        "legendary": ("#fff3ce", "#edc272", "#91612b", "#241622"),
    }
    light, main, dark, background = palettes[key]
    # Costuras, circuitos e gravuras distinguem os acabamentos.
    silhouettes = {
        "common": '<rect id="shape" x="64" y="136" width="472" height="414" rx="6"/>',
        "rare": '<path id="shape" d="M96 132H504L538 166V516L504 550H96L62 516V166Z"/>',
        "legendary": '<path id="shape" d="M68 550V232Q68 132 300 112Q532 132 532 232V550Z"/>',
    }
    stars = {"common": 1, "rare": 2, "legendary": 3}[key]
    marks = ''.join(f'<use href="#star" x="{300+(i-(stars-1)/2)*30-10}" y="721"/>' for i in range(stars))
    # Serial e pequenas marcas variam com a foto sem alterar a raridade.
    barcode = ''.join(f'<path d="M{74+i*5} 753v{10+int(c,16)%9}" stroke="{main}" stroke-width="{1+int(c,16)%2}"/>' for i,c in enumerate(seed[:22]))
    ornament, emblem, sweep = '', '', ''
    if key == 'common':
        ornament = f'''<g fill="none" stroke="{main}">
<rect x="28" y="28" width="544" height="744" rx="12" stroke-dasharray="5 6" opacity=".55"/>
<path d="M48 112H552M48 574H552" stroke-width="2"/>
<path d="M48 152v-32h32M520 120h32v32M48 530v32h32M520 562h32v-32" stroke-width="3"/>
<path d="M74 595h85m282 0h85" opacity=".6"/>
</g>'''
        for x in (44,556):
            for y in (44,756):
                ornament += f'<circle cx="{x}" cy="{y}" r="5" fill="{dark}" stroke="{main}"/><path d="M{x-2} {y+2}l4-4" stroke="{light}"/>'
        emblem = f'''<g transform="translate(300 104)" fill="{background}" stroke="{main}" stroke-width="2">
<circle r="25"/><path d="M0-19L5-5 19 0 5 5 0 19-5 5-19 0-5-5Z" fill="{main}"/>
<circle r="4" fill="{light}"/></g>'''
        subtitle = 'EXPLORADOR · PRIMEIRA EXPEDIÇÃO'
    elif key == 'rare':
        # Circuitos duplos e terminais ao longo das laterais.
        for side in (0,1):
            transform = '' if side == 0 else 'translate(600 0) scale(-1 1)'
            ornament += f'<g transform="{transform}" fill="none" stroke="{main}" stroke-width="1.5">'
            for i in range(6):
                y=176+i*62
                ornament += f'<path d="M24 {y-26}v30l16 16v28"/><circle cx="40" cy="{y+48}" r="3" fill="{background}"/><path d="M49 {y-12}v24" opacity=".4"/>'
            ornament += '</g>'
        ornament += f'''<g fill="none" stroke="{main}"><path d="M28 120V28H190l16 16h188l16-16h162v92M28 670v102h164l14-14h188l14 14h164V670" stroke-width="2"/>
<path d="M76 122H174m252 0h98M76 560H174m252 0h98" stroke-width="4"/>
<path d="M52 600l14-14h130m208 0h130l14 14"/></g>'''
        emblem = f'''<g transform="translate(300 104)" stroke="{light}" stroke-width="2">
<path d="M0-32L32-16V16L0 32-32 16V-16Z" fill="{dark}"/>
<path d="M-17-9L0-19 17-9 0 20Z M-17-9H17M0-19V20" fill="{background}"/>
</g>'''
        subtitle = 'ARQUITETO · CONEXÃO EXTRAORDINÁRIA'
    else:
        # Gravura radial, cantoneiras espelhadas e folhas de louro.
        for i in range(60):
            ornament += f'<path d="M300 76V90" transform="rotate({i*6} 300 340)" stroke="{main}" opacity=".35"/>'
        for transform in ('', 'translate(600 0) scale(-1 1)', 'translate(0 800) scale(1 -1)', 'translate(600 800) scale(-1 -1)'):
            ornament += f'''<g transform="{transform}" fill="none" stroke="{main}">
<path d="M28 166V28H166M36 154V36H154" stroke-width="2"/>
<path d="M45 124C78 110 30 68 72 60S108 48 124 45M48 98Q98 98 98 48M46 46Q68 42 74 74Q42 68 46 46Z"/>
<path d="M48 48L58 51 51 58Z" fill="{light}"/>
</g>'''
        for side in (0,1):
            transform = '' if side == 0 else 'translate(600 0) scale(-1 1)'
            ornament += f'<g transform="{transform}" fill="{main}" stroke="{dark}" stroke-width=".5"><path d="M52 526Q12 380 50 242" fill="none" stroke="{main}" stroke-width="2"/>'
            for i in range(10):
                y=270+i*24
                ornament += f'<path d="M35 {y}q-22-8-16-25q18 4 16 25q19-3 20-19q-17-1-20 19Z"/>'
            ornament += '</g>'
        emblem = f'''<g transform="translate(300 106)">
<path d="M-60 2L-42-17-22-7 0-32 22-7 42-17 60 2 43 29H-43Z" fill="url(#metal)" stroke="{light}"/>
<path d="M-34-8L-26 12H26L34-8M0-22V12" fill="none" stroke="{dark}" stroke-width="3"/>
<path d="M0-10L7 0 0 10-7 0Z" fill="{background}"/>
<path d="M-38 22H38" stroke="{dark}" stroke-width="3"/>
</g>'''
        sweep = '<g id="reflection"><path d="M-160 100h80L-240 560h-80Z" fill="url(#shine)"><animateTransform attributeName="transform" type="translate" values="0 0;900 0;900 0" keyTimes="0;.4;1" dur="6s" repeatCount="indefinite"/></path></g>'
        subtitle = 'LENDA · ALÉM DO IMPOSSÍVEL'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="800" viewBox="0 0 600 800">
<title>Figurinha de {safe_name} — {label}</title>
<defs>
<style>@media(prefers-reduced-motion:reduce) {{ #reflection {{display:none}} }}</style>
<linearGradient id="metal" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{dark}"/><stop offset=".22" stop-color="{light}"/><stop offset=".42" stop-color="{main}"/><stop offset=".55" stop-color="{light}"/><stop offset=".7" stop-color="{dark}"/><stop offset="1" stop-color="{main}"/></linearGradient>
<radialGradient id="field"><stop stop-color="{dark}"/><stop offset="1" stop-color="{background}"/></radialGradient>
<linearGradient id="shade" x2="0" y2="1"><stop offset=".65" stop-color="{background}" stop-opacity="0"/><stop offset="1" stop-color="{background}" stop-opacity=".7"/></linearGradient>
<linearGradient id="shine"><stop stop-color="white" stop-opacity="0"/><stop offset=".5" stop-color="white" stop-opacity=".4"/><stop offset="1" stop-color="white" stop-opacity="0"/></linearGradient>
<pattern id="engraving" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M0 8L8 0" stroke="{main}" stroke-width=".4" opacity=".15"/></pattern>
{silhouettes[key]}<clipPath id="photo"><use href="#shape"/></clipPath>
<path id="star" d="M10 0L13 7 21 8 15 13 17 21 10 17 3 21 5 13-1 8 7 7Z" fill="url(#metal)"/>
</defs>
<rect width="600" height="800" rx="26" fill="url(#metal)"/>
<rect x="8" y="8" width="584" height="784" rx="20" fill="{background}" stroke="{light}" stroke-width=".6"/>
<rect x="18" y="18" width="564" height="764" rx="14" fill="url(#field)" stroke="{main}" stroke-width=".7"/>
<rect x="18" y="18" width="564" height="764" rx="14" fill="url(#engraving)"/>
{ornament}
<text x="300" y="59" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" letter-spacing="2.5" fill="{light}">λ LAMBDA · S3 · SERVERLESS</text>
<use href="#shape" fill="{background}" stroke="url(#metal)" stroke-width="14"/>
<image href="data:{mime};base64,{data}" x="62" y="112" width="476" height="438" preserveAspectRatio="xMidYMid slice" clip-path="url(#photo)"/>
<g clip-path="url(#photo)"><rect x="62" y="112" width="476" height="438" fill="url(#shade)"/>{sweep}</g>
<use href="#shape" fill="none" stroke="{light}" stroke-width="1"/>
{emblem}
<path d="M256 532H344L354 549 344 566H256L246 549Z" fill="{background}" stroke="{main}" stroke-width="2"/>
<text x="300" y="557" text-anchor="middle" font-family="monospace" font-size="22" letter-spacing="4" fill="{light}">{number:03d}</text>
<text x="300" y="622" text-anchor="middle" font-family="Arial,sans-serif" font-size="{name_size}" font-weight="bold" fill="{light}">{safe_name}</text>
<text x="300" y="648" text-anchor="middle" font-family="Arial,sans-serif" font-size="10" letter-spacing="2" fill="{main}">{subtitle}</text>
<path d="M166 680L180 666H420L434 680 420 701H180Z" fill="url(#metal)"/>
<path d="M183 670H417M183 697H417" stroke="{background}" stroke-width=".6"/>
<text x="300" y="690" text-anchor="middle" font-family="Arial,sans-serif" font-size="20" font-weight="bold" letter-spacing="5" fill="{background}">{label}</text>
{marks}
{barcode}
<text x="526" y="765" text-anchor="end" font-family="monospace" font-size="9" letter-spacing="1" fill="{main}">SÉRIE 01 / {seed[:8].upper()}</text>
</svg>'''
