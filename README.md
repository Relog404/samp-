# RELOG-IC — клиент оптимизации Minecraft 1.12.2

Панель с фирменным оформлением (фиолетово-пурпурно-голубой градиент, тёмные
«майнкрафтовские» панели) + инструменты, которые реально правят игру:

* **Оптимизация графики** — `options.txt`: дальность прорисовки, mipmap,
  детализация, частицы, лимит FPS, V-Sync, VBO/FBO, яркость, полный экран;
* **Камера** — FOV («рыбий глаз» 110°), плавная камера и покачивание
  («бодикам»), чувствительность, инверси;
* **Память и JVM** — аргументы в `launcher_profiles.json` (Aikar/G1, Xmx/Xms);
* **Профили** — готовые пресеты: максимальный FPS, баланс, фотореализм,
  бодикам, рыбий глаз, чистый ванилл;
* **Клиент** — пересборка jar: убирает фирменные экраны/HUD/иконки/логи.

Всё локально: ни сети, ни телеметрии. Каждая запись — с бэкапом в
`.minecraft/.relogic_backups/<дата>/`.

```
app/server.py            локальный сервер панели (stdlib, без зависимостей)
app/core/options.py      парсер/писатель options.txt
app/core/presets.py      пресеты и флаги JVM
app/core/jvm.py          launcher_profiles.json
app/core/paths.py        поиск .minecraft, демо-папка
app/static/              интерфейс: index.html, style.css, app.js
tools/vanilla_patch.py   пересборка jar клиента
tools/verify_jar.py      проверка пересобранного jar
tools/build_client.py    сборка RELOG-IC из Impact + скомпилированного модуля
tools/verify_client.py   статическая проверка собранного клиента
src/mod/java, src/mod/resources   исходники миксинов и слой клиента (компиляция в CI)
.github/workflows/build.yml       CI: JDK 8, client.jar, javac, сборка и проверка
tests/test_app.py        14 тестов ядра
tests/test_client_build.py       10 тестов сборки клиента
dist/*.jar               готовые пересобранные jar (в т.ч. RELOG-IC-4.9.1-1.12.2.jar)
```

## Запуск

```bash
python3 app/server.py --demo        # демо-папка, ничего в реальной игре не меняется
python3 app/server.py               # реальный ~/.minecraft (или путь из панели)
```

Открыть <http://localhost:8765>. Дальше в панели можно указать свой путь к
`.minecraft` (поле «Папка Minecraft»).

Проверки:

```bash
python3 -m unittest discover -s tests -v     # 24 теста
python3 tools/verify_jar.py Impact-4.9.1-1.12.2.jar dist/1.12.2.jar
python3 tools/verify_client.py dist/RELOG-IC-4.9.1-1.12.2.jar
```

## Что в интерфейсе

**Главное меню.** Логотип `RELOG-IC` с градиентом и «splash»-надписью, кнопки
«Оптимизация», «Профили», «Память и JVM», «Клиент», «О клиенте». У кнопки
«Оптимизация» при наведении висит подсказка со списком всего, что она открывает.

**Оптимизация.** Четыре вкладки и ~30 параметров с ползунками, тумблерами и
описаниями:

| Вкладка | Параметры |
|---|---|
| Графика | дальность прорисовки, mipmap (сглаживание текстур), красивая графика, AO, облака, яркость, фуллскрин, масштаб UI, anaglyph |
| Камера | FOV (70–110°), плавная камера, покачивание, чувствительность, инверсия Y |
| Производительность | лимит FPS, частицы, VBO, FBO, V-Sync |
| Прочее | видимость чата, прозрачность/масштаб чата, индикатор атаки, рука, тултипы, snooper, скрытие IP сервера, F3 и т.д. |

Неизвестные ключи `options.txt` сохраняются как есть — модовые настройки не
теряются, значения зажимаются в допустимые границы.

**Профили.** Шесть пресетов, применяются одним кликом с бэкапом:

* `maxfps` — 4 чанка, mipmap 0, без облаков/AO, частицы «минимум», лимит 260;
* `balanced` — 8 чанков, mipmap 2, лимит 144;
* `photorealism` — 16 чанков, mipmap 4, AO, все частицы, яркость 45%;
* `bodycam` — smoothCamera + bobView + FOV 85° + мягкая чувствительность;
* `fisheye` — FOV 110° и плавная камера;
* `vanilla` — заводские значения 1.12.2.

