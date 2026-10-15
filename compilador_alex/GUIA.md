# Compilador de ALEX: guía paso a paso

Estudiante: Alexis Viquez Terranova · Compiladores · Prof. William Martinez

## 0. Cómo correrlo

```
python alex.py ejemplos/ok.alex              # programa correcto: AST, AST Table, símbolos y ejecución
python alex.py ejemplos/ok.alex --tokens     # igual, mostrando también la tabla de tokens
python alex.py ejemplos/err_lexico.alex      # errores léxicos
python alex.py ejemplos/err_sintactico.alex  # errores sintácticos
python alex.py ejemplos/err_semantico.alex   # errores semánticos
python alex.py ejemplos/funciones.alex       # funciones propias y predefinidas
python alex.py ejemplos/err_func_sintactico.alex  # errores sintácticos en funciones
python alex.py ejemplos/err_func_semantico.alex   # errores semánticos en funciones
```

Solo necesita Python 3 (sin librerías externas).

## 1. Las reglas de ALEX (lo que explicas en la evaluación)

| Regla | Detalle |
|---|---|
| Declarar | `dato nombre: tipo;` o `dato nombre: tipo = valor;` |
| Asignar | `nombre = expresion;` (la variable debe existir) |
| Fin de instrucción | Siempre `;` |
| Tipos | `entero` (7, -15), `decimal` (3.14), `texto` ("Hola"), `logico` (verdadero / falso) |
| Nombres | Empiezan con letra o `_`; distinguen mayúsculas; no pueden ser reservadas; no se repiten |
| Reservadas | dato, entero, decimal, texto, logico, verdadero, falso |
| Valor por defecto | 0, 0.0, "" y falso |
| Compatibilidad | entero → decimal sí; decimal → entero no |
| Prohibido | `a = b = 3;` (asignación encadenada) |
| Comentarios | `// hasta el final de la línea` |
| Funciones propias | `funcion nombre(p: tipo, ...): tipo { ... retornar valor; }`; el tipo de retorno es opcional |
| Ámbito | Cada función tiene su propio ámbito: ve sus parámetros y sus variables locales, no las globales |
| Llamadas | `nombre(argumentos)` como instrucción o dentro de una expresión; los argumentos deben coincidir en cantidad y tipo |
| Funciones predefinidas | `mostrar`, `longitud`, `mayusculas`, `redondear`, `absoluto` |
| Prohibido en funciones | Código después de `retornar`, llamarse a sí misma, definir una función dentro de otra |

Operadores `+ - * /` y paréntesis: los incluí porque tus propios ejemplos usan `precio + 2.5` y `edad + 1`. `+` también concatena texto. `entero / entero` da decimal. Si el profesor pide solo lo de la actividad anterior, puedes decir que son una extensión mínima.

## 2. Las 4 fases (y dónde está cada una en `alex.py`)

| Fase | Entregable | Dónde está |
|---|---|---|
| 1. Léxica | Tokens | `analizar_lexico()` |
| 2. Sintáctica | Analizador sintáctico + árbol AST | `class Parser` |
| 2b. | AST Table | `numerar()` + `compilar()` (tabla "AST TABLE") |
| 3. Semántica | Analizador semántico + Tabla de Símbolos | `class Semantico` y `class Simbolo` |
| 4. Ejecución | Correr el código fuente | `ejecutar()` |

### Fase 1: léxico
Lee el texto carácter por carácter y lo convierte en tokens: `DATO`, `TIPO`, `IDENT`, `ENTERO`, `DECIMAL`, `TEXTO`, `VERDADERO`, `FALSO`, `:`, `;`, `=`, `+ - * /`, `( )`. Detecta: carácter no válido (`@`), decimal mal formado (`3.`), texto sin cerrar.

### Fase 2: sintáctico
Descendente recursivo: una función por regla de la gramática.

