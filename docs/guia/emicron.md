# Micronegocios (EMICRON)

La Encuesta de Micronegocios (EMICRON) estudia las unidades económicas de **hasta 9 personas ocupadas**: los negocios
de los patrones y los trabajadores por cuenta propia. No tiene un marco propio: el DANE entrevista a los dueños que
encuentra la GEIH, así que cada micronegocio tiene la clave de su propietario en la GEIH (`directorio`, `secuencia_p`,
`secuencia_encuesta`). Es el puente entre los hogares (GEIH) y las empresas ({doc}`EAM <eam>`), y la fuente para
estudiar la informalidad empresarial, la productividad de los negocios pequeños y la inclusión financiera.

| Años | Cobertura | Micronegocios encuestados |
|---|---|---|
| 2019–2024 | Total nacional (sin Amazonas, Arauca, Casanare, Guainía, Guaviare, Putumayo, Vaupés ni Vichada) | 77 000 a 87 000 por año |
| 2025 | Solo las 24 ciudades principales y sus áreas metropolitanas | 53 624 |

## Descargar y cargar

```python
import dane_data as dd

dd.emicron.download(2024)                                 # un año: unos 45 MB de ZIP, 70 MB extraídos
dd.emicron.download(range(2019, 2025), modulos=["ventas", "costos"])
dd.emicron.download()                                     # toda la serie 2019–2025

emi = dd.emicron.load(2024)
```

```text
>>> emi[["anio", "mes_ref", "clase", "sexo", "actividad", "personal_ocupado", "fex", "rut"]].head(3)
   anio  mes_ref                              clase    sexo                                          actividad  personal_ocupado         fex    rut
0  2024        1  Centros poblados y rural disperso   Mujer                            Industria manufacturera                 1   60.050515  False
1  2024        1  Centros poblados y rural disperso  Hombre  Agricultura, ganadería, caza, silvicultura y p...                 1   86.341075  False
2  2024        1              Cabeceras municipales   Mujer                                           Comercio                 1  139.884518  False
```

Cada año el {term}`ANDA` publica un ZIP por módulo del formulario, y `download` extrae el CSV de cada uno a
`<carpeta>/datos/<año>/<módulo>.csv`. La identificación y los factores de expansión se bajan siempre, porque sin ellos
no se puede cargar. Los módulos están en `dd.emicron.MODULOS`, aunque no todos existen todos los años: 2020 no trae
inclusión financiera ni capital social, 2021 no trae capital social y el módulo de expectativas por el COVID-19 solo
existe en 2020.

{dd}`emicron.load()` une a la identificación los módulos que haya, por la clave del micronegocio, y deja una fila por
micronegocio. Toda la serie 2019–2025 carga en unos 6 segundos con las variables armonizadas. Con `columnas="all"` trae
también las preguntas del formulario con su nombre del DANE en minúscula, y con una lista agrega solo las que pida (por
ejemplo `columnas=["p3051", "p3034"]`, el motivo para crear el negocio y los meses que lleva). Las puede buscar con
{dd}`buscar_variable()` y `encuesta="emicron"`.

El módulo de personal ocupado tiene una fila por trabajador, socio o familiar, así que no entra en `load`: se carga con
{dd}`emicron.load_personal()`.

## Variables armonizadas

```{include} ../_generado/emicron_variables.md
```

Los montos son **mensuales y en pesos corrientes** del mes de referencia, con el nombre que les da el DANE. 2019 solo
trae las ventas: el consumo intermedio, el valor agregado, el ingreso mixto y las remuneraciones quedan vacíos (no en
cero).

## El factor de expansión

`fex` dice cuántos micronegocios representa cada registro **en el año**: la suma de los 12 meses es el total anual, no
un promedio mensual como en la GEIH. Por eso el mes se llama `mes_ref` y no `mes`: {dd}`tabla()` promedia los meses
cuando encuentra una columna `mes`. Con `mes_ref`, `dd.tabla` suma el factor tal cual y da las cifras del DANE:

```python
dd.tabla(emi, por=["sexo", "situacion_empleo"], estadistico="porcentaje")
```

```text
  sexo             situacion_empleo     total  n_muestra  porcentaje
Hombre           Patrón o empleador  388171.5       5096        11.3
Hombre Trabajador por cuenta propia 3033153.5      43989        88.7
 Mujer           Patrón o empleador  117023.8       1875         6.2
 Mujer Trabajador por cuenta propia 1758902.8      27541        93.8
```

