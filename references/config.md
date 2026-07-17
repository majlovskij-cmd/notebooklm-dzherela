# config.json schema for build.py

```json
{
  "topic": "Тренди дитячої моди 2026–2027",   // назва теми (у звіті й HTML)
  "out_dir": "/abs/path/NotebookLM_ready",     // куди писати всі файли (створиться)
  "file_prefix": "SUZIE",                       // префікс імен файлів (дефолт "NotebookLM")
  "limit": 300,                                  // ліміт джерел NotebookLM (дефолт 300)
  "exclude_domains": ["suzie.ua", "suzie-clothes.com"],  // підрядки доменів для виключення; [] якщо немає
  "priority": ["Parallel", "Perplexity", "Gemini", "GPT"], // порядок пріоритету при дедуплікації
  "sources": [
    { "label": "Parallel",   "path": "/abs/....parallel.md" },
    { "label": "Perplexity", "path": "/abs/....perplexity.md" },
    { "label": "Gemini",     "path": "/abs/....gemini_full.md", "strip_inline_digits": true },
    { "label": "GPT",        "path": "/abs/....gpt.md" }
  ]
}
```

## Поля
- `topic` — рядок, показується у звіті та заголовку HTML.
- `out_dir` — абсолютний шлях; усі виходи туди. Створюється автоматично.
- `file_prefix` — префікс усіх імен файлів. Дефолт `NotebookLM`.
- `limit` — ціле, дефолт 300. Формула: `len(sources) + унікальні_URL ≤ limit`.
- `exclude_domains` — список підрядків (напр. `"suzie.ua"`). URL, що містить будь-який
  із них, іде у removed-файл, а не в пул. **Заповнюється лише з відповіді користувача.**
- `priority` — список label-ів у порядку пріоритету. Перший при дублях виграє; при
  перевищенні ліміту відсікаються URL з кінця цього порядку. Дефолт — порядок `sources`.
- `sources[]`:
  - `label` — коротка назва мережі/файлу (стає іменем вкладки й файлу).
  - `path` — абсолютний шлях до `.md`/`.txt`.
  - `strip_inline_digits` *(опц., дефолт false)* — `true` лише коли виноски-цифри
    приклеєні до слів у прозі (напр. вставлений «повний» Gemini: `розкоші11`,
    `(Office Siren)9`). Безпечно ігнорує `Y2K`, `SS27`, роки `2026–2027`,
    діапазони `12–16`, нумерацію пунктів `1.`. Для звичайних `.md` не вмикай.

## Що чиститься в кожному синтезі (порядок)
1. ChatGPT PUA-citation-блоки `U+E200 … U+E201` (+ fallback для «голих» `citeturn…`).
2. Хвостовий розділ «Джерела/Источники/Sources/References/Список джерел/Посилання»
   до кінця файлу (нумерована бібліографія — не проза).
3. Рядки-футноти `12. [Title](http…)` та `[^1]: http…`.
4. Дужкові цитати з URL: `[label — https://…]`.
5. Інлайн markdown-лінки `[текст](url)` → лишається `текст`.
6. Маркери-виноски `[^1]`.
7. Будь-які «голі» URL.
8. *(опц.)* приклеєні цифри-виноски, якщо `strip_inline_digits: true`.

## Вихідні файли
- `<PREFIX>_<Label>_copy_ready.txt` — чистий синтез (по одному на джерело).
- `<PREFIX>_external_unique_<N>_URLs.txt` — унікальні зовнішні URL.
- `<PREFIX>_removed_excluded_domains_<N>.txt` — прибрані за доменами (якщо були).
- `<PREFIX>_source_report.txt` — звіт.
- `<PREFIX>_copy_center.html` — офлайн віджет із кнопками «Копіювати».
