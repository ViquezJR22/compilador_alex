# Presentación del compilador ALEX

Duración sugerida: 7 a 8 minutos. Dos partes: características del lenguaje y demostración. Después, las preguntas de dominio de conceptos.

## Parte 1: Características de ALEX (2 minutos)

Decir con mis palabras:

1. **Qué es:** un lenguaje con palabras en español (`dato`, `entero`, `verdadero`) para que el código se lea fácil.
2. **Declaración:** `dato nombre: tipo;` o con valor inicial `dato nombre: tipo = valor;`. Toda instrucción termina con `;`.
3. **Asignación:** `nombre = expresion;`. La variable debe existir y el valor debe ser del mismo tipo.
4. **Cuatro tipos:** entero, decimal, texto y logico. El tipo se reconoce por cómo está escrito el valor: `5` es entero, `5.0` es decimal, `"25"` es texto.
5. **Compatibilidad:** un entero cabe en un decimal, pero un decimal no cabe en un entero.
6. **Nombres:** empiezan con letra o `_`, distinguen mayúsculas, no pueden ser palabras reservadas ni repetirse.
7. **Valores por defecto:** 0, 0.0, texto vacío y falso.
8. **Prohibido:** asignaciones encadenadas (`a = b = 3;`).
9. **Operadores:** `+ - * /` y paréntesis, que agregué porque mis ejemplos ya usaban `edad + 1`.
10. **Funciones propias:** `funcion suma(a: entero, b: entero): entero { retornar a + b; }`. El tipo de retorno es opcional: sin él, la función solo hace algo y no devuelve nada.
11. **Ámbito:** cada función tiene su propio espacio. Ve sus parámetros y sus variables locales, pero no las globales; lo que necesita lo recibe como parámetro.
12. **Funciones predefinidas:** `mostrar`, `longitud`, `mayusculas`, `redondear` y `absoluto`. Con `mostrar` el lenguaje por fin tiene salida en pantalla.
13. **Reglas de las funciones:** se definen antes de usarse, los argumentos deben coincidir en cantidad y tipo, no puede haber código después de `retornar`, y no pueden llamarse a sí mismas porque ALEX todavía no tiene condicionales y la recursión nunca terminaría.

## Parte 2: Demostración (4 minutos)

| Paso | Comando | Qué señalar |
|---|---|---|
| 1 | Mostrar `ejemplos/ok.alex` | Los cuatro tipos, una asignación con expresión y un comentario |
| 2 | `python alex.py ejemplos/ok.alex --tokens` | Tabla de tokens, árbol AST, AST Table, ejecución paso a paso y tabla de símbolos |
| 3 | Señalar la tabla de símbolos | `edad` pasa de 21 a 22 y `promedio` empieza en 0.0 por defecto |
| 4 | `python alex.py ejemplos/err_lexico.alex` | Carácter `@`, decimal `3.` y texto sin cerrar |
| 5 | `python alex.py ejemplos/err_sintactico.alex` | Falta `;`, falta `:`, `a = b = 3;`, palabra reservada como nombre |
| 6 | `python alex.py ejemplos/err_semantico.alex` | Variable no declarada, redeclarada, decimal en entero. No se ejecuta nada |
| 7 | Mostrar `ejemplos/funciones.alex` | Tres funciones propias (una con retorno entero, una con decimal, una sin retorno) y las cinco predefinidas |
| 8 | `python alex.py ejemplos/funciones.alex` | El nodo `Funcion` y `Llamada` en el árbol, "SALIDA DEL PROGRAMA", y la tabla de símbolos con la columna **Ámbito** (`resultado` vive solo en `suma`) junto con la tabla de funciones |
| 9 | `python alex.py ejemplos/err_func_semantico.alex` | Argumentos de más o de menos, tipo de argumento incorrecto, función no definida, `retornar` fuera de función, código inalcanzable y una función que no ve una variable global |
| 10 | `python alex.py ejemplos/err_func_sintactico.alex` | Paréntesis sin cerrar, función dentro de otra, coma sobrante y falta de `}` |

Para mostrar dónde vive cada fase en el código, buscar con `Ctrl+F`: `analizar_lexico`, `class Parser`, `class Semantico`, `ejecutar`.

## Parte 3: Dominio de conceptos (preguntas probables)

**¿Qué hace cada fase?**
- Léxica: lee el texto carácter por carácter y lo agrupa en tokens.
- Sintáctica: comprueba que los tokens sigan la gramática y construye el árbol.
- Semántica: comprueba el significado (declaraciones, tipos, duplicados).
- Ejecución: recorre el árbol y calcula los valores.

**¿Qué es un token, un lexema y un patrón?**
Un lexema es el texto concreto (`edad`), un token es su categoría (`IDENT`) y el patrón es la regla que lo describe (empieza con letra o `_`, sigue con letras, números o `_`).

