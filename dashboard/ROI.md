# ROI / Value

<!-- Machine-facing contract for the portfolio dashboard's GitHub sync (see
     src/github_sync.py). Not for humans browsing the repo - docs/roi_explained.md
     is the real methodology. Written in Ukrainian on purpose: this text renders
     directly inside the dashboard's Ukrainian-language UI, next to labels like
     "Оцінка"/"Виміряно" - condense docs/roi_explained.md's English methodology
     into short Ukrainian captions here, don't just translate it verbatim, and
     keep Hypothesis/How We'll Measure It short - they render in a 300px sidebar
     panel, not a full-width block. Regenerate via automation-portfolio-sync,
     don't hand-edit this prose. -->

## Hypothesis
У Supplax росте кількість автоматизацій, але немає єдиного місця, де видно, що вони
роблять і чи справді окупаються. Дашборд показує ROI і статус кожної автоматизації в
одному місці — і для керівництва, і для власників.

## How We'll Measure It
Час або гроші, які автоматизація економить порівняно з ручним способом — за оцінкою
власника при реєстрації.

## Confidence
Estimated — реальних даних ще немає.

## Actual Results
<!-- Empty at bootstrap - fills in as real data comes in. -->

## Qualitative Value
- Прозорість: усі автоматизації видно в одному місці, а не розкидані по GitHub, ClickUp і усній передачі.
- Швидша реакція на збої — коли запрацюють Telegram-алерти (Next).
- Видимість витрат на токени — коли запрацює трекінг (Later).
