# A-Maze-ing — Guia de estudo

Este guia explica **como o projeto foi feito**, **porque foi feito assim** e
**que conceitos tens de dominar** para o defender na avaliação. Lembra-te do
que o subject diz no capítulo de IA: na defesa tens de conseguir explicar
cada linha e, provavelmente, fazer uma pequena modificação ao vivo. Usa este
guia para estudar, não apenas para ler.

---

## 1. O que o exercício pede (resumo)

| Requisito | Onde está resolvido |
|-----------|---------------------|
| `python3 a_maze_ing.py config.txt` | [a_maze_ing.py](a_maze_ing.py) |
| Ficheiro de config `KEY=VALUE`, `#` = comentário | [amazeing/config.py](amazeing/config.py) |
| Labirinto aleatório e reproduzível (seed) | `random.Random(seed)` em [mazegen/generator.py](mazegen/generator.py) |
| Paredes coerentes entre vizinhos | `_remove_wall` abre as duas paredes ao mesmo tempo |
| Bordas exteriores fechadas | nunca se abre uma parede para fora da grelha |
| Corredores com no máximo 2 de largura (proibido 3x3 aberto) | `_creates_open_area` / `_block_open` |
| "42" desenhado com células fechadas | `PATTERN_42` + `_place_pattern` |
| `PERFECT=True` → um só caminho | backtracker / Prim, que geram uma árvore |
| `PERFECT=False` → tabuleiro Pac-Man | `_braid` + `_ensure_loops` |
| Saída em hexadecimal + entrada/saída/caminho | [amazeing/output.py](amazeing/output.py) |
| Visualização com interação | [amazeing/display.py](amazeing/display.py) + menu |
| Classe reutilizável, empacotada com pip | pacote `mazegen/` + [pyproject.toml](pyproject.toml) |
| Makefile, flake8, mypy, docstrings, type hints | [Makefile](Makefile) |
| README, LICENSE.md | [README.md](README.md), [LICENSE.md](LICENSE.md) |

---

## 2. Arquitetura — porque está dividido assim

```
a_maze_ing.py          ← "cola": lê config, gera, grava, mostra, menu
amazeing/              ← código ESPECÍFICO deste programa
    config.py          ← lê e valida o ficheiro de configuração
    output.py          ← escreve o ficheiro em hexadecimal
    display.py         ← desenha no terminal com cores ANSI
mazegen/               ← código REUTILIZÁVEL (vai para o .whl)
    generator.py       ← classe MazeGenerator
    __init__.py        ← o que o pacote exporta
tests/                 ← testes pytest (não são avaliados)
```

A ideia principal é a **separação de responsabilidades**. O `mazegen` não
sabe nada de ficheiros de config, de terminais nem de cores: só gera e
resolve labirintos. É por isso que pode ser reutilizado num projeto futuro
(o subject sugere que haverá um jogo tipo Pac-Man). O resto do programa
*usa* o `mazegen`, mas o `mazegen` não depende do resto.

> **Pergunta típica na defesa:** "Porque é que o parser de config não está
> dentro da classe?" → Porque um projeto futuro pode querer criar labirintos
> a partir de outra fonte (argumentos, rede, GUI). A classe recebe parâmetros
> Python normais.

---

## 3. Como o labirinto é representado

### 3.1 A grelha e as coordenadas

* `grid[y][x]`: primeiro a **linha** (y) e depois a **coluna** (x).
  É a armadilha mais comum. O subject usa `(x, y)` nas coordenadas, por isso
  `ENTRY=3,1` é a coluna 3, linha 1, ou seja `grid[1][3]`.
* Cada célula é **um inteiro de 4 bits**. Cada bit é uma parede:

| Bit | Valor | Parede |
|-----|-------|--------|
| 0 | 1 | Norte |
| 1 | 2 | Este |
| 2 | 4 | Sul |
| 3 | 8 | Oeste |

Bit a 1 = parede **fechada**. Exemplos:

