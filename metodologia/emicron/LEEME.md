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

## Resultados publicados (cifras para validar)

Boletines, anexos, presentaciones y comunicados de la EMICRON (2019 en adelante) en `resultados/`, bajados
de dane.gov.co (páginas «Micronegocios» y «Micronegocios históricos») el 2026-11-19. No incluye las
publicaciones de 2013-2015: son del módulo de micronegocios anterior a la EMICRON.

- Los anexos «(actualizado-abr2023)» de 2019-2022 reemplazan a los originales del mismo año; están los dos.
- `ciudades/`: informes por ciudad de 2019 y del 30 de marzo de 2020.
- Enlazados en la página pero el DANE responde 404 (no se pudieron bajar):
  - [Pres-micronegocios-2019-webinar.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Pres-micronegocios-2019-webinar.pdf)
  - [anex-EMICRON-IIItrim2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IIItrim2024.xlsx)

| Tipo | Archivo | sha256 |
|---|---|---|
| Anexo | [Anex-II-2022.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anex-II-2022.xlsx) | `1e949652b136` |
| Anexo | [Anexo-nacional-micronegocios-2019.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo-nacional-micronegocios-2019.xlsx) | `1c402ba1b483` |
| Anexo | [Anexo_2019-2021.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_2019-2021.xlsx) | `bcb34edf3e7a` |
| Anexo | [Anexo_24_ciudades_2019-(actualizado-abr2023).xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_24_ciudades_2019-(actualizado-abr2023).xlsx) | `e542c299771e` |
| Anexo | [Anexo_24_ciudades_2019.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_24_ciudades_2019.xlsx) | `e21888bc57e6` |
| Anexo | [Anexo_24_ciudades_2020-(actualizado-abr2023).xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_24_ciudades_2020-(actualizado-abr2023).xlsx) | `3156c76e032e` |
| Anexo | [Anexo_24_ciudades_2020.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_24_ciudades_2020.xlsx) | `6a07d5dcfcfc` |
| Anexo | [Anexo_24_ciudades_2021-(actualizado-abr2023).xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_24_ciudades_2021-(actualizado-abr2023).xlsx) | `71f10c426a95` |
| Anexo | [Anexo_24_ciudades_2021.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_24_ciudades_2021.xlsx) | `50cf3560eee4` |
| Anexo | [Anexo_24_ciudades_2022-(actualizado-abr2023).xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_24_ciudades_2022-(actualizado-abr2023).xlsx) | `ffbb39ed3850` |
| Anexo | [Anexo_I2022.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_I2022.xlsx) | `53c229597c6c` |
| Anexo | [Anexo_total_nacional_2019-(actualizado-abr2023).xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_total_nacional_2019-(actualizado-abr2023).xlsx) | `c2c0a94251c9` |
| Anexo | [Anexo_total_nacional_2019.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_total_nacional_2019.xlsx) | `512618cc34da` |
| Anexo | [Anexo_total_nacional_2020-(actualizado-abr2023).xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_total_nacional_2020-(actualizado-abr2023).xlsx) | `6d7924105409` |
| Anexo | [Anexo_total_nacional_2020.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_total_nacional_2020.xlsx) | `de2cbb356e55` |
| Anexo | [Anexo_total_nacional_2021-(actualizado-abr2023).xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_total_nacional_2021-(actualizado-abr2023).xlsx) | `6997fe28096c` |
| Anexo | [Anexo_total_nacional_2021.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_total_nacional_2021.xlsx) | `b7d56fba129c` |
| Anexo | [Anexo_total_nacional_2022-(actualizado-abr2023).xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexo_total_nacional_2022-(actualizado-abr2023).xlsx) | `a2caddd315c8` |
| Anexo | [Anexos_III_2022.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexos_III_2022.xlsx) | `a3251865003d` |
| Anexo | [Anexos_IV_2022.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Anexos_IV_2022.xlsx) | `e8e5042780f3` |
| Anexo | [anex-Ciudades-EMICRON-2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-Ciudades-EMICRON-2024.xlsx) | `3f45ad4c209c` |
| Anexo | [anex-Departamentos-EMICRON-2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-Departamentos-EMICRON-2024.xlsx) | `d552b55806c3` |
| Anexo | [anex-EMICRON-2023.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-2023.xlsx) | `ae38909c1477` |
| Anexo | [anex-EMICRON-2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-2024.xlsx) | `679a8d4226f0` |
| Anexo | [anex-EMICRON-24Ciudades-2023.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-24Ciudades-2023.xlsx) | `4196fe29250d` |
| Anexo | [anex-EMICRON-24Ciudades-2025.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-24Ciudades-2025.xlsx) | `51cdf94bdae4` |
| Anexo | [anex-EMICRON-IIITrim2023.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IIITrim2023.xlsx) | `2fba8700ad2d` |
| Anexo | [anex-EMICRON-IIItrim2025.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IIItrim2025.xlsx) | `e650a8ada5e9` |
| Anexo | [anex-EMICRON-IITrim2023.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IITrim2023.xlsx) | `a7e4ccf44a69` |
| Anexo | [anex-EMICRON-IItrim2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IItrim2024.xlsx) | `0741bbebf406` |
| Anexo | [anex-EMICRON-IItrim2025.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IItrim2025.xlsx) | `474880bb171b` |
| Anexo | [anex-EMICRON-IItrim2026.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IItrim2026.xlsx) | `534ae92f2061` |
| Anexo | [anex-EMICRON-ITrim2023.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-ITrim2023.xlsx) | `7694e4d711d9` |
| Anexo | [anex-EMICRON-IVTrim2023.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IVTrim2023.xlsx) | `5243239f5ce8` |
| Anexo | [anex-EMICRON-IVtrim2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IVtrim2024.xlsx) | `b8d18f398881` |
| Anexo | [anex-EMICRON-IVtrim2025.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-IVtrim2025.xlsx) | `0360960cc509` |
| Anexo | [anex-EMICRON-Itrim2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-Itrim2024.xlsx) | `d40e24e0421f` |
| Anexo | [anex-EMICRON-Itrim2025.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-Itrim2025.xlsx) | `d0f5bab02874` |
| Anexo | [anex-EMICRON-Itrim2026.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-Itrim2026.xlsx) | `e7bbc2cec636` |
| Anexo | [anex-EMICRON-ModuloConstruccion-2022-2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-ModuloConstruccion-2022-2024.xlsx) | `b055ca6003c4` |
| Anexo | [anex-EMICRON-SectorConstruccion-2022.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-SectorConstruccion-2022.xlsx) | `bacf7b3e2e76` |
| Anexo | [anex-EMICRON-SectorConstruccion-2023.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-SectorConstruccion-2023.xlsx) | `2dadff0e213b` |
| Anexo | [anex-EMICRON-SectorConstruccion-2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRON-SectorConstruccion-2024.xlsx) | `57514017b51a` |
| Anexo | [anex-EMICRONDep-2020.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRONDep-2020.xlsx) | `62bc47b1f0b5` |
| Anexo | [anex-EMICRONDep-2021.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRONDep-2021.xlsx) | `e9854a88faa6` |
| Anexo | [anex-EMICRONDep-2022.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRONDep-2022.xlsx) | `ee01aeee7f26` |
| Anexo | [anex-EMICRONDep-2023.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRONDep-2023.xlsx) | `6250f8ef3242` |
| Anexo | [anex-EMICRONVendedoresAmbulantes-2023.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRONVendedoresAmbulantes-2023.xlsx) | `f096f7cbddb8` |
| Anexo | [anex-EMICRONVendedoresAmbulantes-2024.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRONVendedoresAmbulantes-2024.xlsx) | `d7df4941bea2` |
| Anexo | [anex-EMICRONVendedoresAmbulantes-2025.xlsx](https://www.dane.gov.co/files/operaciones/EMICRON/anex-EMICRONVendedoresAmbulantes-2025.xlsx) | `f9e360d9340c` |
| Anexo | [anexo-24-ciudades-micronegocios-2020.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-24-ciudades-micronegocios-2020.xlsx) | `8b68c87e2859` |
| Anexo | [anexo-24-ciudades-micronegocios-variaciones-2020.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-24-ciudades-micronegocios-variaciones-2020.xlsx) | `b28b39c26dc6` |
| Anexo | [anexo-ciudades-micronegocios-2019.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-ciudades-micronegocios-2019.xlsx) | `5f70d48e64a8` |
| Anexo | [anexo-micronegocios-I-2020.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-micronegocios-I-2020.xlsx) | `e519dfe1831a` |
| Anexo | [anexo-micronegocios-II-2020.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-micronegocios-II-2020.xlsx) | `d041ab900048` |
| Anexo | [anexo-micronegocios-III-2021.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-micronegocios-III-2021.xlsx) | `6d9850076c61` |
| Anexo | [anexo-micronegocios-IV-2021.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-micronegocios-IV-2021.xlsx) | `50194ea15fc2` |
| Anexo | [anexo-micronegocios-pobreza-condiciones-de-vida-propietarios-2019-2020.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-micronegocios-pobreza-condiciones-de-vida-propietarios-2019-2020.xlsx) | `8dd70c729d3e` |
| Anexo | [anexo-nacional-micronegocios-2020.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-nacional-micronegocios-2020.xlsx) | `738b439f08d0` |
| Anexo | [anexo-nacional-micronegocios-covid-2020.xlsx](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/anexo-nacional-micronegocios-covid-2020.xlsx) | `38908aa6a21f` |
| Boletín | [bol-Departamentos-EMICRON-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-Departamentos-EMICRON-2024.pdf) | `716a69f832fa` |
| Boletín | [bol-EMICRON-2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-2023.pdf) | `5a257bf5e93e` |
| Boletín | [bol-EMICRON-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-2024.pdf) | `9572c2d7e2a4` |
| Boletín | [bol-EMICRON-24Ciudades-2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-24Ciudades-2025.pdf) | `b629f7d55bd5` |
| Boletín | [bol-EMICRON-IIITrim2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IIITrim2023.pdf) | `51341b528172` |
| Boletín | [bol-EMICRON-IIItrim2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IIItrim2024.pdf) | `3b163c46ccfd` |
| Boletín | [bol-EMICRON-IIItrim2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IIItrim2025.pdf) | `9fcfd8074ad7` |
| Boletín | [bol-EMICRON-IITrim2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IITrim2023.pdf) | `9333306ff45a` |
| Boletín | [bol-EMICRON-IItrim2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IItrim2024.pdf) | `2fd9502f80c5` |
| Boletín | [bol-EMICRON-IItrim2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IItrim2025.pdf) | `3d72a886fbe5` |
| Boletín | [bol-EMICRON-IItrim2026.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IItrim2026.pdf) | `aeb390836f99` |
| Boletín | [bol-EMICRON-ITrim2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-ITrim2023.pdf) | `5abf6745bc2f` |
| Boletín | [bol-EMICRON-IVTrim2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IVTrim2023.pdf) | `aa3b2c23e168` |
| Boletín | [bol-EMICRON-IVtrim2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IVtrim2024.pdf) | `91ff243bad5d` |
| Boletín | [bol-EMICRON-IVtrim2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-IVtrim2025.pdf) | `c4ea4b27969f` |
| Boletín | [bol-EMICRON-Itrim2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-Itrim2024.pdf) | `76a1c6eb3a56` |
| Boletín | [bol-EMICRON-Itrim2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-Itrim2025.pdf) | `6182082eadf4` |
| Boletín | [bol-EMICRON-Itrim2026.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-Itrim2026.pdf) | `742a21aeb318` |
| Boletín | [bol-EMICRON-PanaderiasTiendasBarrio-2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-PanaderiasTiendasBarrio-2023.pdf) | `d770d079a108` |
| Boletín | [bol-EMICRON-PanaderiasTiendasBarrio-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-PanaderiasTiendasBarrio-2024.pdf) | `2fe37896e7ec` |
| Boletín | [bol-EMICRON-SectorConstruccion-2022.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-SectorConstruccion-2022.pdf) | `c910883a9564` |
| Boletín | [bol-EMICRON-SectorConstruccion-2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-SectorConstruccion-2023.pdf) | `124f7f11172d` |
| Boletín | [bol-EMICRON-SectorConstruccion-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRON-SectorConstruccion-2024.pdf) | `e188acae486f` |
| Boletín | [bol-EMICRONDep-2022.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRONDep-2022.pdf) | `7f1b844b6a14` |
| Boletín | [bol-EMICRONDep-2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRONDep-2023.pdf) | `70510897aa97` |
| Boletín | [bol-EMICRONVendedoresAmbulantes-2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRONVendedoresAmbulantes-2023.pdf) | `23001c3b779d` |
| Boletín | [bol-EMICRONVendedoresAmbulantes-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRONVendedoresAmbulantes-2024.pdf) | `f310915e2cf6` |
| Boletín | [bol-EMICRONVendedoresAmbulantes-2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/bol-EMICRONVendedoresAmbulantes-2025.pdf) | `8bf6c65d97bb` |
| Boletín | [bol-micronegocios-2019-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-2019-2021.pdf) | `61889e90ce8f` |
| Boletín | [bol-micronegocios-2019-ene-oct.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-2019-ene-oct.pdf) | `fcc66fe139b9` |
| Boletín | [bol-micronegocios-2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-2019.pdf) | `45ff887abf71` |
| Boletín | [bol-micronegocios-2020.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-2020.pdf) | `b1d749204e77` |
| Boletín | [bol-micronegocios-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-2021.pdf) | `6b6b0d6672ab` |
| Boletín | [bol-micronegocios-2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-2022.pdf) | `4e2c68da3b31` |
| Boletín | [bol-micronegocios-I-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-I-2021.pdf) | `528d7f30f35b` |
| Boletín | [bol-micronegocios-I2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-I2022.pdf) | `fac8c1953b51` |
| Boletín | [bol-micronegocios-II-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-II-2021.pdf) | `6b5d33902bc4` |
| Boletín | [bol-micronegocios-II-2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-II-2022.pdf) | `b17420a4ba95` |
| Boletín | [bol-micronegocios-III-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-III-2021.pdf) | `35f537e5524a` |
| Boletín | [bol-micronegocios-III-2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-III-2022.pdf) | `25dc8103996d` |
| Boletín | [bol-micronegocios-IV-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-IV-2021.pdf) | `9061b325901a` |
| Boletín | [bol-micronegocios-IV-2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-IV-2022.pdf) | `8c5d6808d0e1` |
| Boletín | [bol-micronegocios-covid-2020.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/bol-micronegocios-covid-2020.pdf) | `323c2d0f89a2` |
| Comunicado | [CP-micronegocios-2019-ene-oct.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/CP-micronegocios-2019-ene-oct.pdf) | `4e03d567a896` |
| Comunicado | [CP-micronegocios-2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/CP-micronegocios-2019.pdf) | `6d51de3ef278` |
| Comunicado | [CP-micronegocios-2020-ene-oct.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/CP-micronegocios-2020-ene-oct.pdf) | `657f4b270274` |
| Comunicado | [CP_emicron_clases sociales.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/CP_emicron_clases%20sociales.pdf) | `c3586972be3f` |
| Informe | [2019-ene-dic-informe-micronegocio-peluqueria-tratamientos-belleza.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/2019-ene-dic-informe-micronegocio-peluqueria-tratamientos-belleza.pdf) | `49aadd95c1e3` |
| Informe | [2019-ene-dic-informe-micronegocio-serv-comidas-bebidas.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/2019-ene-dic-informe-micronegocio-serv-comidas-bebidas.pdf) | `eee44bd21aca` |
| Informe | [ciudades/informe_Armenia_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Armenia_30mar_20.pdf) | `4d8e89ce4712` |
| Informe | [ciudades/informe_Barranquilla_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Barranquilla_30mar_20.pdf) | `7a0b599ea79b` |
| Informe | [ciudades/informe_Bogota_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Bogota_30mar_20.pdf) | `4c396cf7b845` |
| Informe | [ciudades/informe_Bucaramanga_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Bucaramanga_30mar_20.pdf) | `3d247d01de43` |
| Informe | [ciudades/informe_Cali_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Cali_30mar_20.pdf) | `051e61f80c94` |
| Informe | [ciudades/informe_Cartagena_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Cartagena_30mar_20.pdf) | `fff446292fb2` |
| Informe | [ciudades/informe_Cucuta_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Cucuta_30mar_20.pdf) | `0b0c2c3b28b8` |
| Informe | [ciudades/informe_Florencia_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Florencia_30mar_20.pdf) | `0f35e5b6af3a` |
| Informe | [ciudades/informe_Ibague_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Ibague_30mar_20.pdf) | `05e449a315ad` |
| Informe | [ciudades/informe_Manizales_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Manizales_30mar_20.pdf) | `eac1bb6ea1a6` |
| Informe | [ciudades/informe_Medellin_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Medellin_30mar_20.pdf) | `8a7a681ca112` |
| Informe | [ciudades/informe_Monteria_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Monteria_30mar_20.pdf) | `8a48a8c20304` |
| Informe | [ciudades/informe_Neiva_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Neiva_30mar_20.pdf) | `1aef7eaa98a6` |
| Informe | [ciudades/informe_Pasto_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Pasto_30mar_20.pdf) | `62210d0bd8a0` |
| Informe | [ciudades/informe_Pereira_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Pereira_30mar_20.pdf) | `c9c774771d17` |
| Informe | [ciudades/informe_Popayan_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Popayan_30mar_20.pdf) | `5483529c7303` |
| Informe | [ciudades/informe_Quibdo_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Quibdo_30mar_20.pdf) | `a6d3b350697c` |
| Informe | [ciudades/informe_Riohacha_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Riohacha_30mar_20.pdf) | `cbf7e483a12f` |
| Informe | [ciudades/informe_SantaMarta_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_SantaMarta_30mar_20.pdf) | `f4922e481590` |
| Informe | [ciudades/informe_Sincelejo_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Sincelejo_30mar_20.pdf) | `faaa1e5d7312` |
| Informe | [ciudades/informe_Tunja_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Tunja_30mar_20.pdf) | `038b872d6e33` |
| Informe | [ciudades/informe_Valledupar_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Valledupar_30mar_20.pdf) | `a32118d7f676` |
| Informe | [ciudades/informe_Villavicencio_30mar_20.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/informe_Villavicencio_30mar_20.pdf) | `32e08c07eec4` |
| Informe | [ciudades/micronegocios_informe_Armenia_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Armenia_2019.pdf) | `6de14252fa31` |
| Informe | [ciudades/micronegocios_informe_Barranquilla_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Barranquilla_2019.pdf) | `632c41c43f69` |
| Informe | [ciudades/micronegocios_informe_Bogota_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Bogota_2019.pdf) | `d0981dd56a50` |
| Informe | [ciudades/micronegocios_informe_Bucaramanga_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Bucaramanga_2019.pdf) | `bad7fde736e4` |
| Informe | [ciudades/micronegocios_informe_Cali_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Cali_2019.pdf) | `2370f2a28971` |
| Informe | [ciudades/micronegocios_informe_Cartagena_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Cartagena_2019.pdf) | `f8bdadfc1e34` |
| Informe | [ciudades/micronegocios_informe_Cucuta_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Cucuta_2019.pdf) | `7765f4cb43db` |
| Informe | [ciudades/micronegocios_informe_Florencia_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Florencia_2019.pdf) | `613bafd84a11` |
| Informe | [ciudades/micronegocios_informe_Ibague_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Ibague_2019.pdf) | `1f899dd903f5` |
| Informe | [ciudades/micronegocios_informe_Manizales_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Manizales_2019.pdf) | `a0e842715913` |
| Informe | [ciudades/micronegocios_informe_Medellin_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Medellin_2019.pdf) | `b55201cad730` |
| Informe | [ciudades/micronegocios_informe_Monteria_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Monteria_2019.pdf) | `3b73188d21dd` |
| Informe | [ciudades/micronegocios_informe_Neiva_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Neiva_2019.pdf) | `84630462e075` |
| Informe | [ciudades/micronegocios_informe_Pasto_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Pasto_2019.pdf) | `60ba58c48c1e` |
| Informe | [ciudades/micronegocios_informe_Pereira_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Pereira_2019.pdf) | `f7964701f6fc` |
| Informe | [ciudades/micronegocios_informe_Popayan_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Popayan_2019.pdf) | `cb5282d0fe3d` |
| Informe | [ciudades/micronegocios_informe_Quibdo_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Quibdo_2019.pdf) | `715746c96631` |
| Informe | [ciudades/micronegocios_informe_Riohacha_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Riohacha_2019.pdf) | `4d875c103fa8` |
| Informe | [ciudades/micronegocios_informe_SantaMarta_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_SantaMarta_2019.pdf) | `d1894e696db9` |
| Informe | [ciudades/micronegocios_informe_Sincelejo_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Sincelejo_2019.pdf) | `32c830a8adce` |
| Informe | [ciudades/micronegocios_informe_Tunja_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Tunja_2019.pdf) | `a62975ff1c44` |
| Informe | [ciudades/micronegocios_informe_Valledupar_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Valledupar_2019.pdf) | `5437e5abdbeb` |
| Informe | [ciudades/micronegocios_informe_Villavicencio_2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/ciudades/micronegocios_informe_Villavicencio_2019.pdf) | `7ae9669e5570` |
| Presentación | [Pres-micronegocios-2019.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Pres-micronegocios-2019.pdf) | `87a3429dcd00` |
| Presentación | [Pres-micronegocios-2020-ene-oct.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/Pres-micronegocios-2020-ene-oct.pdf) | `b914f77dd167` |
| Presentación | [pres-Departamentos-EMICRON-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-Departamentos-EMICRON-2024.pdf) | `e0838f9a261b` |
| Presentación | [pres-EMICRON-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-2024.pdf) | `3191df601dca` |
| Presentación | [pres-EMICRON-24Ciudades-2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-24Ciudades-2025.pdf) | `2b24869f3bda` |
| Presentación | [pres-EMICRON-IIITrim2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IIITrim2023.pdf) | `7202e84021fd` |
| Presentación | [pres-EMICRON-IIItrim2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IIItrim2024.pdf) | `88a94e244054` |
| Presentación | [pres-EMICRON-IIItrim2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IIItrim2025.pdf) | `1dbfa1a008b8` |
| Presentación | [pres-EMICRON-IITrim2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IITrim2023.pdf) | `b452fca85ba8` |
| Presentación | [pres-EMICRON-IItrim2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IItrim2024.pdf) | `fe4e3fdc2363` |
| Presentación | [pres-EMICRON-IItrim2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IItrim2025.pdf) | `d38e02ab9595` |
| Presentación | [pres-EMICRON-IItrim2026.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IItrim2026.pdf) | `4a631fa3294e` |
| Presentación | [pres-EMICRON-ITrim2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-ITrim2023.pdf) | `8f993361e7b5` |
| Presentación | [pres-EMICRON-IVTrim2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IVTrim2023.pdf) | `2a9f6c803564` |
| Presentación | [pres-EMICRON-IVtrim2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IVtrim2024.pdf) | `192dc38c1741` |
| Presentación | [pres-EMICRON-IVtrim2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-IVtrim2025.pdf) | `9603ccbb149a` |
| Presentación | [pres-EMICRON-Itrim2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-Itrim2024.pdf) | `4a33d8941302` |
| Presentación | [pres-EMICRON-Itrim2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-Itrim2025.pdf) | `6338d8fbe081` |
| Presentación | [pres-EMICRON-Itrim2026.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-Itrim2026.pdf) | `2d13496a6a94` |
| Presentación | [pres-EMICRON-PanaderiasTiendasBarrio-2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-PanaderiasTiendasBarrio-2023.pdf) | `5303d063c6d8` |
| Presentación | [pres-EMICRON-PanaderiasTiendasBarrio-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-PanaderiasTiendasBarrio-2024.pdf) | `fbee98e3913f` |
| Presentación | [pres-EMICRON-SectorConstruccion-2022.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-SectorConstruccion-2022.pdf) | `538bc84e3134` |
| Presentación | [pres-EMICRON-SectorConstruccion-2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-SectorConstruccion-2023.pdf) | `5a3b2fe6acf0` |
| Presentación | [pres-EMICRON-SectorConstruccion-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRON-SectorConstruccion-2024.pdf) | `c8c290d6fa04` |
| Presentación | [pres-EMICRONDep-2022.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRONDep-2022.pdf) | `4cd3005c60b7` |
| Presentación | [pres-EMICRONDep-2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRONDep-2023.pdf) | `e155b33e9fad` |
| Presentación | [pres-EMICRONVendedoresAmbulantes-2023.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRONVendedoresAmbulantes-2023.pdf) | `c4ed88655b3e` |
| Presentación | [pres-EMICRONVendedoresAmbulantes-2024.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRONVendedoresAmbulantes-2024.pdf) | `ec3d7526e8d0` |
| Presentación | [pres-EMICRONVendedoresAmbulantes-2025.pdf](https://www.dane.gov.co/files/operaciones/EMICRON/pres-EMICRONVendedoresAmbulantes-2025.pdf) | `12ede62181af` |
| Presentación | [presentacion-micronegocios-2019-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-2019-2021.pdf) | `9b2352a8365f` |
| Presentación | [presentacion-micronegocios-2020.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-2020.pdf) | `f5b42cdcf213` |
| Presentación | [presentacion-micronegocios-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-2021.pdf) | `e4ac4f3ed244` |
| Presentación | [presentacion-micronegocios-2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-2022.pdf) | `8f71ebd90abc` |
| Presentación | [presentacion-micronegocios-I-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-I-2021.pdf) | `234c2ac7f6f7` |
| Presentación | [presentacion-micronegocios-I2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-I2022.pdf) | `79042ad35055` |
| Presentación | [presentacion-micronegocios-II-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-II-2021.pdf) | `8e559f070f9f` |
| Presentación | [presentacion-micronegocios-II-2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-II-2022.pdf) | `1d40979073bc` |
| Presentación | [presentacion-micronegocios-III-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-III-2021.pdf) | `24fda821d851` |
| Presentación | [presentacion-micronegocios-III-2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-III-2022.pdf) | `d67abd048ae3` |
| Presentación | [presentacion-micronegocios-IV-2021.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-IV-2021.pdf) | `d87b88c66036` |
| Presentación | [presentacion-micronegocios-IV-2022.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-IV-2022.pdf) | `1c11b7950ff6` |
| Presentación | [presentacion-micronegocios-pobreza-condiciones-de-vida-propietarios-2019-2020.pdf](https://www.dane.gov.co/files/investigaciones/boletines/ech/micro/presentacion-micronegocios-pobreza-condiciones-de-vida-propietarios-2019-2020.pdf) | `8183e8ee6845` |