**Память и JVM.** Выбор профиля лаунчера, памяти (1–16 ГБ), сборщика мусора
(Aikar/G1/не трогать) и дополнительных аргументов; предпросмотр итоговой строки
и запись в `launcher_profiles.json` с бэкапом.

**Клиент.** Кнопки «Пересобрать» и «Проверить» для jar: тот же патч, что и в
CLI, плюс проверка результата (список файлов, миксины, логирование, манифест).

## Что меняется в jar

| Что | Как |
|---|---|
| Главное меню клиента (`gui.MixinGuiMainMenu`) | миксин отключён → ванильное меню |
| Кнопка клиента в меню паузы, HUD/watermark, версия в F3 | отключены |
| `credits.json`, `changelog.md`, `welcome.md` | вычищены |
| `icons/*.png` (логотип в иконке окна) | нейтральная «травяная» иконка |
| `log4j2.xml` внутри jar | `Root level="off"` |
| даты в архиве, `MANIFEST.MF` | фиксированная дата, лишние атрибуты убраны |

Байткод не трогается: 4241 запись на месте, изменены 12 (это проверяет
`tools/verify_jar.py`).

## Свой экран внутри Minecraft: скомпилированный модуль

Да, теперь это не «нельзя»: код **реально компилируется** на GitHub Actions
(в песочнице компилятора нет, поэтому сборка вынесена в CI на настоящем JDK 8).

```
src/mod/java/RelogicClient.java            слой клиента (default package!)
src/mod/java/relogic/mixin/MixinGuiMainMenu.java
src/mod/java/relogic/mixin/MixinGuiIngame.java
src/mod/java/relogic/mixin/MixinMinecraft.java
src/mod/java/relogic/mixin/Bridge.java     мост mixin -> RelogicClient
src/mod/resources/mixins.relogic.json      конфиг миксинов
```

Почему `RelogicClient` лежит в default package: обфусцированный клиент 1.12.2
(`bib`, `blk`, `bir`, ...) сам лежит в default package. Только так можно
обращаться к нему напрямую — и даже читать `protected` поля вроде
`blk.n` (список кнопок) и `bja.f/g/h/i` (рамка кнопки), потому что это одна и
та же «безымянная» пакетная область.

**Почему не обфусцированные имена.** Первый запуск упал:

```
Mixin apply failed ... @Inject ... could not find any targets matching 't'
in the target class net.minecraft.client.Minecraft. No refMap loaded.
```

Forge 1.12.2 переименовывает ванильные классы в SRG-имена **в рантайме**:
`bib` → `net.minecraft.client.Minecraft`, `bib.t()` → `func_71407_l()`,
`bib.k` → `field_71466_p` и т.д. Поэтому модуль больше не ссылается на
`bib/blk/...` напрямую, а работает через рефлексию по SRG-именам, взятым из
официального `mcp-1.12.2-srg` (и сверенным с `fields.csv`/`methods.csv`).

Каждое имя проверяется в CI (`tools/verify_client.py`):

```
target ok (srg): net.minecraft.client.gui.GuiMainMenu.func_73863_a(IIF)V
target ok (srg): net.minecraft.client.gui.GuiIngame.func_175180_a(F)V
target ok (srg): net.minecraft.client.Minecraft.func_71407_l()V
reflection ok: net.minecraft.client.gui.Gui.func_73734_a(IIIII)V
reflection ok: net.minecraft.client.settings.GameSettings.func_74296_a(...Options;)F
reflection names ok: 32 checked against mcp-1.12.2-srg
```

| Что нужно | SRG-имя в рантайме |
|---|---|
| `Minecraft.getMinecraft()` | `func_71410_x` |
| `Minecraft.fontRenderer` / `gameSettings` / `currentScreen` | `field_71466_p` / `field_71474_y` / `field_71462_r` |
| `Minecraft.runTick()` | `func_71407_l` |
| `GuiScreen.buttonList` / `width` / `height` | `field_146292_n` / `field_146294_l` / `field_146295_m` |
| `GuiButton.x` / `y` / `width` / `height` / `id` / `displayString` | `field_146128_h` / `field_146129_i` / `field_146120_f` / `field_146121_g` / `field_146127_k` / `field_146126_j` |
| `FontRenderer.drawString` / `getStringWidth` | `func_78276_b` / `func_78256_a` |
| `Gui.drawRect` | `func_73734_a` |
| `ScaledResolution.getScaledWidth/Height` | `func_78326_a` / `func_78328_b` |
| `GameSettings.getOptionFloatValue/setOptionValue/setOptionFloatValue/saveOptions` | `func_74296_a` / `func_74306_a` / `func_74304_a` / `func_74303_b` |
| `GuiMainMenu.drawScreen` / `GuiIngame.renderGameOverlay` | `func_73863_a(IIF)V` / `func_175180_a(F)V` |

