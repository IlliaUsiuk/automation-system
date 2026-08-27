# TODO

<!-- Machine-facing mirror for the portfolio dashboard's GitHub sync (see
     src/github_sync.py). Generated verbatim from the repo's root TODO.md -
     edit that file and regenerate this one via automation-portfolio-sync,
     don't hand-edit this prose. -->

- [x] «Що відбувається зараз» на картці автоматизації — реалізовано як простий факт,
  а не вгаданий етап: дашборд показує текст останнього коміту репозиторію і коли він
  стався (формулювання коміту не завжди відповідає етапу життєвого циклу, тож воно не
  перетворюється на наратив). Необов'язковий `## Current Stage` у
  `dashboard/SUMMARY.md` перекриває це для всього, чого коміт сказати не може
  ("очікуємо погодження", "заблоковано"). Стоїть поруч зі `Status`, а не замінює його.
- [ ] Це досі оновлюється лише вручну кнопкою "Оновити з GitHub", а не наживо —
  webhook або періодичний опит закрили б цей розрив, поки не реалізовано.