* `F` = 15 = `1111` → as 4 paredes fechadas (célula do "42", ou estado inicial).
* `A` = 10 = `1010` → Este e Oeste fechados, ou seja um corredor vertical.
* `3` = `0011` → Norte e Este fechados, aberto a Sul e Oeste.

### 3.2 Operações com bits (tens de saber de cor)

```python
cell & EAST          # != 0 se a parede Este está fechada  (testar)
cell &= ~EAST        # abre a parede Este                  (limpar bit)
cell |= EAST         # fecha a parede Este                 (pôr bit)
f"{cell:X}"          # inteiro -> dígito hexadecimal maiúsculo
int("A", 16)         # dígito hexadecimal -> inteiro
```

### 3.3 Coerência das paredes

A parede Este da célula (x, y) **é a mesma** que a parede Oeste da célula
(x+1, y). Por isso existe o dicionário `OPPOSITE` e a função `_remove_wall`
altera **as duas células** de uma vez. Se só alterasses uma, o
`maze_analyzer.py` diria "INCOHERENT walls".

---

## 4. Teoria de grafos: a chave do projeto

Vê o labirinto como um **grafo**:

* **vértices** (nós) = células;
* **arestas** = passagens abertas entre duas células vizinhas.

### 4.1 Labirinto perfeito = árvore geradora (spanning tree)

Uma **árvore** é um grafo **conexo** e **sem ciclos**. Uma *spanning tree*
liga todos os vértices usando exatamente `V − 1` arestas.

* Conexo → todas as células são alcançáveis (sem células isoladas).
* Sem ciclos → entre duas células só existe **um** caminho.

Isto é exatamente a definição de labirinto perfeito do subject. Qualquer
algoritmo que construa uma árvore geradora aleatória (DFS, Prim, Kruskal,
Wilson, Aldous-Broder...) gera um labirinto perfeito.

### 4.2 Contar ciclos: `E − V + 1`

Num grafo conexo, o número de **ciclos independentes** (o "número ciclomático")
é `arestas − vértices + 1`.

* Árvore: E = V − 1, logo 0 ciclos, logo é perfeito.
* Cada parede extra que abres num labirinto perfeito acrescenta **1** ciclo.

É exatamente o que o `maze_analyzer.py` calcula em `loops`, e o que
`_count_loops` faz no gerador para garantir pelo menos 2 rotas independentes.

### 4.3 Porque é que um labirinto perfeito nunca tem uma área 3x3 aberta

Um bloco 2x2 totalmente aberto já forma um ciclo (as 4 células em quadrado).
Uma árvore não tem ciclos, por isso nunca tem um 2x2 aberto e, muito menos, um
3x3. No modo perfeito a regra dos "corredores ≤ 2" cumpre-se sozinha. Só no
modo Pac-Man, onde abrimos paredes extra, é preciso verificar.

---

## 5. Os algoritmos usados

### 5.1 Recursive backtracker (DFS aleatório): o padrão

```
começar na entrada, marcá-la como visitada, pô-la na pilha
enquanto a pilha não estiver vazia:
    célula = topo da pilha
    vizinhos = vizinhos NÃO visitados e que NÃO são do "42"
    se não há vizinhos: tirar da pilha (backtrack)
    senão: escolher um ao acaso, derrubar a parede entre os dois,
           marcá-lo como visitado e empilhá-lo
```

* É feito com uma **pilha explícita** (`list`) em vez de recursão, porque o
  Python tem um limite de recursão (~1000). Um labirinto 100x100 tem 10 000
  células e uma recursão rebentaria com `RecursionError`.
* Complexidade: **O(V)**, porque cada célula entra e sai da pilha uma vez.
* Característica: corredores longos e sinuosos, poucos ramos.

### 5.2 Prim aleatório: o bónus "vários algoritmos"

```
visitadas = {entrada}; fronteira = paredes entre a entrada e os vizinhos
enquanto houver fronteira:
    tirar uma parede ao acaso da fronteira
    se a célula do outro lado já foi visitada: ignorar (criaria um ciclo)
    senão: derrubar a parede, visitar a célula, juntar as suas paredes
```

