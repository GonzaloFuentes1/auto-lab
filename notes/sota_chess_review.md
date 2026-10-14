# Bot de ajedrez de nivel mundial: estado del arte y plan (octubre 2026)

Pregunta de partida: ¿conviene hacer primero **aprendizaje supervisado (SL)** y después
**RL con self-play / contra otros**? ¿Qué es lo mejor hoy y cómo lo aprovechamos?

## TL;DR

1. **La idea SL → RL va bien encaminada, con dos ajustes importantes.**
   - El SL tiene que **destilar un motor** (evaluaciones de Stockfish o los objetivos de MCTS de
     Lc0), no imitar partidas humanas. Imitar humanos te deja en nivel humano (techo de Maia).
     Destilar Stockfish lleva un transformer **sin búsqueda** a ~2900 Elo blitz en Lichess
     (Ruoss et al. 2024).
   - **Hacer RL desde cero no es viable en un side-project.** AlphaZero y Lc0 costaron (según
     estimaciones) decenas de millones de dólares en cómputo, o años de cómputo distribuido entre
     voluntarios. El RL sirve como **fine-tuning** sobre la red SL, con MCTS barato (Gumbel) y un
     ancla KL hacia la política previa. Esperamos ganancias marginales, no saltos. Hay evidencia
     de 2026 de que el self-play sin ancla colapsa (Miłosz et al. 2026).
2. **Lo mejor hoy:**
   - **Stockfish** (alpha-beta + red NNUE en CPU): Stockfish 19, ~3650 CCRL. Ganó TCEC S28 y
     S29 y todos los CCC de 2025–2026.
   - **Lc0** (MCTS + transformer "Chessformer"/BT4): segundo, y ya gana partidas y torneos
     puntuales a Stockfish. Chessformer salió en ICLR 2026.
   - Ninguno de los dos se entrena hoy "puramente con self-play desde cero". Las redes NNUE de
     Stockfish se entrenan supervisadamente sobre miles de millones de posiciones etiquetadas por
     motores, y Chessformer se entrenó con un dataset fijo de una corrida de Lc0. **En la práctica
     el estado del arte es destilación a gran escala más búsqueda.**
3. **Meta realista:** "nivel mundial humano" (>2800, superar a cualquier GM) **sí es alcanzable**
   con destilación + MCTS en 1 GPU. "Le gana a Stockfish 19" **no lo es** para un side-project:
   requiere el ecosistema completo de Stockfish o de Lc0. Donde sí podemos aportar algo nuevo es
   en **Elo por FLOP**: el bot sin búsqueda o con poca búsqueda más fuerte para un presupuesto
   dado, y RL de fine-tuning que mejore sobre su profesor.

## 1. El panorama

| Sistema | Búsqueda | Red | Cómo se entrena | Fuerza aprox. |
|---|---|---|---|---|
| **Stockfish 19** (sep. 2026) | alpha-beta, CPU | NNUE (MLP pequeño, actualizable en forma incremental) | SL sobre miles de millones de posiciones con eval de motor (`nnue-pytorch`; los mejores nets usan ~16B posiciones con score de profundidad 9 y >200 épocas) | ~3650 CCRL 40/15, #1 |
| **Lc0** + Chessformer/BT4 | MCTS (PUCT), GPU | transformer, 1 token por casilla, ~15 capas × 1024 | históricamente RL self-play distribuido; Chessformer se entrenó sobre un dataset fijo de una corrida de Lc0 (abril 2024) | #2; según el paper, gana torneos a Stockfish; solo la política ya es nivel GM |
| **searchless_chess** (DeepMind 2024) | ninguna (1 forward) | transformer decoder de 270M | SL sobre ChessBench: 15B action-values de Stockfish 16 | 2895 Lichess blitz vs humanos |
| **Maia-2 / Maia-3** | ninguna | Chessformer | SL sobre partidas humanas | imita humanos (57% de acierto de jugada) |
| **LLMs generales** | razonamiento en texto | LLM | RL/SFT con texto | muy débil: o3 ~758 Elo en LLM CHESS; ningún LLM supera a Maia-1100 en ChessArena |

