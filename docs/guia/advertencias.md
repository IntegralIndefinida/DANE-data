# Advertencias metodológicas

- **Informalidad**: `formal` replica la medición oficial del DANE (17.ª CIET) con el código que el DANE
  publica en el anexo de *Empleo informal y seguridad social*: los formales e informales de cada mes desde
  2022 coinciden con los publicados. Antes de 2022 el cuestionario no tenía esas preguntas, y `formal` y
  `tasa_informalidad` quedan vacías (la serie oficial empieza en 2021, con la encuesta paralela, que no
  está en el ANDA). Para 2007–2021, `formal_marco2005` y `tasa_informalidad_marco2005` replican la medición
  anterior del DANE (empresas de hasta 5 personas), que coincide con la publicada para 13 y 23 ciudades.
  Las dos mediciones no son comparables entre sí.
- **Serie principal vs. empalme**: para series largas 2010–2020 comparables con 2021+, use `empalme=True`.
- **PET**: desde 2022 son las personas de 15 años o más; antes, 12+ (urbano) y 10+ (rural).
- **Ingresos**: `INGLABO` en pesos corrientes; la GEIH 2007 no lo trae. `ingreso_no_laboral` suma, sin
  imputar, las fuentes no laborales que el DANE cuenta en la pobreza monetaria, así que no da sus cifras.
- **EAM**: los montos vienen en miles de pesos corrientes. Según los propios archivos, la CIIU es
  Rev. 2 hasta 2000, Rev. 3 en 2001–2011 y Rev. 4 desde 2012 (la documentación del ANDA dice otra
  cosa; vea {doc}`diferencias`); los sectores no se comparan entre revisiones sin una
  correlativa.
- **EAM, composición por sector**: para anonimizar, el ANDA publica muchos establecimientos grandes con el
  código residual «otras industrias manufactureras» (3909, 3699 o 3290) o con el código truncado a 2–3
  dígitos. Los totales nacionales y por departamento coinciden con el DANE, pero la división residual sale
  inflada y las demás, subestimadas: en 2024 la división 32 suma el 11,0 % del valor agregado (2,2 % en el
  anexo del DANE) y bebidas el 5,3 % (9,7 %). Para la composición por sector, use los anexos del DANE.
- **EAM, análisis por establecimiento**: cada año, los valores de 13–25 % de los establecimientos, que suman
  la mitad del valor agregado o más, son el promedio de un grupo de establecimientos (casi siempre 3), no los
  propios. Sirven para agregados; para productividad, funciones de producción o paneles por planta,
  excluya o controle los registros `microagregado` (`dd.eam.panel(..., excluir_microagregados=True)`).
- **ECV, IPM de 2020**: con los colegios cerrados, el DANE armó la inasistencia escolar de 2020 con su base
  complementaria (estrategias de estudio en casa). `dd.ecv.download(2020)` la baja; sin ella, la incidencia de 2020 sale
  14,8 % y no 18,1 %, y `privaciones` avisa.
- **Estadísticas Vitales, tasas**: `dd.eevv.tasas` usa hechos registrados, sin ajustar por subregistro, así que no tiene por
  qué coincidir con los indicadores demográficos del DANE, que salen de un modelo. Los años antiguos salen más bajos que los
  reales. Por departamento y área se usa la residencia, y quedan por fuera los residentes en el extranjero y quienes no
  tienen el dato. Cada tasa sigue la fórmula de su ficha técnica del DANE (2026): la razón de mortalidad materna cuenta solo
  las muertes de hasta 42 días (sin O96 ni O97), y la mortalidad perinatal, los mortinatos y no todas las defunciones fetales.
- **Estadísticas Vitales, fuentes desde 2022**: además de los certificados del sector salud entran registros de la
  Registraduría y formatos de notificación étnica (`TIPOFORMULARIO`). Están en los conteos, como en los cuadros del DANE, pero
  los de la Registraduría no traen consultas, peso, sitio del parto ni departamento de residencia (1,7 % de los nacimientos
  de 2025).
- **Estadísticas Vitales, comparación en el tiempo**: las causas básicas pasan de CIE-9 a CIE-10 en 1997 (use `causa_105`
  para series largas), los archivos de 1979 y 1980 están incompletos, y enero–junio de 1991 no separa las edades de los
  menores de 10 años. El registro fue mejorando: parte de los cambios, sobre todo en defunciones fetales hasta 2012, es mejor
  cobertura.
- **Estadísticas Vitales, prematuridad**: solo se puede saber con `T_GES_AGRU_CIE`, que no está en 2012, 2013, 2020 ni antes de
  2008. `T_GES` agrupa «de 28 a 37» semanas, que mezcla prematuros con nacidos a término.
- **EMICRON, cobertura**: 2019–2024 cubren el total nacional (sin Amazonas, Arauca, Casanare, Guainía, Guaviare,
  Putumayo, Vaupés ni Vichada) y 2025 solo las 24 ciudades: para una serie con 2025, use las 24 ciudades en todos los
  años. 2025 no trae factor departamental (`fex_dpto`): `dd.emicron.indicadores` y `dd.tabla` dejan fuera esos
  registros con un aviso, en vez de contarlos como cero.
- **EMICRON, montos**: son mensuales y en pesos corrientes; `dd.emicron.indicadores` los da anuales y en miles de pesos,
  como el DANE. 2019 solo trae las ventas: consumo intermedio, valor agregado, ingreso mixto y remuneraciones quedan
  vacíos. El factor de expansión es anual (la suma del año es el total), y por eso el mes se llama `mes_ref`: con una
  columna `mes`, `dd.tabla` promediaría los meses como en la GEIH.
- **Muestras pequeñas**: con menos de ~100 observaciones (`n_muestra`) las cifras no son confiables.
- El salario mínimo histórico (`dd.SMLV`) está tomado de los decretos; verifíquelo antes de publicar.

Vea también {doc}`ponderacion` (tamaños de muestra y promedios mensuales) y {doc}`encuestas` (marcos
muestrales y {term}`serie de empalme`).