`fex` es el de la serie vigente del DANE. En 2019–2021 es el factor «ajustado» de 2023, que viene en un archivo aparte,
porque el `F_EXP` que traen los módulos de esos años es el de la serie anterior. Desde 2022 es el `F_EXP` de la
identificación. Con él los totales coinciden con los anexos vigentes. Para cifras por departamento el DANE usa otro
factor, `fex_dpto`, que no existe en 2025: {dd}`emicron.indicadores()` y {dd}`tabla()` dejan fuera esos registros con
un aviso, en vez de contarlos como cero.

## Indicadores

{dd}`emicron.indicadores()` da, por grupo, las cifras del cuadro I.1 de los anexos del DANE («Resumen de las principales
variables») y tres de informalidad:

```python
dd.emicron.indicadores(dd.emicron.load(range(2019, 2025)))   # una fila por año
dd.emicron.indicadores(emi, por="actividad")
dd.emicron.indicadores(emi, por="departamento", peso="fex_dpto")
```

```text
 anio  micronegocios  personal_ocupado  valor_agregado  pct_rut
 2019      5215035.0         7296699.0             NaN     23.1
 2020      4819329.0         6397340.3    3.760150e+10     22.6
 2021      4921210.0         6542110.7    4.564952e+10     21.5
 2022      5150956.3         6887313.9    5.655814e+10     22.5
 2023      5188402.4         6748263.3    7.722177e+10     23.8
 2024      5297251.6         6879489.3    8.675564e+10     22.4
```

* `micronegocios` y `personal_ocupado` (el propietario más `trabajadores_remunerados`, `socios` y
  `familiares_sin_remuneracion`), expandidos.
* `ventas`, `consumo_intermedio`, `valor_agregado`, `remuneracion`, `sueldos`, `prestaciones` e `ingreso_mixto`, en
  **miles de pesos corrientes del año**: el mes de referencia por 12, como el cuadro I.1. En 2024, el valor agregado
  de los micronegocios fue de 86,8 billones de pesos.
* `coeficiente_tecnico`: el consumo intermedio sobre las ventas, en %.
* `pct_rut`, `pct_camara_comercio` y `pct_salud_pension` (el propietario aporta a salud y a pensión), sobre los
  micronegocios con el dato.

Las definiciones están en `dd.emicron.GLOSARIO` y en el {doc}`../glosario`. No hay intervalos de confianza ni
coeficientes de variación: los anexos los publican, pero los microdatos no traen el diseño muestral con que se calculan.

## Los trabajadores: `load_personal`

```python
per = dd.emicron.load_personal(2024)
dd.tabla(per, por=["tipo", "p3077"])   # tipo de contrato de los trabajadores remunerados
```

Cada fila es una persona ocupada distinta del propietario, con su `tipo` (trabajador remunerado, socio, o trabajador o
familiar sin remuneración), las preguntas del módulo y, del micronegocio, `fex`, `clase`, `ciudad`, `departamento` y
`actividad`. El `fex` es el del micronegocio. Para contar personas use `trabajadores_remunerados`, `socios` y
`familiares_sin_remuneracion` de `load`, que dan las cifras del DANE. El DANE corre los nombres de la clave en este
módulo; `load_personal` los deja como en los demás y numera a la persona en `orden` (vea {doc}`diferencias`).

## Qué tener en cuenta

* **2025 no es nacional.** Sus microdatos solo cubren las 24 ciudades, y `load` lo avisa. Para una serie comparable
  con 2025, quédese con las 24 ciudades en todos los años: `emi[emi.ciudad.notna()]`.
* **2019 no trae los montos calculados**, salvo las ventas. Y sus trabajadores remunerados salen 0,2 % por debajo del
  anexo, que los cuenta con el módulo de personal (vea {doc}`diferencias`).
* **Pesos corrientes.** Para comparar montos entre años hay que deflactar.
* **Muestras pequeñas.** Con pocos micronegocios encuestados (`n_muestra`) las cifras no son confiables, sobre todo por
  ciudad o departamento.
* **Cortes repetidos, no un panel.** Cada año son otros micronegocios: la EMICRON no sigue a los mismos negocios.

```{seealso}
El ejemplo {doc}`../ejemplos/micronegocios` sigue la informalidad de los micronegocios de 2019 a 2024, por actividad y
por ciudad.
```