Característica: muitos ramos curtos, com aspeto "espinhoso". Também gera uma
árvore e, por isso, também é perfeito. O truque `frontier[i], frontier[-1] =
...; pop()` remove um elemento aleatório em O(1).

### 5.3 Modo Pac-Man: "braiding" (entrançar)

Um **beco sem saída** (dead-end) é uma célula com uma única abertura. O
subject pede que sejam raros (o bónus é ter zero). O método é:

1. gerar um labirinto perfeito;
2. percorrer as células numa ordem aleatória; para cada beco, abrir **uma**
   parede extra, de preferência para outro beco (assim resolve dois de uma
   vez);
3. antes de abrir, chamar `_creates_open_area`, que abre temporariamente a
   parede, verifica todos os blocos 3x3 que contêm as duas células e repõe o
   estado no `finally`;
4. no fim, `_ensure_loops(2)` garante pelo menos 2 ciclos (importante em
   labirintos pequenos).

Os únicos becos que ficam são as células "presas" dentro do desenho do "42"
(por exemplo, o buraco do 4). O analyzer chama-lhes "enclosed" e tolera-as,
porque não é possível abrir nenhuma parede delas sem ser para uma célula do
"42".

### 5.4 Caminho mais curto: BFS (busca em largura)

```
fila = [entrada]; pai = {entrada: None}
enquanto fila:
    c = fila.popleft()
    para cada vizinho aberto v ainda não visto: pai[v] = c; fila.append(v)
reconstruir o caminho a partir da saída seguindo pai[] e inverter
```

* Num grafo **sem pesos**, a BFS encontra sempre o caminho mais curto, porque
  explora por "camadas" de distância 0, 1, 2...
* A DFS **não** garante o caminho mais curto. No modo perfeito há só um
  caminho, mas no Pac-Man há vários.
* `collections.deque`: `popleft()` é O(1), enquanto `list.pop(0)` é O(n).
* Depois converte-se a sequência de células em letras N/E/S/W.

---

## 6. O padrão "42"

```
X.X.XXX      7 colunas x 5 linhas
X.X...X      a coluna do meio (índice 3) está sempre vazia
XXX.XXX
..X.X..
..X.XXX
```

* É colocado de forma a que a coluna vazia do meio fique **exatamente** sobre
  a célula central `(width // 2, height // 2)`, que é onde o jogador Pac-Man
  começa e que tem de ser um corredor aberto.
  `left = width // 2 - 3`, `top = height // 2 - 2`.
* Precisa de uma margem de pelo menos 1 célula à volta, para o resto do
  labirinto continuar ligado. Por isso o tamanho mínimo é **9x7**. Abaixo
  disso o padrão é omitido e é mostrada uma mensagem de erro, como o subject
  pede.
* Se a entrada ou a saída caírem em cima do "42", ele também é omitido.
* As células do "42" ficam com valor `F` e **nunca** são visitadas pelos
  algoritmos. O analyzer tolera-as como "isoladas".

---

## 7. Formato do ficheiro de saída

```
91395539555539513913     ← uma linha por linha do labirinto, 1 hex por célula
...
C4445455444546C55446
                         ← linha vazia
0,0                      ← entrada x,y
19,14                    ← saída x,y
SSSSSESWSSEEEE...        ← caminho mais curto
```

Todas as linhas terminam com `\n`, incluindo a última (é o `+ "\n"` em
`format_maze`). Verifica com:

```bash
python3 maze_analyzer.py maze.txt                     # verificação normal
python3 maze_analyzer.py maze.txt --max-dead-ends 0   # verificação do bónus
```

---

## 8. Visualização no terminal

* Usa **códigos de escape ANSI**: `\033[47m` muda a cor de fundo para branco
  e `\033[0m` repõe a cor. Duas espaços com cor de fundo formam um "bloco"
  quase quadrado.
