# Diseño de losa aligerada unidireccional

Aplicación académica desarrollada con Python y Streamlit para diseñar una losa aligerada unidireccional con las normas peruanas E.020 y E.060.

## Funciones incluidas

- Predimensionamiento con la Tabla 9.1 de la E.060.
- Verificación geométrica de losas nervadas, numeral 8.11.
- Metrado y combinación de cargas.
- Momentos mediante el método aproximado del numeral 8.3.4.
- Diseño de secciones positivas como viga T y negativas como sección rectangular.
- Selección de barras con la ruta simplificada del numeral 10.5.3.
- Verificación de deformación neta de tracción.
- Verificación de cortante con el incremento permitido para nervaduras.
- Acero por retracción y temperatura.
- Longitud de desarrollo recta y longitud básica con gancho.
- Sección transversal dinámica.
- Memoria de cálculo en Excel.
- Detalle esquemático en DXF compatible con AutoCAD.

## Instalación en Windows con Anaconda

Abra **Anaconda Prompt** y ejecute:

```bash
cd RUTA\losa_aligerada_streamlit
conda create -n losa_e060 python=3.11 -y
conda activate losa_e060
pip install -r requirements.txt
streamlit run app.py
```

Streamlit abrirá la aplicación en el navegador. Si no lo hace, copie la dirección local que aparece en la terminal, normalmente `http://localhost:8501`.

Después de instalar las dependencias, también puede iniciar la aplicación con doble clic en `iniciar_app.bat`, siempre que el entorno de Python correspondiente esté activo.

## Validación del caso de clase

Desde la carpeta del proyecto:

```bash
python -m unittest discover -s tests -v
```

El caso de referencia utiliza tres tramos de 3,00 m, `f'c = 210 kgf/cm²`, `fy = 4200 kgf/cm²`, carga muerta de `530 kgf/m²` y carga viva de `200 kgf/m²`. La aplicación reproduce:

- `h = 17 cm`
- `wu = 1082 kgf/m²`
- `wu por vigueta = 0,4328 tf/m`
- `Mu positivo exterior = 0,3541 tf·m`
- `Mu positivo interior = 0,24345 tf·m`
- `Mu negativo interior = 0,38952 tf·m`
- acero de temperatura `Ø 1/4" @ 25 cm`

## Alcance del DXF

El archivo DXF contiene una sección transversal parametrizada y una elevación esquemática. Sirve como base gráfica y no reemplaza el plano estructural definitivo. Los cortes de barras, anclajes, traslapes y notas deben coordinarse con la geometría real del proyecto.

## Límites de uso

El método de coeficientes se habilita para dos o más tramos, carga uniformemente distribuida, secciones constantes, luces adyacentes con diferencia no mayor de 20 % y carga viva no mayor que tres veces la carga muerta. La aplicación avisa cuando alguna condición no se cumple, pero no sustituye el análisis estructural ni la revisión y firma de un ingeniero responsable.