Para el RL, lo relevante es lo siguiente:

- **AlphaZero (2017)**: RL puro con 5000 TPUs. El mismo enfoque en Go costó ~41 TPU-años.
- **KataGo (2019)** demostró que con ingeniería (objetivos auxiliares, randomización del número
  de playouts, etc.) el self-play se puede hacer entre 5 y 50 veces más eficiente, aunque sigue
  siendo caro.
- **Gumbel AlphaZero (Danihelka et al., ICLR 2022)** garantiza mejora de política aunque se usen
  muy pocas simulaciones (incluso 2–16). Es la pieza clave para un RL barato.
- **Miłosz et al. (ago. 2026)**: fine-tuning con self-play sobre la red Chessformer de Lc0.
  - Con un ancla KL "forward" hacia el prior de MCTS sube el puzzle accuracy (93,9 → 94,9%) y el
    Elo sin búsqueda se mantiene o sube un poco.
  - **Sin ancla, el self-play colapsa** en una sola línea de juego.
  - Optimizar solo puzzles **costó ~260 Elo**: la precisión en táctica y la fuerza de juego se
    disocian.

## 2. ¿SL → RL es la mejor manera? Veredicto por etapa

| Etapa | Tu idea | Recomendación | Por qué |
|---|---|---|---|
| SL | aprendizaje supervisado | **Sí, pero con datos de motor** (evals y PVs de Stockfish, después action-values) | Ruoss 2024: los action-values de un motor son mejor objetivo que clonar comportamiento, y el profesor es sobrehumano. Imitar humanos tiene techo humano. |
| Búsqueda | (no mencionada) | **Agregar MCTS (PUCT) sobre la red** | La búsqueda suma cientos de Elo y es gratis en entrenamiento. Todos los motores top la usan. |
| RL | self-play / contra otros | **Como fine-tuning acotado**: expert iteration con Gumbel MCTS de pocas simulaciones, ancla KL a la red SL y una liga mixta (self-play + Stockfish con límite de Elo + checkpoints anteriores) | RL desde cero es inviable en costo. El self-play puro colapsa. Contra Stockfish con límite hay señal densa y diversa. |
| Datos de RL | — | **Re-etiquetar posiciones de self-play con Stockfish** (híbrido) | Es lo que hace el ecosistema Lc0 + SF: las posiciones vienen de nuestra distribución y los valores del profesor fuerte. Barato y muy efectivo. |