* A imagem tem `(2*altura+1) x (2*largura+1)` "píxeis":
  * linha ímpar e coluna ímpar → célula;
  * linha ímpar e coluna par → parede vertical (Este/Oeste);
  * linha par e coluna ímpar → parede horizontal (Norte/Sul);
  * linha par e coluna par → "poste" (esquina), desenhado só se alguma
    parede lhe toca.
* `\033[H\033[2J` limpa o ecrã antes de redesenhar.
* O menu usa `input()`. `EOFError` (Ctrl+D) sai de forma limpa e
  `KeyboardInterrupt` (Ctrl+C) é apanhado no `__main__`.
* Se o stdin não for um terminal (`sys.stdin.isatty()` é falso), desenha uma
  vez e termina. Assim um teste automático com `< /dev/null` não fica
  bloqueado.

> **MiniLibX (opcional):** o subject aceita ASCII **ou** MLX. Optou-se pelo
> terminal para não haver dependências gráficas. Se quiseres a versão MLX,
> o `mlx-2.2.tgz` tem um wheel (`ubuntu/mlx-2.2-py3-none-any.whl`). Basta
> escrever um novo `display` que use a mesma `MazeGenerator`, e o resto não
> muda. Isso também é uma boa demonstração da separação de responsabilidades.

---

## 9. Python "profissional" exigido pelo subject

| Conceito | O que estudar | Onde está no código |
|----------|---------------|---------------------|
| **Type hints** | `int`, `List[...]`, `Tuple[...]`, `Optional[...]`, `Dict`, aliases (`Coord = Tuple[int, int]`) | todos os ficheiros |
| **mypy** | verificação estática; `--strict`, `--disallow-untyped-defs` | `make lint`, `make lint-strict` |
| **flake8 / PEP 8** | linhas ≤ 79 colunas, indentação, imports não usados | `make lint`, `.flake8` |
| **Docstrings (PEP 257)** | estilo Google: `Args:`, `Returns:`, `Raises:` | todas as funções |
| **Exceções** | `try/except/finally`, exceções próprias (`ConfigError`, `MazeError`, `OutputError`) | config.py, output.py, main |
| **Context managers** | `with open(...) as f:` fecha o ficheiro mesmo com erro | `read_pairs`, `write_maze` |
| **dataclasses** | `@dataclass` gera `__init__`, `__repr__`, `__eq__` | `Config` |
| **`random.Random(seed)`** | gerador pseudoaleatório *independente* e reproduzível (não mexe no `random` global) | `MazeGenerator` |
| **`collections.deque`** | fila eficiente para a BFS | `solution_cells` |
| **f-strings** | `f"{x:X}"` (formato hex) | `to_hex_lines` |
| **`if __name__ == "__main__"`** | o ficheiro pode ser executado ou importado | a_maze_ing.py |
| **Códigos de saída** | `sys.exit(0)` sucesso, `1` erro, `130` Ctrl+C | a_maze_ing.py |

### 9.1 Tratamento de erros: a regra de ouro

O subject diz que, se o programa crashar na avaliação, é considerado
**não funcional**. Por isso há três níveis:

1. **Validação**: `load_config` e `MazeGenerator._validate` rejeitam tudo o
   que é inválido com uma mensagem clara (chave em falta, chave duplicada,
   chave desconhecida, número inválido, coordenadas fora, entrada = saída,
   tamanho 0 ou > 1000, algoritmo desconhecido).
2. **Erros de sistema**: `FileNotFoundError`, `IsADirectoryError`,
   `PermissionError`, `UnicodeDecodeError` e `OSError` são convertidos em
   `ConfigError` / `OutputError`.
3. **Rede de segurança** no `__main__`: `except Exception` imprime a
   mensagem sem traceback.

Experimenta (todos dão uma mensagem limpa):

```bash
python3 a_maze_ing.py                  # sem argumentos
python3 a_maze_ing.py nao_existe.txt   # ficheiro inexistente
python3 a_maze_ing.py /tmp             # é um diretório
# config com EXIT=99,99, PERFECT=talvez, WIDTH=abc, OUTPUT_FILE=/root/x ...
```

