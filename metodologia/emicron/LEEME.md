# Documentación metodológica de la EMICRON

Encuesta de Micronegocios (EMICRON) del DANE, 2019-2025. Descargada del ANDA
(<https://microdatos.dane.gov.co>, materiales relacionados de cada catálogo) el 2026-11-19.

- Cada carpeta es un año; los `.zip` de diccionarios están extraídos en la carpeta del mismo nombre.
- `DDI-EMICRON-<año>.xml`: metadatos DDI del catálogo (variables, etiquetas, categorías). De ahí salen
  los `src/dane_data/data/*_diccionario.json` de las otras encuestas.
- La metodología (DSO-EMICRON-MET-001) y la ficha (DSO-EMICRON-FME-001) también se enlazan desde
  dane.gov.co, pero a través de Isolución, que pide usuario; las del ANDA son las descargables.
- El DANE reusa documentos entre años (2023 trae los de 2022, 2025 los de 2024, la metodología y la ficha
  de 2021 son las de 2020 y el manual de 2024 es el de 2022): la columna «Nota» lo marca.
- `2020/Diccionario_de_datos.zip` trae un archivo que se llama «2019 base adicional»: así lo publica el DANE.

| Año | Catálogo | Archivo | Tipo | sha256 | Nota |
|---|---|---|---|---|---|
| 2019 | [681](https://microdatos.dane.gov.co/index.php/catalog/681) | [DDI-EMICRON-2019.xml](https://microdatos.dane.gov.co/index.php/metadata/export/681/ddi) | DDI (metadatos) | `096134290769` |  |
| 2019 | [681](https://microdatos.dane.gov.co/index.php/catalog/681) | [Diccionario de datos 2019 (base adicional).zip](https://microdatos.dane.gov.co/index.php/catalog/681/download/22746) | Diccionario | `f9d720b41b9d` |  |
| 2019 | [681](https://microdatos.dane.gov.co/index.php/catalog/681) | [Diccionario de datos 2019 base adicional.zip](https://microdatos.dane.gov.co/index.php/catalog/681/download/23516) | Diccionario | `c179348e4ab6` |  |
| 2019 | [681](https://microdatos.dane.gov.co/index.php/catalog/681) | [MICRONEGOCIOS_2019_Formulario (Final)_1.pdf](https://microdatos.dane.gov.co/index.php/catalog/681/download/21658) | Formulario | `7fb0e6d7f14c` |  |
| 2019 | [681](https://microdatos.dane.gov.co/index.php/catalog/681) | [Ficha_metodologica 22062020.pdf](https://microdatos.dane.gov.co/index.php/catalog/681/download/13792) | Técnico | `dcb9af0b321e` |  |
| 2019 | [681](https://microdatos.dane.gov.co/index.php/catalog/681) | [Guia_para_el_procesamiento_de_las_bases.pdf](https://microdatos.dane.gov.co/index.php/catalog/681/download/13795) | Técnico | `e5fd7b894a54` |  |
| 2019 | [681](https://microdatos.dane.gov.co/index.php/catalog/681) | [MICRONEGOCIOS_2019_Manual_Final.pdf](https://microdatos.dane.gov.co/index.php/catalog/681/download/13789) | Técnico | `f19235be493d` |  |
| 2019 | [681](https://microdatos.dane.gov.co/index.php/catalog/681) | [Metodologia_EMICRON_24062020.pdf](https://microdatos.dane.gov.co/index.php/catalog/681/download/13791) | Técnico | `522216da2ab8` |  |
| 2020 | [712](https://microdatos.dane.gov.co/index.php/catalog/712) | [DDI-EMICRON-2020.xml](https://microdatos.dane.gov.co/index.php/metadata/export/712/ddi) | DDI (metadatos) | `24261855714d` |  |
| 2020 | [712](https://microdatos.dane.gov.co/index.php/catalog/712) | [Diccionario de datos 2020 base adicional.zip](https://microdatos.dane.gov.co/index.php/catalog/712/download/22747) | Diccionario | `c1df4f3b58bf` |  |
| 2020 | [712](https://microdatos.dane.gov.co/index.php/catalog/712) | [Diccionario de datos 2020 base adicional_1.zip](https://microdatos.dane.gov.co/index.php/catalog/712/download/23517) | Diccionario | `c0eced6bf6f1` |  |
| 2020 | [712](https://microdatos.dane.gov.co/index.php/catalog/712) | [Diccionario_de_datos.zip](https://microdatos.dane.gov.co/index.php/catalog/712/download/21265) | Diccionario | `3c3c9e135cfa` |  |
| 2020 | [712](https://microdatos.dane.gov.co/index.php/catalog/712) | [Formulario_EMICRON_2020.pdf](https://microdatos.dane.gov.co/index.php/catalog/712/download/20398) | Formulario | `752f5a664389` |  |
| 2020 | [712](https://microdatos.dane.gov.co/index.php/catalog/712) | [Ficha_metodologica_EMICRON_2020.pdf](https://microdatos.dane.gov.co/index.php/catalog/712/download/20397) | Técnico | `e42b23a76c2c` |  |
| 2020 | [712](https://microdatos.dane.gov.co/index.php/catalog/712) | [Manual_recoleccion_EMICRON_2020.pdf](https://microdatos.dane.gov.co/index.php/catalog/712/download/20399) | Técnico | `62e042e2d777` |  |
| 2020 | [712](https://microdatos.dane.gov.co/index.php/catalog/712) | [Metodologia_EMICRON_2020.pdf](https://microdatos.dane.gov.co/index.php/catalog/712/download/20396) | Técnico | `a2db877733b6` |  |
| 2021 | [742](https://microdatos.dane.gov.co/index.php/catalog/742) | [DDI-EMICRON-2021.xml](https://microdatos.dane.gov.co/index.php/metadata/export/742/ddi) | DDI (metadatos) | `a9584df13d51` |  |
| 2021 | [742](https://microdatos.dane.gov.co/index.php/catalog/742) | [Diccionario de datos 2021 (base adicional).zip](https://microdatos.dane.gov.co/index.php/catalog/742/download/22750) | Diccionario | `ee56c1b5a170` |  |
| 2021 | [742](https://microdatos.dane.gov.co/index.php/catalog/742) | [Diccionario de datos 2021 base adicional.zip](https://microdatos.dane.gov.co/index.php/catalog/742/download/23520) | Diccionario | `27d11d21c7de` |  |
| 2021 | [742](https://microdatos.dane.gov.co/index.php/catalog/742) | [Formulario.pdf](https://microdatos.dane.gov.co/index.php/catalog/742/download/21402) | Formulario | `729597fb3542` |  |
| 2021 | [742](https://microdatos.dane.gov.co/index.php/catalog/742) | [Ficha_metodologica_EMICRON.pdf](https://microdatos.dane.gov.co/index.php/catalog/742/download/21246) | Técnico | `e42b23a76c2c` | igual a `2020/Ficha_metodologica_EMICRON_2020.pdf` |
| 2021 | [742](https://microdatos.dane.gov.co/index.php/catalog/742) | [Manual de recoleccion y conceptos basicos.pdf](https://microdatos.dane.gov.co/index.php/catalog/742/download/21260) | Técnico | `778db761a861` |  |
| 2021 | [742](https://microdatos.dane.gov.co/index.php/catalog/742) | [Metodologia_EMICRON.pdf](https://microdatos.dane.gov.co/index.php/catalog/742/download/21400) | Técnico | `a2db877733b6` | igual a `2020/Metodologia_EMICRON_2020.pdf` |
| 2022 | [796](https://microdatos.dane.gov.co/index.php/catalog/796) | [DDI-EMICRON-2022.xml](https://microdatos.dane.gov.co/index.php/metadata/export/796/ddi) | DDI (metadatos) | `cc33b06b0033` |  |
| 2022 | [796](https://microdatos.dane.gov.co/index.php/catalog/796) | [Diccionario de datos 2022_ANONIMIZADO_EMICRON.zip](https://microdatos.dane.gov.co/index.php/catalog/796/download/22665) | Diccionario | `df5a594fab56` |  |
| 2022 | [796](https://microdatos.dane.gov.co/index.php/catalog/796) | [08072022 Micronegocios_Formulario_2022_VER01.pdf](https://microdatos.dane.gov.co/index.php/catalog/796/download/22663) | Formulario | `21439ac7ee0f` |  |
| 2022 | [796](https://microdatos.dane.gov.co/index.php/catalog/796) | [12072022 EMICRON_Manual_2.pdf](https://microdatos.dane.gov.co/index.php/catalog/796/download/22664) | Técnico | `90ddefaf63b9` |  |
| 2022 | [796](https://microdatos.dane.gov.co/index.php/catalog/796) | [DSO-EMICRON-FME-001.pdf](https://microdatos.dane.gov.co/index.php/catalog/796/download/22715) | Técnico | `f2b7316d0309` |  |
| 2022 | [796](https://microdatos.dane.gov.co/index.php/catalog/796) | [DSO-EMICRON-MET-001-2022.pdf](https://microdatos.dane.gov.co/index.php/catalog/796/download/22666) | Técnico | `dc9c47c77258` |  |
| 2023 | [832](https://microdatos.dane.gov.co/index.php/catalog/832) | [DDI-EMICRON-2023.xml](https://microdatos.dane.gov.co/index.php/metadata/export/832/ddi) | DDI (metadatos) | `1adde26fb45d` |  |
| 2023 | [832](https://microdatos.dane.gov.co/index.php/catalog/832) | [Diccionario de datos 2022_ANONIMIZADO_EMICRON.zip](https://microdatos.dane.gov.co/index.php/catalog/832/download/23525) | Diccionario | `df5a594fab56` | igual a `2022/Diccionario de datos 2022_ANONIMIZADO_EMICRON.zip` |
| 2023 | [832](https://microdatos.dane.gov.co/index.php/catalog/832) | [08072022 Micronegocios_Formulario_2022_VER01.pdf](https://microdatos.dane.gov.co/index.php/catalog/832/download/23523) | Formulario | `21439ac7ee0f` | igual a `2022/08072022 Micronegocios_Formulario_2022_VER01.pdf` |
| 2023 | [832](https://microdatos.dane.gov.co/index.php/catalog/832) | [12072022 EMICRON_Manual_2.pdf](https://microdatos.dane.gov.co/index.php/catalog/832/download/23524) | Técnico | `90ddefaf63b9` | igual a `2022/12072022 EMICRON_Manual_2.pdf` |
| 2023 | [832](https://microdatos.dane.gov.co/index.php/catalog/832) | [DSO-EMICRON-FME-001.pdf](https://microdatos.dane.gov.co/index.php/catalog/832/download/23522) | Técnico | `f2b7316d0309` | igual a `2022/DSO-EMICRON-FME-001.pdf` |
| 2023 | [832](https://microdatos.dane.gov.co/index.php/catalog/832) | [DSO-EMICRON-MET-001-2022.pdf](https://microdatos.dane.gov.co/index.php/catalog/832/download/23521) | Técnico | `dc9c47c77258` | igual a `2022/DSO-EMICRON-MET-001-2022.pdf` |
| 2024 | [875](https://microdatos.dane.gov.co/index.php/catalog/875) | [DDI-EMICRON-2024.xml](https://microdatos.dane.gov.co/index.php/metadata/export/875/ddi) | DDI (metadatos) | `7d3ca01ec56e` |  |
| 2024 | [875](https://microdatos.dane.gov.co/index.php/catalog/875) | [Micronegocios_Formulario.pdf](https://microdatos.dane.gov.co/index.php/catalog/875/download/24180) | Formulario | `c448155d8431` |  |
| 2024 | [875](https://microdatos.dane.gov.co/index.php/catalog/875) | [DSO-EMICRON-FME-001_v1.pdf](https://microdatos.dane.gov.co/index.php/catalog/875/download/24182) | Técnico | `f69b0f823081` |  |
| 2024 | [875](https://microdatos.dane.gov.co/index.php/catalog/875) | [DSO-EMICRON-MET-001_v1.pdf](https://microdatos.dane.gov.co/index.php/catalog/875/download/24181) | Técnico | `ecd9141508d7` |  |
| 2024 | [875](https://microdatos.dane.gov.co/index.php/catalog/875) | [Diccionario_datos-Anonimizado-EMICRON-2024.xlsx](https://microdatos.dane.gov.co/index.php/catalog/875/download/24184) | Técnico | `45b755370859` |  |
| 2024 | [875](https://microdatos.dane.gov.co/index.php/catalog/875) | [Manual-EMICRON.pdf](https://microdatos.dane.gov.co/index.php/catalog/875/download/24183) | Técnico | `90ddefaf63b9` | igual a `2022/12072022 EMICRON_Manual_2.pdf` |
| 2025 | [914](https://microdatos.dane.gov.co/index.php/catalog/914) | [DDI-EMICRON-2025.xml](https://microdatos.dane.gov.co/index.php/metadata/export/914/ddi) | DDI (metadatos) | `fb88c90d9414` |  |
| 2025 | [914](https://microdatos.dane.gov.co/index.php/catalog/914) | [05112024  Micronegocios_Formulario.pdf](https://microdatos.dane.gov.co/index.php/catalog/914/download/24774) | Técnico | `c448155d8431` | igual a `2024/Micronegocios_Formulario.pdf` |
| 2025 | [914](https://microdatos.dane.gov.co/index.php/catalog/914) | [DSO-EMICRON-FME-001_v1.pdf](https://microdatos.dane.gov.co/index.php/catalog/914/download/24771) | Técnico | `f69b0f823081` | igual a `2024/DSO-EMICRON-FME-001_v1.pdf` |
| 2025 | [914](https://microdatos.dane.gov.co/index.php/catalog/914) | [DSO-EMICRON-MET-001_v1.pdf](https://microdatos.dane.gov.co/index.php/catalog/914/download/24772) | Técnico | `ecd9141508d7` | igual a `2024/DSO-EMICRON-MET-001_v1.pdf` |
| 2025 | [914](https://microdatos.dane.gov.co/index.php/catalog/914) | [Diccionario_datos-Anonimizado-EMICRON.xlsx](https://microdatos.dane.gov.co/index.php/catalog/914/download/24770) | Técnico | `9d3751f4f75c` |  |
| 2025 | [914](https://microdatos.dane.gov.co/index.php/catalog/914) | [Manual-EMICRON.pdf](https://microdatos.dane.gov.co/index.php/catalog/914/download/24773) | Técnico | `90ddefaf63b9` | igual a `2022/12072022 EMICRON_Manual_2.pdf` |
