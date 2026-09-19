# Gerador de Cardápio — Empório do Nono

Sisteminha simples (Flask + Pillow) para gerar automaticamente a arte
"Almoço do Dia" a partir do texto que o restaurante te manda. Você cola os
pratos num único campo, clica em "Montar cardápio" e recebe a imagem já
pronta, no layout e nas cores do modelo original — direto na tela, sem
precisar salvar nada em disco.

## 1. Instalar

Precisa de Python 3.9+ instalado. No terminal, dentro da pasta do projeto:

```bash
pip install -r requirements.txt
```

(Opcional, só se for usar a revisão por IA — veja a seção 3):
```bash
pip install python-dotenv
```

## 2. Colocar as fontes oficiais (importante para o visual ficar idêntico)

O sistema já funciona sem isso (usa fontes parecidas como reserva), mas para
ficar **pixel a pixel igual** ao modelo original, baixe as 3 famílias abaixo,
gratuitas no Google Fonts, e salve os arquivos `.ttf` dentro da pasta
`fonts/` **com estes nomes exatos**:

| Uso no cardápio                                   | Arquivo esperado                        | Baixar em |
|----------------------------------------------------|------------------------------------------|-----------|
| Selo "— DESDE 1999 · BARÃO GERALDO —"              | `fonts/SpecialElite-Regular.ttf`         | fonts.google.com/specimen/Special+Elite |
| Título "Almoço" / "Dia" (peso Black)               | `fonts/PlayfairDisplay-Black.ttf`        | fonts.google.com/specimen/Playfair+Display |
| Palavra "do" no título (Light Italic)              | `fonts/PlayfairDisplay-LightItalic.ttf`  | fonts.google.com/specimen/Playfair+Display |
| Nome dos pratos, em negrito                        | `fonts/Archivo-Bold.ttf`                 | fonts.google.com/specimen/Archivo |
| Descrição dos pratos e tarja amarela, regular      | `fonts/Archivo-Regular.ttf`              | fonts.google.com/specimen/Archivo |

Basta baixar o `.zip` de cada família no Google Fonts, abrir a pasta
`static/` dentro do zip e copiar o arquivo `.ttf` certo para dentro de
`fonts/`, renomeando conforme a tabela acima.

## 3. (Opcional) Revisão do texto por IA

O campo "O Menu" aceita o texto exatamente como o restaurante manda —
com abreviações, erros de digitação, etc. Se você configurar uma chave da
API da Anthropic, o sistema usa a IA para:
- corrigir erros de digitação/português;
- separar corretamente o **nome do prato** (negrito) da **descrição/acompanhamentos** (peso normal);
- expandir abreviações óbvias (ex.: "PF" → "P.F.").

