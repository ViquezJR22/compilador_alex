# ALEX: compilador de mi lenguaje de programación

Proyecto de la materia **Compiladores** (Universidad Adventista de Centro América, Escuela de Ingeniería).
Profesor: William Martinez · Estudiante: Alexis Viquez Terranova

ALEX es un lenguaje con palabras en español, pensado para que el código sea fácil de leer.
Este repositorio contiene el compilador (análisis léxico, sintáctico y semántico) y un intérprete que ejecuta el programa.
El lenguaje tiene variables, expresiones, **condicionales** (`si` / `sino`) y **funciones** (predefinidas y propias).

## Entregables

| Entregable | Dónde está |
|---|---|
| Analizador sintáctico | `class Parser` en `alex.py` |
| Analizador semántico | `class Semantico` en `alex.py` |
| AST Table | `numerar()` y la sección "AST TABLE" de la salida |
| Tabla de símbolos | `class Simbolo` y la sección "TABLA DE SÍMBOLOS" de la salida (con ámbitos y tabla de funciones) |
| Funciones | Parser (`funcion`, `retorno`, `llamada`), Semántico (`funcion`, `retorno`, `llamada`), ejecución (`llamar`) |
| Condicionales | Parser (`si`, `bloque`), Semántico (`si`, `bloque`), ejecución (`exec_stmt`, `ejecutar_bloque`) |

## Requisitos

Python 3.10 o superior. No usa librerías externas.

## Cómo ejecutarlo

```
python alex.py ejemplos/ok.alex
python alex.py ejemplos/funciones.alex
python alex.py ejemplos/condicionales.alex
python alex.py ejemplos/condicionales.alex --tokens
```

Programas de ejemplo con errores, uno por tipo:

```
python alex.py ejemplos/err_lexico.alex
python alex.py ejemplos/err_sintactico.alex
python alex.py ejemplos/err_semantico.alex
python alex.py ejemplos/err_func_sintactico.alex
python alex.py ejemplos/err_func_semantico.alex
python alex.py ejemplos/err_si_sintactico.alex
python alex.py ejemplos/err_si_semantico.alex
```

## Reglas del lenguaje

| Regla | Detalle |
|---|---|
| Declarar | `dato nombre: tipo;` o `dato nombre: tipo = valor;` |
| Asignar | `nombre = expresion;` (la variable debe estar declarada) |
| Fin de instrucción | Siempre `;` |
| Tipos | `entero`, `decimal`, `texto`, `logico` |
| Valores lógicos | `verdadero` y `falso` |
| Nombres | Empiezan con letra o `_`; distinguen mayúsculas; no se repiten en el mismo ámbito |
| Palabras reservadas | dato, funcion, retornar, si, sino, entero, decimal, texto, logico, verdadero, falso |
| Valor por defecto | 0, 0.0, texto vacío y falso |
| Compatibilidad | Un entero cabe en un decimal; un decimal no cabe en un entero |
| Prohibido | Asignaciones encadenadas (`a = b = 3;`) |
| Operadores aritméticos | `+ - * /` y paréntesis; `+` también une textos |
| Comparaciones | `==  !=  <  >  <=  >=`; el resultado siempre es `logico` |
| Comentarios | `// hasta el final de la línea` |

### Comparaciones

| Operador | Qué compara | Ejemplo |
|---|---|---|
| `<  >  <=  >=` | Solo números (entero o decimal, se pueden mezclar) | `edad >= 18` |
| `==  !=` | Dos números, dos textos o dos lógicos | `nombre == "Ana"` |

Una comparación tiene menos prioridad que la suma y la resta: `a + 1 > b * 2` se calcula como `(a + 1) > (b * 2)`.
No se pueden comparar tipos distintos (por ejemplo, un texto con un entero).

### Condicionales

```
si (edad >= 18) {
    mostrar("Es mayor de edad");
} sino si (edad >= 12) {
    mostrar("Es adolescente");
} sino {
    mostrar("Es menor de edad");
}
```

| Regla | Detalle |
|---|---|
| Forma | `si (condicion) { ... }` y, opcionalmente, `sino { ... }` o `sino si (condicion) { ... }` |
| Paréntesis y llaves | Obligatorios: la condición va entre `( )` y cada bloque entre `{ }` |
| Condición | Debe ser de tipo `logico` (normalmente una comparación) |
| Ejecución | Se evalúa la condición; si es verdadera corre el bloque del `si`, si no, el del `sino` (si existe) |
| Ámbito de bloque | Una variable declarada dentro de un bloque solo existe en ese bloque |
| Visibilidad | Un bloque ve las variables de los bloques que lo rodean y puede modificarlas |
| Sombreado | Un bloque puede declarar una variable con el nombre de una externa: la del bloque la tapa solo dentro del bloque |
| Dónde | Se puede usar al nivel principal y dentro de funciones; no se pueden definir funciones dentro de un bloque |