Миксины сделаны «двойными»: по одному `@Inject` на SRG-имя и на старое
обфусцированное, оба с `require = 0`. В рантайме срабатывает тот, который
существует, а второй тихо пропускается — вместо жёсткого краша, как было.

**Что делает модуль в игре:**

* главное меню — градиентный `RELOG-IC` (фиолетовый → пурпурный → голубой),
  подзаголовок, постоянная карточка со списком настроек и всплывающая подсказка
  у ванильной кнопки «Настройки...» (id 0);
* `F6` — панель поверх игры: 11 строк (дальность, частицы, облака, AO, графика,
  mipmap, лимит FPS, FOV, гамма, прозрачность и масштаб чата);
  `PgUp/PgDn` — выбор строки, `-`/`=` — значение, применяется сразу через
  `GameSettings.setOptionValue`;
* `F7` — «исчезнуть»: панель и вся отрисовка выключаются полностью.

**Как это собирается (CI, `.github/workflows/build.yml`):**

1. `setup-java` temurin **8** → `javac 1.8.0_514`;
2. скачивается настоящий `client.jar` 1.12.2 с launchermeta (10 180 113 байт)
   и LWJGL 2.9.4 из манифеста версии;
3. `javac -encoding UTF-8 -source 8 -target 8 -proc:none -cp "client.jar:/tmp/mc/*:Impact-4.9.1-1.12.2.jar"`
   → `ci/out/relogic-module.jar` (8 записей: 4 класса + 3 миксина + конфиг);
4. `tools/build_client.py` вшивает модуль в `Impact-4.9.1-1.12.2.jar`:
   добавляет классы, дописывает `mixins.relogic.json` в `MixinConfigs`
   манифеста, вырезает фирменные миксины Impact
   (`gui.MixinGuiMainMenu`, `gui.MixinGuiIngame`, `gui.MixinGuiIngameMenu`,
   `MixinGuiOverlayDebug`) и ставит `log4j Root level="off"`;
5. `tools/verify_client.py --client client.jar` проверяет, что цели инъекций
   реально есть в клиенте. Лог CI:

```
target ok: blr.a(IIF)V
target ok: biq.a(F)V
target ok: bib.t()V
OK: клиент собран корректно
```

**Готовый jar:** `dist/RELOG-IC-4.9.1-1.12.2.jar` (4249 записей: 4241 базовых +
8 модуля). Собран из того же модуля, что проверен в CI.

Пересобрать локально:

```bash
python3 tools/build_client.py            # нужен ci/out/relogic-module.jar из CI
python3 tools/verify_client.py dist/RELOG-IC-4.9.1-1.12.2.jar
```

**Честные границы:**

* игру в песочнице запустить нельзя — проверено компиляцией, соответствием
  сигнатур целям (`target ok: ...`) и структурой jar, но не живым запуском;
* `Mixin` сам пишет в лог строку `Mixing MixinGuiMainMenu ...`, если включён
  verbose; наш код не логирует вообще ничего (все исключения глушатся), а
  `log4j2.xml` в jar переведён в `off`;
* встроенные чат-команды Impact и его оверлеи — закрытый код: убрать их
  «неизвестной командой» на уровне исходников нельзя, но фирменные
  GUI-миксины вырезаны, поэтому меню и HUD выглядят ванильно.

## Важно

* Панель и клиент не запускались с реальной игрой в песочнице: проверены ядро
  (24 теста), HTTP-API, компиляция модуля и пересборка jar; на живой установке сначала сделайте бэкап (панель
  и сама его делает, но лишним не будет).
* Шейдеры/настоящее MSAA-FXAA панель не подменяет: «сглаживание» здесь —
  mipmap-фильтрация текстур, «фотореализм» — комбинация ванильных настроек.
  Для шейдеров нужен OptiFine + shaderpack.