---

## 10. Empacotamento (pip) e licença

### 10.1 `pyproject.toml`

É o ficheiro padrão moderno (PEP 517/518/621) que descreve um pacote Python:

* `[build-system]`: que ferramenta constrói o pacote (setuptools);
* `[project]`: nome `mazegen`, versão, descrição, README do pacote
  (`MAZEGEN.md`) e licença;
* `[tool.setuptools] packages = ["mazegen"]`: **só** o pacote `mazegen` vai
  para o wheel (o `amazeing/` e os testes ficam de fora).

```bash
python3 -m venv /tmp/v && /tmp/v/bin/pip install build   # na avaliação
python3 -m build            # cria dist/mazegen-1.0.0-py3-none-any.whl e .tar.gz
pip install mazegen-1.0.0-py3-none-any.whl
python3 -c "from mazegen import MazeGenerator"
```

* **`.whl` (wheel)**: pacote já "construído", que é só copiar e instalar.
* **`.tar.gz` (sdist)**: código-fonte, que o pip constrói na instalação.
* `py3-none-any` significa Python 3, sem ABI específica, qualquer
  plataforma (Python puro).

O `make build` gera os dois ficheiros e copia-os para a raiz, que é onde o
subject os exige.

### 10.2 Licença MIT

Foi escolhida a **MIT** porque é curta, permissiva e permite explicitamente
usar, copiar, modificar e distribuir (o subject exige que o projeto futuro a
possa reutilizar). A única condição é manter o aviso de copyright. Conhece as
alternativas para a defesa:

* **MIT / BSD / Apache-2.0**: permissivas. Apache-2.0 acrescenta uma
  cláusula sobre patentes.
* **GPL**: *copyleft*. Quem distribuir uma obra derivada tem de a publicar
  também sob GPL.
* **Sem licença**: por defeito, *todos os direitos reservados*, e ninguém
  pode legalmente reutilizar o código.

---

## 11. Makefile

| Regra | O que faz |
|-------|-----------|
| `install` | `pip install -r requirements.txt` (flake8, mypy, pytest, build) |
| `run` | `python3 a_maze_ing.py config.txt` |
| `debug` | `python3 -m pdb a_maze_ing.py config.txt` |
| `lint` | `flake8 .` + `mypy` com as flags obrigatórias |
| `lint-strict` | `flake8 .` + `mypy . --strict` |
| `test` | `pytest` |
| `build` | `python -m build` e cópia do .whl/.tar.gz para a raiz |
| `clean` | apaga `__pycache__`, `.mypy_cache`, `build`, `dist`... |

**pdb**, os comandos essenciais: `n` (next), `s` (step into), `c` (continue),
`b ficheiro:linha` (breakpoint), `p variavel` (print), `l` (list), `q` (quit).

---

## 12. Como foi verificado

1. **pytest** ([tests/test_mazegen.py](tests/test_mazegen.py)), com 40 testes:
   coerência das paredes, bordas fechadas, conectividade total, ausência de
   3x3 aberto, 0 ciclos no modo perfeito, ≥ 2 ciclos e quase nenhum beco no
   modo Pac-Man, reprodutibilidade da seed, configs inválidas.
2. **maze_analyzer.py** em 192 combinações (2 modos × 2 algoritmos × 6
   tamanhos × 8 seeds): todos os perfeitos deram "PERFECT maze" e todos os
   Pac-Man deram "bonus-grade (perfectly braided)".
3. `flake8`, `mypy` (flags obrigatórias) e `mypy --strict` sem erros.
4. Instalação do `.whl` num venv limpo e import a partir de outra pasta.

---

## 13. Prepara-te para a modificação ao vivo

O subject avisa que te podem pedir uma pequena alteração. Treina estas:

1. **Mudar a cor do caminho** → `PATH_COLOUR` em `display.py`.
2. **Acrescentar uma opção ao menu** (por exemplo "6. mostrar a seed") →
   `MENU` e mais um `elif` em `interactive_loop`.
