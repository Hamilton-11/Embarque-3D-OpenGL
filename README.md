# Embarque 3D — Ônibus e Boneco de Blocos

Trabalho de Computação Gráfica: cena 3D interativa criada com **Python, Pygame e PyOpenGL**.

## Temas
- **12 — Ônibus de brinquedo**
- **20 — Boneco de blocos**

**Integrantes:** [PREENCHER NOME DO INTEGRANTE 1] e [PREENCHER NOME DO INTEGRANTE 2].

## História e interação
O boneco espera no ponto; o ônibus chega e para; a porta desliza; o boneco caminha até a entrada; o embarque é representado de modo simbólico; a porta fecha; o ônibus parte. O ciclo de 18 segundos se repete. A animação depende do tempo decorrido (`dt`), não da taxa de quadros. As ações são coordenadas por fases (`phase`), não movimentos independentes.

## Instalação no Windows (VS Code)
1. Instale Python 3.11 ou 3.12 em https://www.python.org/downloads/ e marque **Add Python to PATH**. Instale a extensão **Python** no VS Code.
2. Extraia este ZIP, abra a pasta `embarque_3d` em **Arquivo > Abrir Pasta** no VS Code.
3. Abra **Terminal > Novo Terminal** e execute:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Se tiver Python 3.11, substitua `-3.12` por `-3.11`. Se o comando `py` não existir, tente `python -m venv .venv` e execute os demais comandos. É necessária placa de vídeo/driver com OpenGL 3.3.

## Controles
| Tecla | Função |
|---|---|
| Espaço | Pausar/retomar |
| Setas esquerda/direita ou A/D | Girar câmera |
| Setas cima/baixo ou W/S | Altura da câmera |
| Q / E | Aproximar / afastar câmera |
| + / - | Acelerar / reduzir animação |
| R | Reiniciar sequência |
| Esc | Sair |

## Arquitetura e conceitos
- `main.py`: `Renderer` configura VAO/VBO, shaders, textura e framebuffer; `bus`, `character`, `environment` constroem modelos a partir de cubos; `phase` coordena os movimentos; `main` executa o loop de eventos, delta time e câmera.
- `shaders/scene.vert`: atributos `aPos`, `aNormal`, `aUV`; uniforms `model`, `view`, `projection`, `lightSpace`; transformações e normais.
- `shaders/scene.frag`: luz direcional, materiais coloridos, textura e filtro PCF 3×3 para sombra.
- `shaders/depth.vert` e `depth.frag`: passe de profundidade do **shadow mapping**. A textura de profundidade é produzida do ponto de vista da luz e consultada no passe principal.
- `assets/piso.png`: textura gerada pelo próprio programa na primeira execução, com padrão de piso. Não usa imagem de terceiros.
- **Sombreamento** é a variação de brilho de cada superfície segundo a normal e a luz. **Sombra projetada** ocorre quando a profundidade indica que outro objeto bloqueia a luz.
- Transformações hierárquicas: matriz do ônibus aplicada a corpo, janelas, rodas e porta; matriz do personagem aplicada aos membros articulados.

## Contribuições individuais (preencher conforme o trabalho real)
- Integrante 1: [descrever contribuições efetivas].
- Integrante 2: [descrever contribuições efetivas].

## Uso de inteligência artificial
**Ferramenta:** ChatGPT (OpenAI). **Finalidade:** auxílio na elaboração inicial do código, shaders, organização dos arquivos e documentação. **Trechos apoiados:** implementação inicial de `main.py`, shaders e README. A dupla deve executar, testar, revisar, compreender e ajustar o material antes da entrega.

## Fontes
- STEMKOSKI, Lee; PASCALE, Michael. *Developing Graphics Frameworks with Python and OpenGL*. CRC Press, 2022. DOI: 10.1201/9781003181378. Referência conceitual; implementação própria simplificada, não cópia do framework original.
- Documentação oficial: https://www.pygame.org/docs/ e https://pyopengl.sourceforge.net/documentation/index.html

## GitHub
Crie um repositório vazio no GitHub, abra o terminal nesta pasta e execute (substitua a URL):

```powershell
git init
git add .
git commit -m "Projeto Embarque 3D - Onibus e Boneco"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/embarque-3d.git
git push -u origin main
```

Se o terminal disser que `git` não foi encontrado, instale o Git em https://git-scm.com/downloads e reinicie o VS Code. O GitHub pode pedir autenticação.

## Observação de compatibilidade
O código requer um contexto OpenGL 3.3 Core e não foi validado nesta máquina com janela gráfica/driver de GPU. Execute no seu computador e relate qualquer erro para ajuste.
