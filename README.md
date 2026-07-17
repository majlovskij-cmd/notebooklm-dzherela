# notebooklm-dzherela

A [Claude Code](https://claude.com/claude-code) skill that turns several **deep-research
exports** (Perplexity, Parallel, Gemini, ChatGPT, …) into a clean, ready-to-paste pack for
**Google NotebookLM / Gemini**.

Скіл для Claude Code, що зводить кілька deep-research експортів у чистий пакет для NotebookLM.

## Що робить

Для кожного дослідження:

- **Чистий синтез** — окремий копі-текст, з якого прибрано URL, `[^n]`-виноски,
  markdown-лінки, PUA-citation-токени ChatGPT і хвостовий розділ «Джерела/Sources/References».
  **Формулювання зберігається дослівно — текст не переписується.**
- **Єдиний список посилань** — усі URL зведені в один файл: дедуплікація за нормалізованим
  host+path, у порядку пріоритету, tracking-параметри зрізано, під ліміт NotebookLM (300).
- **Виключення доменів** — за бажанням прибирає власні сайти (задаються під час запуску,
  нічого не зашито в код).
- **HTML «copy center»** — офлайн-сторінка з вкладками по синтезах + вкладка «Посилання»,
  у кожній кнопка «Копіювати». Light/dark.
- **Звіт** — скільки посилань з кожного файлу, скільки унікальних, математика ліміту, топ-домени.

Розпізнає 4 типові формати цитат автоматично: Parallel (інлайн `[… — URL]`),
Perplexity (нумеровані футноти), Gemini (розділ «Джерела»), ChatGPT (`citeturn…`-токени).

## Встановлення

```bash
git clone https://github.com/<owner>/notebooklm-dzherela.git \
  ~/.claude/skills/notebooklm-dzherela
```

Або завантаж ZIP і поклади папку в `~/.claude/skills/notebooklm-dzherela/`
(структура: `SKILL.md`, `scripts/build.py`, `references/config.md`).

Скіл підхопиться автоматично. Виклик: `/notebooklm-dzherela` — або просто кинь Claude
кілька дослідницьких файлів і скажи «підготуй для NotebookLM».

## Вимоги

- Claude Code
- Python 3 (лише стандартна бібліотека — жодних залежностей)

## Як користуватись напряму (без Claude)

```bash
python3 scripts/build.py config.json
```

Схема `config.json` — у [`references/config.md`](references/config.md).

## Ліцензія

MIT