3. **Nova chave de config** (por exemplo `DISPLAY=False`) → `OPTIONAL_KEYS`,
   campo na `Config`, ler em `load_config`.
4. **Mudar o padrão** (desenhar outro número/letra) → `PATTERN_42` (atenção
   à coluna livre no centro e ao tamanho mínimo).
5. **Contar becos sem saída** → `sum(1 for c in células if
   len(maze.open_neighbours(c)) == 1)`.
6. **Gerar sempre a mesma seed ao regenerar** → em `interactive_loop`,
   `maze.generate()` sem argumento.
7. **Imprimir o comprimento do caminho** → `len(maze.solve())` (já aparece na
   linha de estado).
8. **Mudar a ordem dos bits** (por exemplo Norte = bit 3) → só as constantes
   `NORTH/EAST/SOUTH/WEST`. Todo o resto usa os nomes e não os números. É
   uma boa prova de que o código está bem estruturado.
9. **Implementar outro algoritmo** (Kruskal com *union-find*, ou
   *Binary tree*) → novo método `_carve_xxx` e o seu nome em `ALGORITHMS`.

---

## 14. Perguntas que te podem fazer (e a resposta curta)

* **O que é um labirinto perfeito?** Uma árvore geradora: conexo e sem
  ciclos, com exatamente um caminho entre quaisquer duas células.
* **Porque BFS e não DFS para o caminho?** A BFS garante o mais curto em
  grafos sem pesos.
* **Como garantes a reprodutibilidade?** Com `random.Random(seed)` próprio da
  instância. Mesma seed significa a mesma sequência de números e o mesmo
  labirinto.
* **Como garantes que não há células isoladas?** O DFS/Prim só termina quando
  visitou todas as células livres. Os testes verificam-no com um flood fill.
* **Porque pilha e não recursão?** Por causa do limite de recursão do Python.
* **Como evitas áreas 3x3?** Uma árvore não tem 2x2 abertos. No braiding,
  cada abertura é testada antes de ser aplicada.
* **O que faz `cell & ~EAST`?** `~EAST` é a máscara com todos os bits a 1
  exceto o de Este. O `&` limpa esse bit, ou seja, abre a parede.
* **Diferença entre `.whl` e `.tar.gz`?** Um é o pacote construído, o outro
  é o código-fonte.
* **Porque MIT?** Permissiva e simples, e permite a reutilização e a
  distribuição pedidas pelo subject.
* **Quantos ciclos tem o labirinto?** `arestas − vértices + 1`.

---

## 15. Leituras recomendadas

* Jamis Buck, *Mazes for Programmers*, o livro de referência sobre o tema.
* Blog do Jamis Buck: série "Maze Generation" (um artigo por algoritmo, com
  animações).
* Walter Pullen, *Think Labyrinth*: terminologia (perfect, braid, dead-end).
* Wikipedia: *Maze generation algorithm*, *Spanning tree*,
  *Breadth-first search*, *Cyclomatic number*.
* Documentação Python: `typing`, `dataclasses`, `collections`, `random`, `pdb`.
* PEP 8, PEP 257, PEP 484, PEP 621; *Python Packaging User Guide*.
* choosealicense.com, para comparar licenças.

---

## 16. Antes de submeter

- [ ] Mudar `<login>` na primeira linha do README.md (e na secção da equipa).
- [ ] Ajustar o parágrafo "AI usage" no README à forma como realmente trabalhaste.
- [ ] `git init`. O `.gitignore` já exclui `.venv/`, caches e `maze.txt`.
- [ ] Confirmar que `mazegen-1.0.0-py3-none-any.whl` (e/ou o `.tar.gz`) está
      na raiz e foi commitado.
- [ ] `make lint` e `make lint-strict` sem erros.
- [ ] Decidir se este `GUIA_DE_ESTUDO.md` vai para o repositório ou não (não é
      exigido; podes adicioná-lo ao `.gitignore`).