### Funciones propias

```
funcion suma(a: entero, b: entero): entero {
    retornar a + b;
}

funcion saludar(quien: texto) {
    mostrar("Hola,", quien);
}

dato resultado: entero = suma(2, 3);
saludar("Alexis");
```

| Regla | Detalle |
|---|---|
| Definir | `funcion nombre(parametro: tipo, ...): tipo { ... }`; el tipo de retorno es opcional |
| Retornar | `retornar valor;` termina la función y devuelve el valor; sin tipo de retorno no devuelve nada |
| Dónde | Solo al nivel principal; no se puede definir una función dentro de otra ni dentro de un bloque |
| Orden | Una función se define antes de llamarla |
| Llamar | `nombre(argumentos)`, como instrucción (`saludar("x");`) o dentro de una expresión (`suma(2, 3) * 2`) |
| Argumentos | Deben coincidir en cantidad y tipo con los parámetros (un entero sirve para un parámetro decimal) |
| Ámbito | Cada función tiene su propio ámbito: ve sus parámetros y sus variables locales, pero no las globales |
| Obligatorio | Si declara un tipo, debe tener `retornar` en todos sus caminos (por ejemplo, en el `si` y en el `sino`) y su valor debe ser de ese tipo |
| Prohibido | Código después de un `retornar` que siempre se ejecuta; usar una función sin valor dentro de una expresión |
| Recursión | Una función puede llamarse a sí misma; el `si` sirve de caso base (límite de 200 llamadas anidadas) |

### Funciones predefinidas

| Función | Qué hace | Ejemplo |
|---|---|---|
| `mostrar(valor, ...)` | Imprime uno o más valores separados por espacio | `mostrar("Total:", total);` |
| `longitud(texto)` | Cantidad de caracteres (entero) | `longitud("Alexis")` da 6 |
| `mayusculas(texto)` | Pasa el texto a mayúsculas | `mayusculas("hola")` da HOLA |
| `redondear(numero)` | Entero más cercano (los .5 suben) | `redondear(9.5)` da 10 |
| `absoluto(numero)` | Valor sin signo, del mismo tipo que el argumento | `absoluto(-15)` da 15 |

No se puede definir una función ni una variable con el nombre de una predefinida.

## Gramática

```
programa    ::= { sentencia }
sentencia   ::= declaracion | asignacion | funcion | retorno | si | llamada ";"
declaracion ::= "dato" IDENT ":" TIPO [ "=" expresion ] ";"
asignacion  ::= IDENT "=" expresion ";"
funcion     ::= "funcion" IDENT "(" [ parametros ] ")" [ ":" TIPO ] bloque
parametros  ::= IDENT ":" TIPO { "," IDENT ":" TIPO }
retorno     ::= "retornar" [ expresion ] ";"
si          ::= "si" "(" expresion ")" bloque [ "sino" ( si | bloque ) ]
bloque      ::= "{" { sentencia } "}"
llamada     ::= IDENT "(" [ expresion { "," expresion } ] ")"
expresion   ::= suma { ("==" | "!=" | "<" | ">" | "<=" | ">=") suma }
suma        ::= termino { ("+" | "-") termino }
termino     ::= factor { ("*" | "/") factor }
factor      ::= "-" factor | ENTERO | DECIMAL | TEXTO
              | "verdadero" | "falso" | llamada | IDENT | "(" expresion ")"
```

## Fases del compilador

1. **Léxica:** convierte el texto en tokens.
2. **Sintáctica:** convierte los tokens en el árbol AST (parser descendente recursivo).
3. **Semántica:** llena la tabla de símbolos (por ámbito) y verifica declaraciones, duplicados, tipos, condiciones, argumentos y retornos.
4. **Ejecución:** recorre el AST y calcula el valor final de cada variable; cada llamada a una función y cada bloque crean su propio ámbito.

Si una fase encuentra errores, el compilador se detiene ahí y muestra cada error con su línea y columna.

## Estructura

```
alex.py          compilador e intérprete
ejemplos/        programas de prueba (correctos y con errores)
GUIA.md          guía paso a paso del proyecto
PRESENTACION.md  guion de la presentación y conceptos de clase
```
