# Automation Summary

<!-- Machine-facing contract for the portfolio dashboard's GitHub sync (see
     src/github_sync.py). Not for humans browsing the repo - that's README.md's
     job. Every heading below is a fixed field the sync parser reads by name;
     don't rename them, and keep this file honest and current as the project
     changes - a stale summary is worse than no summary. -->

## Name
Automation ROI Dashboard

## One-liner
Внутрішній дашборд Supplax, що збирає всі автоматизації компанії в одному місці.

## What it does
Веб-застосунок на Flask, куди стікаються всі автоматизації, які будує компанія:
хто власник, який відділ отримує користь, який статус (ідея / у розробці /
готово-не-запущено / працює / архів), і найголовніше — ROI: гіпотеза цінності,
як її виміряти, і реальний результат, коли він з'являється.

Дані потрапляють сюди двома шляхами: адмін додає автоматизацію руками через
форму, або через синхронізацію з GitHub-репозиторію автоматизації — застосунок
сам читає README.md, ROI.md і цей-от summary/SUMMARY.md і заповнює картку.

Це ж і є той репозиторій, який зараз дивиться сам на себе — Automation ROI
Dashboard імпортований у власний портфель як демонстрація механізму синку.

## Departments
- IT

## Status
in_development

## Connections