**¿Qué es una gramática libre de contexto?**
Un conjunto de reglas de producción que describe qué programas son válidos. La mía está escrita en notación BNF en el `README.md`.

**¿Qué tipo de parser usé?**
Un descendente recursivo: una función por cada regla de la gramática. Decide con solo mirar el token actual (por ejemplo, `dato` inicia una declaración y un identificador inicia una asignación), por eso no necesita retroceder.

**¿Cómo resuelvo la precedencia de operadores?**
Con la propia gramática. `*` y `/` están en `termino`, un nivel más profundo que `+` y `-` en `expresion`, así que se agrupan primero. Los ciclos `{ ... }` hacen que se evalúen de izquierda a derecha.

**¿Qué es el AST y en qué se diferencia del árbol de derivación?**
El AST guarda solo lo esencial. No tiene nodos para `;`, `:` ni paréntesis, porque su efecto ya está en la forma del árbol. Un árbol de derivación tendría un nodo por cada regla aplicada.

**¿Qué es la AST Table?**
Es el mismo árbol en forma de tabla: cada nodo con un ID, su tipo, valor, tipo de dato, padre, hijos y línea.

**¿Qué guarda la tabla de símbolos y cuándo se llena?**
Una entrada por variable o parámetro: nombre, tipo, clase, ámbito, línea de declaración, asignaciones, lecturas, valor inicial y valor final. Se llena durante el análisis semántico, y los valores de las globales se completan al ejecutar. Además hay una tabla de funciones con su firma y las veces que se llamaron.

**¿Qué verifica el análisis semántico que el sintáctico no puede?**
Que la variable exista, que no se declare dos veces y que los tipos sean compatibles. Una instrucción como `edad = "veinte";` está bien escrita (la gramática la acepta) pero no tiene sentido porque `edad` es entera.

**¿Qué es la coerción de tipos?**
Una conversión automática. En ALEX solo hay una: un entero se convierte a decimal (`precio = 5;` guarda `5.0`). La contraria no existe porque perdería información.

**¿Cómo manejo los errores?**
Cada error indica fase, línea, columna y la línea de código con una flecha. El parser, al fallar, salta hasta el siguiente `;` y sigue revisando (recuperación en modo pánico), por eso reporta varios errores en una sola corrida. Un error en una fase detiene las siguientes.

**¿Es un compilador o un intérprete?**
Mi proyecto cubre el *front-end* de un compilador (léxico, sintáctico y semántico) y además ejecuta el AST directamente, como un intérprete. No genera código máquina ni bytecode. Ese sería el siguiente paso: una fase de generación de código a partir del mismo AST.

**¿Qué diferencia hay entre parámetro y argumento?**
El parámetro es la variable que aparece en la definición (`a: entero` en `funcion suma(a: entero, b: entero)`). El argumento es el valor que se pasa en la llamada (`suma(2, 3)`). El semántico comprueba que coincidan en cantidad y en tipo.

**¿Qué es un ámbito (scope) y cómo lo manejo?**
Es la zona del programa donde una variable existe. En ALEX hay un ámbito global y uno por cada función. La tabla de símbolos guarda cada variable con su ámbito, así que `x` global y `x` local pueden convivir sin chocar. Una función no ve las variables globales; lo que necesita lo recibe por parámetros.

**¿Qué pasa cuando se ejecuta una llamada?**
Primero se calculan los argumentos. Luego se crea un ámbito nuevo con los parámetros ya cargados, se ejecuta el cuerpo, y `retornar` sale de la función con su valor. El valor reemplaza a la llamada dentro de la expresión.

**¿Por qué no permito la recursión?**
Porque ALEX todavía no tiene condicionales. Sin una condición de parada, una función que se llama a sí misma nunca terminaría. Cuando se agregue `si / sino`, bastará con quitar esa regla del semántico.

**¿Cómo sabe el semántico qué tipo devuelve una llamada?**
Busca la función en la tabla de funciones y toma su tipo de retorno. En `absoluto` el retorno depende del argumento: entero si recibe entero y decimal si recibe decimal. Una función sin tipo de retorno no se puede usar dentro de una expresión.

**¿Qué agregaría después?**
Condicionales y ciclos, que serían reglas nuevas en la gramática, nuevos nodos en el AST y nuevos casos en el analizador semántico. Con condicionales también se podrían permitir la recursión y los operadores de comparación (`>`, `<`, `==`).

## Antes de presentar

- [ ] El link de GitHub abre en una ventana de incógnito.
- [ ] `python alex.py ejemplos/ok.alex` y `python alex.py ejemplos/funciones.alex` corren sin errores en la computadora de la presentación.
- [ ] La terminal de VS Code está abierta en la carpeta donde está `alex.py`.