Para ativar:
1. Copie `.env.example` para `.env`
2. Cole sua chave (gerada em https://console.anthropic.com/) na linha `ANTHROPIC_API_KEY=`

Sem isso, o sistema usa um parser local baseado em regras (funciona bem
para o formato mais comum: "Nome do prato - descrição..." ou "Nome do prato
com/ao/no acompanhamento...").

## 4. Rodar localmente

```bash
python app.py
```

Acesse **http://127.0.0.1:5000** no navegador (se `localhost` não abrir por
algum motivo do seu sistema, use o endereço `127.0.0.1` mesmo), cole os
pratos do dia no campo **O Menu** e clique em **Montar cardápio**. A imagem
aparece na tela com um botão para baixar o PNG (pronto para postar no Story).

### Não abriu nada no navegador? Checklist rápido

1. Confirme que está **dentro da pasta do projeto** no terminal (`cd menu-gerador`)
   antes de rodar `python app.py`.
2. Rode `pip install -r requirements.txt` e veja se termina sem erro. Se
   aparecer `ModuleNotFoundError: No module named 'flask'`, é porque esse
   passo não rodou direito — rode de novo e leia a saída.
3. Depois de `python app.py`, o terminal precisa mostrar algo como:
   ```
   * Running on http://127.0.0.1:5000
   ```
   Se o terminal fechar sozinho ou mostrar um erro (`Traceback...`), é isso
   que impede o site de abrir — copie a mensagem de erro para investigar.
4. Use exatamente `http://127.0.0.1:5000` (não `https://`) no navegador.
5. Windows: se o Firewall perguntar se permite o Python acessar a rede,
   clique em **Permitir**.

## 5. Publicar na Vercel

O projeto já vem pronto para a Vercel, na estrutura que ela espera hoje em
dia para funções Python:

```
menu-gerador/
├── api/
│   └── index.py       -> ponto de entrada que a Vercel executa
├── app.py              -> o app Flask de verdade (usado local e na Vercel)
├── vercel.json         -> manda toda rota para api/index.py e garante que
│                          templates/, static/ e fonts/ vão junto no deploy
└── ...
```

Todo o app roda em um único endpoint (registrado tanto em `/` quanto em
`/api/index`), porque o runtime Python da Vercel entrega ao Flask o caminho
de destino do rewrite, não o caminho original da URL — registrando os dois,
funciona nos dois ambientes sem diferença de comportamento. A imagem gerada
volta embutida na própria página (base64), então não há escrita em disco em
nenhum momento — evita de vez os problemas de sistema de arquivos
somente-leitura do ambiente serverless.

Depois de subir esses arquivos pro GitHub (seção 6) e importar o repositório
na Vercel, ela detecta tudo sozinha — não precisa mudar nenhuma configuração
na tela de deploy. Se algo falhar, veja os logs em **Project → Deployments
→ (clique no deployment) → Runtime Logs** dentro do painel da Vercel; me
manda o texto ou print do erro que eu ajusto.

## 6. Subir no GitHub (sem usar linha de comando)

Como sua máquina não tem o Git instalado, o jeito mais seguro de manter a
estrutura de pastas correta (a pasta `api/` precisa continuar sendo uma
pasta de verdade dentro do repositório) é usar o **GitHub Desktop**:

1. Baixe e instale: https://desktop.github.com/
2. Abra o app e faça login com sua conta do GitHub
3. Menu **File → Add Local Repository** → selecione a pasta `menu-gerador`
   (se ele avisar que não é um repositório git ainda, clique em
   **create a repository** — ele faz isso automaticamente)
4. Escreva uma mensagem de commit (ex.: "Corrige rotas para Vercel") e
   clique em **Commit to main**
5. Clique em **Publish repository** (primeira vez) ou **Push origin**
   (se o repositório já existir)

Isso garante que todas as subpastas (`api/`, `templates/`, `static/`,
`fonts/`) subam exatamente como estão, sem risco de "achatar" a estrutura
— o que costuma acontecer quando se arrasta arquivo por arquivo direto
pela página do GitHub no navegador.

Se preferir mesmo assim usar o upload pelo navegador (github.com → seu
repositório → **Add file → Upload files**), arraste a **pasta inteira**
`menu-gerador` de uma vez (não os arquivos individualmente) — navegadores
baseados em Chrome/Edge preservam a estrutura de pastas ao arrastar uma
pasta. Depois confira na aba **Code** do repositório se o `vercel.json`
está na raiz (não dentro de outra pasta) e se existe uma pasta `api`
contendo `index.py` dentro dela.

A Vercel redesploya automaticamente a cada push/upload novo.

## Estrutura do projeto

```
menu-gerador/
├── api/
│   └── index.py          -> ponto de entrada que a Vercel executa
├── app.py                 -> servidor Flask (backend, roda local e na Vercel)
├── menu_parser.py         -> interpreta o texto colado (IA ou regras locais)
├── menu_render.py         -> desenha a arte final (PIL) com cores/fontes/layout
├── templates/index.html   -> a tela principal, com o campo "O Menu" e o botão
├── static/logo.png        -> logo do Empório do Nono
├── fonts/                 -> coloque aqui os .ttf oficiais (veja seção 2)
├── vercel.json            -> configuração de deploy da Vercel
└── requirements.txt
```

## Personalização rápida

- Trocar o texto do selo, título ou tarja amarela: são parâmetros da função
  `gerar_cardapio()` em `menu_render.py`.
- Cores, margens e tamanhos de fonte: todos nomeados no topo/meio de
  `menu_render.py` (`COR_FUNDO`, `COR_BORDA`, `COR_TEXTO`, `COR_AMARELO`,
  `TEXT_LEFT`, `DIVIDER_Y`, etc.) — já calibrados para bater com o modelo
  original.
- Se algum dia o menu vier muito grande (muitos pratos), o sistema reduz
  automaticamente o tamanho da fonte do corpo até caber sem sobrepor a
  tarja amarela.