```
programa    ::= { sentencia }
sentencia   ::= declaracion | asignacion | funcion | retorno | llamada ";"
declaracion ::= "dato" IDENT ":" TIPO [ "=" expresion ] ";"
asignacion  ::= IDENT "=" expresion ";"
funcion     ::= "funcion" IDENT "(" [ parametros ] ")" [ ":" TIPO ] "{" { sentencia } "}"
parametros  ::= IDENT ":" TIPO { "," IDENT ":" TIPO }
retorno     ::= "retornar" [ expresion ] ";"
llamada     ::= IDENT "(" [ expresion { "," expresion } ] ")"
expresion   ::= termino { ("+" | "-") termino }
termino     ::= factor { ("*" | "/") factor }
factor      ::= "-" factor | ENTERO | DECIMAL | TEXTO | "verdadero" | "falso" | llamada | IDENT | "(" expresion ")"
```

La precedencia sale de la gramática: `*` y `/` están un nivel más abajo que `+` y `-`, así que se evalúan primero. Cuando hay un error, el parser lo reporta y salta hasta el siguiente `;` para seguir revisando (por eso puede mostrar varios errores en una corrida).

### AST Table
Cada nodo del árbol se numera (ID), con su tipo de nodo, valor, tipo de dato (lo llena el semántico), padre, hijos y línea. Sale justo después del árbol dibujado.

### Fase 3: semántico y Tabla de Símbolos
Recorre el AST en orden y lleva la tabla de símbolos por ámbito (`global` y uno por función): `nombre → tipo, clase, ámbito, línea, asignaciones, lecturas`. También lleva una tabla de funciones con su firma y cuántas veces se llamó. Verifica:
1. Variable declarada antes de usarse.
2. No declarada dos veces.
3. El valor coincide con el tipo (entero → decimal permitido, decimal → entero no).
4. Operadores válidos para los tipos (no se puede `"a" - "b"`).
5. Funciones: no se redefinen ni se llaman antes de definirlas, y los parámetros no se repiten.
6. Llamadas: la cantidad y el tipo de los argumentos coinciden con los parámetros, y una función sin valor no se usa dentro de una expresión.
7. Retornos: una función con tipo debe tener `retornar` con un valor de ese tipo, no hay código después de `retornar`, y `retornar` solo existe dentro de funciones.
8. Ámbitos: una función no ve las variables globales, y las variables de una función no existen afuera.

Si hay errores semánticos no se ejecuta nada.

### Fase 4: ejecución
Recorre el AST, calcula las expresiones y guarda los valores. Cada llamada a una función crea un ámbito nuevo con sus parámetros; `retornar` sale de la función con su valor. Lo que imprime `mostrar` aparece en la ejecución y en el bloque "SALIDA DEL PROGRAMA". Al final la Tabla de Símbolos muestra valor inicial y valor final de cada variable global. También detecta división entre cero.

## 3. Guion para la evaluación (5 minutos)

1. Mostrar `ok.alex` y explicar las reglas de la sección 1 con 2 o 3 líneas del código.
2. Correr `python alex.py ejemplos/ok.alex --tokens`: señalar los tokens, el árbol, la AST Table, la ejecución y la Tabla de Símbolos.
3. Correr `err_sintactico.alex`: «falta el `;`», «asignación encadenada», «palabra reservada».
4. Correr `err_semantico.alex`: «no declarada», «redeclarada», «decimal en entero».
5. Cerrar con el siguiente paso: agregar condicionales y ciclos, que serían nuevas reglas en el parser y nuevos casos en el semántico.

## 4. Si el profesor pide un cambio en vivo

- Palabra reservada nueva: agregarla a `RESERVADAS` y en `analizar_lexico()`.
- Tipo nuevo: agregarlo a `TIPOS`, a `defecto()` y a `fmt()`.
- Operador nuevo: añadirlo a `SIMPLES`, al parser (`expresion` o `termino`) y a `evaluar()`.
- Función predefinida nueva: agregarla a `PREDEFINIDAS` (parámetros y tipo de retorno) y escribir su comportamiento en `llamar_predef()`.