**Conclusión:** la secuencia correcta es **destilación (SL de motor) → búsqueda → RL de
fine-tuning**, y el RL se justifica como pregunta de investigación ("¿puede superar a su
profesor con poco cómputo?"), no como el motor principal de fuerza.

## 3. Cómo lo aprovechamos: recursos abiertos

- **Datos**
  - [Lichess eval DB](https://database.lichess.org/) (CC0): ~395M posiciones con eval de
    Stockfish y varias PVs. Es la fuente de la fase 1 y ya está integrada (`chessbot.prepare evaldb`).
  - [ChessBench](https://github.com/google-deepmind/searchless_chess): 15B action-values de SF16
    (~1,1 TB). También trae los checkpoints de 9M/136M/270M (CC-BY 4.0) como baselines directos.
  - Datos de entrenamiento de Lc0 (`storage.lczero.org/files/training_data/`): objetivos de MCTS
    (distribución de visitas + WDL). Es la fuente "estilo Chessformer".
  - [Lichess puzzle DB](https://database.lichess.org/): ~5M puzzles con rating. Se usa para eval
    barata (`chessbot.puzzles`).
  - Partidas de Lichess (PGN): solo como baseline humano (hipótesis H1).
- **Profesor y sparring:** Stockfish con `UCI_LimitStrength`/`UCI_Elo` (1320–3190) da una
  escalera de Elo calibrada (`chessbot.arena`).
- **Arquitectura:** las ideas de Chessformer (token por casilla, sesgo de atención geométrico,
  policy head origen→destino) ya están en `chessbot/model.py` en versión simple, con un sesgo de
  atención aprendido estático. GAB/smolgen dinámico queda como hipótesis.
- **Despliegue:** [lichess-bot](https://github.com/lichess-bot-devs/lichess-bot) habla UCI y nuestro
  `chessbot.uci` ya funciona como motor.

## 4. Plan por fases (cada fase con su criterio de éxito)

| Fase | Qué | Criterio para pasar a la siguiente |
|---|---|---|
| 0. Infra de eval | arena vs escalera de SF, puzzles, Elo con IC95 | ✅ hecho en este commit |
| 1. Destilación | Lichess eval DB → transformer 10–50M; después ChessBench action-values | política sin búsqueda ≥ SF@2000 (puntaje ≥ 50% con IC que no cruce 40%) |
| 2. Búsqueda | PUCT batcheado, reutilización de árbol, curva Elo vs nodos | ≥ +250 Elo sobre la política cruda a 400 nodos |
| 3. RL fine-tuning | Gumbel expert-iteration, ancla KL, liga mixta, re-etiquetado con SF | Elo > red SL a nodos fijos, con IC95 que excluya 0 |
| 4. Despliegue | BOT en Lichess | rating estable en blitz |

## 5. Riesgos y decisiones abiertas

- **Cómputo:** está indefinido. La fase 1 en CPU solo sirve para smoke tests; un modelo de 50M
  sobre ~400M posiciones necesita GPU (orden de 1–3 días en una A100). Hay que definir
  cluster o GPU local.
- **Preparar datos en Python es lento** (~6k pos/s por núcleo). Para 400M posiciones hay que
  paralelizar (multiproceso por shard) o portar el encoding a Rust/C++.
- **Elo vs humanos ≠ Elo vs motores.** Hay que reportar ambas escaleras por separado y no mezclarlas.
- **Puzzles ≠ fuerza de juego** (Miłosz 2026). Ninguna hipótesis se confirma solo con puzzles.

## Fuentes

- [Stockfish (Wikipedia)](https://en.wikipedia.org/wiki/Stockfish_(chess))
- [nnue-pytorch](https://github.com/official-stockfish/nnue-pytorch)
- [Chessformer: A Unified Architecture for Chess Modeling (ICLR 2026, arXiv 2605.19091)](https://arxiv.org/abs/2605.19091)
- [Lc0 blog: Transformer Progress](https://lczero.org/blog/2024/02/transformer-progress/)
- [Ruoss et al. 2024, Amortized Planning with Large-Scale Transformers / Grandmaster-Level Chess Without Search](https://arxiv.org/abs/2402.04494)
- [searchless_chess / ChessBench](https://github.com/google-deepmind/searchless_chess)
- [Farebrother et al. 2024, Stop Regressing (HL-Gauss)](https://arxiv.org/abs/2403.03950)
- [Miłosz et al. 2026, Beyond Search-Imitation: Prior-Directed Exploration for Searchless Chess](https://arxiv.org/abs/2608.27757)
- [Danihelka et al. 2022, Policy Improvement by Planning with Gumbel](https://iclr.cc/virtual/2022/poster/6418)
- [Wu 2019, Accelerating Self-Play Learning in Go (KataGo)](https://arxiv.org/abs/1902.10565)
- [Search-contempt (2025), costo estimado de entrenar motores tipo AlphaZero](https://arxiv.org/abs/2504.07757)
- [LLM CHESS benchmark](https://arxiv.org/abs/2512.01992), [ChessArena](https://arxiv.org/abs/2509.24239), [RL de LLMs en puzzles](https://arxiv.org/abs/2507.00726)
- [Lichess open database](https://database.lichess.org/)
