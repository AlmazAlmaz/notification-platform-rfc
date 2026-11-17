# Диаграммы архитектуры

Здесь находятся исходники PlantUML и готовые SVG/PNG. Для просмотра на GitHub установка инструментов не нужна. Файлы рендера лежат рядом с исходниками, без подкаталога `rendered`.

| Вариант | C4 Container | Основной сценарий | Failover |
|---|---|---|---|
| A — Kafka + PostgreSQL + автомат | [SVG](a-container.svg) · [PNG](a-container.png) · [исходник](a-container.puml) | [SVG](a-normal.svg) · [PNG](a-normal.png) · [исходник](a-normal.puml) | [SVG](a-failover.svg) · [PNG](a-failover.png) · [исходник](a-failover.puml) |
| B — Temporal | [SVG](b-container.svg) · [PNG](b-container.png) · [исходник](b-container.puml) | [SVG](b-normal.svg) · [PNG](b-normal.png) · [исходник](b-normal.puml) | [SVG](b-failover.svg) · [PNG](b-failover.png) · [исходник](b-failover.puml) |

На C4 critical и bulk имеют независимые Kafka и PostgreSQL. Bulk-путь показан укрупнённо одним сервисом, поскольку предмет RFC — критичная доставка. Вариант A использует ledger как источник состояния; вариант B — историю workflow, а admission/business index является проекцией. Пометка `3-AZ sync HA` означает primary и две standby в разных AZ, подтверждение записи после локального и удалённого WAL flush и согласованную strict synchronous promotion/fencing policy. В C4 это аннотация контейнера хранилища; deployment topology подробно описана в RFC.

## Повторный рендер

Нужны Java 17+ и [PlantUML 1.2025.2](https://github.com/plantuml/plantuml/releases/tag/v1.2025.2). Рендер C4 использует встроенный Smetana (`!pragma layout smetana`), поэтому Graphviz устанавливать не требуется. Макросы C4 подключаются локально: после загрузки JAR сетевой доступ для рендера не нужен.

В PowerShell из корня репозитория; Java должна быть в `PATH`:

```powershell
New-Item -ItemType Directory -Path '.tools' -Force | Out-Null
Invoke-WebRequest -Uri 'https://github.com/plantuml/plantuml/releases/download/v1.2025.2/plantuml-1.2025.2.jar' -OutFile '.tools/plantuml.jar'
$expectedHash = '862C7D6D0D3BDE3C819EAC4DFC03CF549046BF1D49C04D18A779EB2D834B77C9'
if ((Get-FileHash -LiteralPath '.tools/plantuml.jar' -Algorithm SHA256).Hash -ne $expectedHash) {
    throw 'PlantUML JAR checksum mismatch'
}
java '-Djava.awt.headless=true' -jar '.tools/plantuml.jar' -charset UTF-8 -checkonly 'diagrams/*.puml'
if ($LASTEXITCODE -ne 0) { throw 'PlantUML source validation failed' }
java '-Djava.awt.headless=true' -jar '.tools/plantuml.jar' -charset UTF-8 -tsvg 'diagrams/*.puml'
if ($LASTEXITCODE -ne 0) { throw 'SVG render failed' }
java '-Djava.awt.headless=true' -jar '.tools/plantuml.jar' -charset UTF-8 -tpng 'diagrams/*.puml'
if ($LASTEXITCODE -ne 0) { throw 'PNG render failed' }
```

Если Java доступна через `JAVA_HOME`, вместо `java` используется `& "$env:JAVA_HOME/bin/java.exe"` с теми же аргументами. JAR хранится локально в игнорируемом `.tools`; он не включён в репозиторий. Различия шрифтов/Java могут немного изменить размеры рендера, поэтому после изменения исходников следует просмотреть все шесть PNG.

## Источники и лицензии

Макросы скопированы без изменений из официального [C4-PlantUML v2.12.0](https://github.com/plantuml-stdlib/C4-PlantUML/tree/v2.12.0). Локальная цепочка включает весь необходимый набор: `C4_Container.puml` → `C4_Context.puml` → `C4.puml`; `RELATIVE_INCLUDE` в исходниках выбирает локальные include. [MIT License](lib/LICENSE) сохранена вместе с библиотекой.

| Vendored-файл | SHA-256 |
|---|---|
| `lib/C4.puml` | `EE4F85B5C31104155E14059D942831C3361CDDD5009E22D66B1242060464BF7D` |
| `lib/C4_Context.puml` | `5C0C2A05B9F5E443447CD874A8F3923674390E5B2FF07D0DB8E0DE2BDE872035` |
| `lib/C4_Container.puml` | `65FB59E1504DA77BA0C32DDC6AA75179BFA28882143DDB23A2F0B11DA6E6B596` |

Диаграммы — авторское описание предложенной системы, а не доказательство её производительности. Перед production нужны проверки, перечисленные в RFC.
