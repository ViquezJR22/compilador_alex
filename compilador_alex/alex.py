#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALEX - Compilador (front-end) + intérprete
Estudiante: Alexis Viquez Terranova
Materia: Compiladores - UNADECA - Prof. William Martinez

Fases:
  1. Análisis léxico      -> lista de tokens
  2. Análisis sintáctico  -> AST (árbol) + AST Table
  3. Análisis semántico   -> Tabla de Símbolos + verificación de tipos
  4. Ejecución            -> se interpreta el AST y se muestran los valores finales

Uso:
    python alex.py programa.alex
    python alex.py programa.alex --tokens     (muestra también la tabla de tokens)
"""
import sys
import argparse

# ---------------------------------------------------------------------------
# Definición del lenguaje
# ---------------------------------------------------------------------------
TIPOS = {"entero", "decimal", "texto", "logico"}
RESERVADAS = {"dato", "entero", "decimal", "texto", "logico", "verdadero", "falso"}
DIGITOS = "0123456789"
SIMPLES = {
    ":": "DOSPUNTOS", ";": "PUNTOCOMA", "=": "IGUAL",
    "+": "MAS", "-": "MENOS", "*": "POR", "/": "DIV",
    "(": "LPAR", ")": "RPAR",
}


class ErrorAlex(Exception):
    """Error de cualquiera de las fases (léxico, sintáctico, semántico)."""

    def __init__(self, fase, mensaje, linea, col=None):
        super().__init__(mensaje)
        self.fase = fase
        self.mensaje = mensaje
        self.linea = linea
        self.col = col


class ErrorEjecucion(Exception):
    pass


# ---------------------------------------------------------------------------
# 1. ANALIZADOR LÉXICO
# ---------------------------------------------------------------------------
class Token:
    def __init__(self, tipo, valor, linea, col, ancho=None):
        self.tipo = tipo
        self.valor = valor
        self.linea = linea
        self.col = col
        self.ancho = ancho if ancho is not None else len(str(valor))


def analizar_lexico(fuente):
    tokens, errores = [], []
    i, n = 0, len(fuente)
    linea, inicio_linea = 1, 0

    def error(msg, col):
        errores.append(ErrorAlex("léxico", msg, linea, col))

    while i < n:
        c = fuente[i]
        col = i - inicio_linea + 1

        if c == "\n":
            linea += 1
            inicio_linea = i + 1
            i += 1
        elif c in " \t\r":
            i += 1
        elif fuente.startswith("//", i):                 # comentario de línea
            while i < n and fuente[i] != "\n":
                i += 1
        elif c.isalpha() or c == "_":                    # identificador o palabra reservada
            j = i
            while j < n and (fuente[j].isalnum() or fuente[j] == "_"):
                j += 1
            lex = fuente[i:j]
            if lex == "dato":
                t = "DATO"
            elif lex in TIPOS:
                t = "TIPO"
            elif lex == "verdadero":
                t = "VERDADERO"
            elif lex == "falso":
                t = "FALSO"
            else:
                t = "IDENT"
            tokens.append(Token(t, lex, linea, col))
            i = j
        elif c in DIGITOS:                               # entero o decimal
            j = i
            while j < n and fuente[j] in DIGITOS:
                j += 1
            if j < n and fuente[j] == ".":
                k = j + 1
                if k < n and fuente[k] in DIGITOS:
                    while k < n and fuente[k] in DIGITOS:
                        k += 1
                    tokens.append(Token("DECIMAL", fuente[i:k], linea, col))
                    i = k
                else:
                    error(f"Número decimal mal formado «{fuente[i:j + 1]}»: "
                          "después del punto deben ir dígitos", col)
                    i = j + 1
            else:
                tokens.append(Token("ENTERO", fuente[i:j], linea, col))
                i = j
        elif c == '"':                                   # texto entre comillas dobles
            j = i + 1
            while j < n and fuente[j] not in '"\n':
                j += 1
            if j >= n or fuente[j] == "\n":
                error("Texto sin cerrar: falta la comilla doble de cierre", col)
                i = j
            else:
                tokens.append(Token("TEXTO", fuente[i + 1:j], linea, col, ancho=j - i + 1))
                i = j + 1
        elif c in SIMPLES:
            tokens.append(Token(SIMPLES[c], c, linea, col))
            i += 1
        else:
            error(f"Carácter no válido en ALEX: «{c}»", col)
            i += 1

    tokens.append(Token("EOF", "", linea, i - inicio_linea + 1, ancho=0))
    return tokens, errores


# ---------------------------------------------------------------------------
# 2. ANALIZADOR SINTÁCTICO (descendente recursivo) -> AST
#
# Gramática de ALEX:
#   programa    ::= { sentencia } EOF
#   sentencia   ::= declaracion | asignacion
#   declaracion ::= "dato" IDENT ":" TIPO [ "=" expresion ] ";"
#   asignacion  ::= IDENT "=" expresion ";"
#   expresion   ::= termino { ("+" | "-") termino }
#   termino     ::= factor  { ("*" | "/") factor }
#   factor      ::= "-" factor | ENTERO | DECIMAL | TEXTO
#                 | "verdadero" | "falso" | IDENT | "(" expresion ")"
# ---------------------------------------------------------------------------
class Nodo:
    def __init__(self, tipo, valor=None, hijos=None, linea=0):
        self.tipo = tipo
        self.valor = valor
        self.hijos = hijos if hijos is not None else []
        self.linea = linea
        self.tipo_dato = None     # lo llena el analizador semántico
        self.nombre = None        # variable (Declaracion / Asignacion)
        self.tipo_decl = None     # tipo declarado (Declaracion)
        self.id = None            # lo llena la AST Table
        self.padre = None


def simbolo(t):
    if t.tipo == "EOF":
        return "fin del archivo"
    if t.tipo == "TEXTO":
        return f'"{t.valor}"'
    return t.valor


class Parser:
    def __init__(self, tokens):
        self.t = tokens
        self.p = 0
        self.errores = []

    # utilidades
    def actual(self):
        return self.t[self.p]

    def previo(self):
        return self.t[self.p - 1] if self.p > 0 else self.t[0]

    def avanzar(self):
        tok = self.t[self.p]
        if tok.tipo != "EOF":
            self.p += 1
        return tok

    def error(self, msg, tok):
        raise ErrorAlex("sintáctico", msg, tok.linea, tok.col)

    def esperar(self, tipo, msg):
        if self.actual().tipo == tipo:
            return self.avanzar()
        self.error(msg, self.actual())

    def punto_y_coma(self):
        if self.actual().tipo == "PUNTOCOMA":
            return self.avanzar()
        p = self.previo()
        raise ErrorAlex("sintáctico",
                        "Falta «;» al final de la instrucción (toda instrucción termina con punto y coma)",
                        p.linea, p.col + p.ancho)

    def sin_encadenar(self):
        if self.actual().tipo == "IGUAL":
            self.error("No se pueden encadenar asignaciones (a = b = 3; no está permitido en ALEX)",
                       self.actual())

    def sincronizar(self, inicio):
        """Recuperación de errores: salta hasta el siguiente ';' o la siguiente declaración."""
        while self.actual().tipo != "EOF":
            if self.actual().tipo == "PUNTOCOMA":
                self.avanzar()
                return
            if self.actual().tipo == "DATO" and self.p > inicio:
                return
            self.avanzar()

    # reglas
    def programa(self):
        raiz = Nodo("Programa", linea=1)
        while self.actual().tipo != "EOF":
            inicio = self.p
            try:
                raiz.hijos.append(self.sentencia())
            except ErrorAlex as e:
                self.errores.append(e)
                self.sincronizar(inicio)
        return raiz

    def sentencia(self):
        t = self.actual()
        if t.tipo == "DATO":
            return self.declaracion()
        if t.tipo == "IDENT":
            return self.asignacion()
        if t.tipo in ("TIPO", "VERDADERO", "FALSO"):
            self.error(f"«{t.valor}» es una palabra reservada; una instrucción debe empezar "
                       "con «dato» o con el nombre de una variable", t)
        self.error(f"Instrucción inesperada «{simbolo(t)}»: se esperaba «dato» o el nombre de una variable", t)

    def declaracion(self):
        tdato = self.avanzar()
        t = self.actual()
        if t.tipo in ("DATO", "TIPO", "VERDADERO", "FALSO"):
            self.error(f"«{t.valor}» es una palabra reservada y no puede usarse como nombre de variable", t)
        if t.tipo != "IDENT":
            self.error("Después de «dato» se esperaba el nombre de la variable", t)
        nombre = self.avanzar()
        self.esperar("DOSPUNTOS", "Se esperaba «:» después del nombre de la variable")
        tt = self.actual()
        if tt.tipo != "TIPO":
            self.error("Se esperaba un tipo de dato (entero, decimal, texto o logico)", tt)
        tipo = self.avanzar()
        nodo = Nodo("Declaracion", f"{nombre.valor}: {tipo.valor}", linea=tdato.linea)
        nodo.nombre = nombre.valor
        nodo.tipo_decl = tipo.valor
        if self.actual().tipo == "IGUAL":
            self.avanzar()
            nodo.hijos.append(self.expresion())
            self.sin_encadenar()
        self.punto_y_coma()
        return nodo

    def asignacion(self):
        nombre = self.avanzar()
        if self.actual().tipo != "IGUAL":
            self.error(f"Después de «{nombre.valor}» se esperaba «=» (asignación)", self.actual())
        self.avanzar()
        nodo = Nodo("Asignacion", nombre.valor, [self.expresion()], nombre.linea)
        nodo.nombre = nombre.valor
        self.sin_encadenar()
        self.punto_y_coma()
        return nodo

    def expresion(self):
        izq = self.termino()
        while self.actual().tipo in ("MAS", "MENOS"):
            op = self.avanzar()
            izq = Nodo("BinOp", op.valor, [izq, self.termino()], op.linea)
        return izq

    def termino(self):
        izq = self.factor()
        while self.actual().tipo in ("POR", "DIV"):
            op = self.avanzar()
            izq = Nodo("BinOp", op.valor, [izq, self.factor()], op.linea)
        return izq

    def factor(self):
        t = self.actual()
        if t.tipo == "MENOS":
            self.avanzar()
            if self.actual().tipo in ("ENTERO", "DECIMAL"):          # -15, -0.5 son literales
                num = self.avanzar()
                tipo = "LiteralEntero" if num.tipo == "ENTERO" else "LiteralDecimal"
                return Nodo(tipo, "-" + num.valor, linea=t.linea)
            return Nodo("Unario", "-", [self.factor()], t.linea)
        if t.tipo == "ENTERO":
            self.avanzar()
            return Nodo("LiteralEntero", t.valor, linea=t.linea)
        if t.tipo == "DECIMAL":
            self.avanzar()
            return Nodo("LiteralDecimal", t.valor, linea=t.linea)
        if t.tipo == "TEXTO":
            self.avanzar()
            return Nodo("LiteralTexto", t.valor, linea=t.linea)
        if t.tipo in ("VERDADERO", "FALSO"):
            self.avanzar()
            return Nodo("LiteralLogico", t.valor, linea=t.linea)
        if t.tipo == "IDENT":
            self.avanzar()
            return Nodo("Variable", t.valor, linea=t.linea)
        if t.tipo == "LPAR":
            self.avanzar()
            e = self.expresion()
            self.esperar("RPAR", "Falta cerrar el paréntesis «)»")
            return e
        self.error(f"Se esperaba un valor o expresión, pero se encontró «{simbolo(t)}»", t)


# ---------------------------------------------------------------------------
# 3. ANALIZADOR SEMÁNTICO + TABLA DE SÍMBOLOS
# ---------------------------------------------------------------------------
class Simbolo:
    def __init__(self, nombre, tipo, linea):
        self.nombre = nombre
        self.tipo = tipo
        self.linea = linea
        self.con_valor = False
        self.asignaciones = 0
        self.lecturas = 0
        self.valor_inicial = None
        self.valor_final = None


class Semantico:
    def __init__(self):
        self.tabla = {}          # nombre -> Simbolo (la Tabla de Símbolos)
        self.errores = []

    def err(self, msg, linea):
        self.errores.append(ErrorAlex("semántico", msg, linea))

    def analizar(self, raiz):
        for s in raiz.hijos:
            if s.tipo == "Declaracion":
                self.declaracion(s)
            else:
                self.asignacion(s)

    def compatible(self, destino, origen, nombre, linea):
        if destino == origen or (destino == "decimal" and origen == "entero"):
            return
        if destino == "entero" and origen == "decimal":
            self.err(f"No se puede guardar un decimal en «{nombre}», que es de tipo entero", linea)
        else:
            self.err(f"Tipos incompatibles: «{nombre}» es de tipo {destino} y se esperaba "
                     f"un valor {destino}, pero se recibió {origen}", linea)

    def declaracion(self, n):
        te = self.tipo_expr(n.hijos[0]) if n.hijos else None     # primero la expresión
        if n.nombre in self.tabla:
            self.err(f"La variable «{n.nombre}» ya fue declarada en la línea "
                     f"{self.tabla[n.nombre].linea}", n.linea)
        else:
            s = Simbolo(n.nombre, n.tipo_decl, n.linea)
            s.con_valor = bool(n.hijos)
            self.tabla[n.nombre] = s
        n.tipo_dato = n.tipo_decl
        if te:
            self.compatible(n.tipo_decl, te, n.nombre, n.linea)

    def asignacion(self, n):
        te = self.tipo_expr(n.hijos[0])
        s = self.tabla.get(n.nombre)
        if s is None:
            self.err(f"La variable «{n.nombre}» no está declarada (hay que declararla antes con «dato»)", n.linea)
            return
        s.asignaciones += 1
        n.tipo_dato = s.tipo
        if te:
            self.compatible(s.tipo, te, n.nombre, n.linea)

    def tipo_expr(self, n):
        t = self._tipo(n)
        n.tipo_dato = t
        return t

    def _tipo(self, n):
        k = n.tipo
        if k == "LiteralEntero":
            return "entero"
        if k == "LiteralDecimal":
            return "decimal"
        if k == "LiteralTexto":
            return "texto"
        if k == "LiteralLogico":
            return "logico"
        if k == "Variable":
            s = self.tabla.get(n.valor)
            if s is None:
                self.err(f"La variable «{n.valor}» no está declarada", n.linea)
                return None
            s.lecturas += 1
            return s.tipo
        if k == "Unario":
            t = self.tipo_expr(n.hijos[0])
            if t is None:
                return None
            if t in ("entero", "decimal"):
                return t
            self.err(f"El signo «-» solo se aplica a entero o decimal, no a {t}", n.linea)
            return None
        if k == "BinOp":
            ti = self.tipo_expr(n.hijos[0])
            td = self.tipo_expr(n.hijos[1])
            if ti is None or td is None:
                return None
            num = ("entero", "decimal")
            if ti in num and td in num:
                return "entero" if (ti == td == "entero" and n.valor != "/") else "decimal"
            if n.valor == "+" and ti == td == "texto":
                return "texto"                                   # concatenación
            self.err(f"El operador «{n.valor}» no se puede aplicar a {ti} y {td}", n.linea)
            return None


# ---------------------------------------------------------------------------
# 4. EJECUCIÓN (intérprete del AST)
# ---------------------------------------------------------------------------
def defecto(t):
    return {"entero": 0, "decimal": 0.0, "texto": "", "logico": False}[t]


def fmt(v, t):
    if t == "logico":
        return "verdadero" if v else "falso"
    if t == "texto":
        return f'"{v}"'
    if t == "decimal":
        return repr(round(float(v), 10))
    return str(v)


def evaluar(n, env):
    k = n.tipo
    if k == "LiteralEntero":
        return int(n.valor)
    if k == "LiteralDecimal":
        return float(n.valor)
    if k == "LiteralTexto":
        return n.valor
    if k == "LiteralLogico":
        return n.valor == "verdadero"
    if k == "Variable":
        return env[n.valor]
    if k == "Unario":
        return -evaluar(n.hijos[0], env)
    a, b = evaluar(n.hijos[0], env), evaluar(n.hijos[1], env)
    op = n.valor
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if b == 0:
        raise ErrorEjecucion(f"División entre cero (línea {n.linea})")
    return a / b


def ejecutar(raiz, tabla):
    env, traza = {}, []
    for s in raiz.hijos:
        if s.tipo == "Declaracion":
            t = s.tipo_decl
            v = evaluar(s.hijos[0], env) if s.hijos else defecto(t)
            if t == "decimal":
                v = float(v)
            env[s.nombre] = v
            tabla[s.nombre].valor_inicial = fmt(v, t) + ("" if s.hijos else "  (por defecto)")
        else:
            t = tabla[s.nombre].tipo
            v = evaluar(s.hijos[0], env)
            if t == "decimal":
                v = float(v)
            env[s.nombre] = v
        traza.append((s.linea, s.nombre, fmt(v, tabla[s.nombre].tipo)))
    for nombre, v in env.items():
        tabla[nombre].valor_final = fmt(v, tabla[nombre].tipo)
    return env, traza


# ---------------------------------------------------------------------------
# Presentación: AST Table, árbol, Tabla de Símbolos, errores
# ---------------------------------------------------------------------------
def tabla_txt(cab, filas):
    filas = [[str(c) for c in f] for f in filas]
    an = [max([len(cab[i])] + [len(f[i]) for f in filas]) for i in range(len(cab))]
    sep = "+" + "+".join("-" * (a + 2) for a in an) + "+"
    def lin(f):
        return "| " + " | ".join(f[i].ljust(an[i]) for i in range(len(cab))) + " |"
    out = [sep, lin(cab), sep] + [lin(f) for f in filas] + [sep]
    return "\n".join(out)


def numerar(raiz):
    lista = []
    def rec(n, padre):
        n.id = len(lista) + 1
        n.padre = padre.id if padre else None
        lista.append(n)
        for h in n.hijos:
            rec(h, n)
    rec(raiz, None)
    return lista


def valor_txt(n):
    if n.tipo == "LiteralTexto":
        return f'"{n.valor}"'
    return "" if n.valor is None else str(n.valor)


def arbol_txt(n, prefijo="", ultimo=True, es_raiz=True):
    etiqueta = n.tipo
    if n.valor is not None:
        etiqueta += f" [{valor_txt(n)}]"
    if n.tipo_dato and n.tipo != "Declaracion":
        etiqueta += f" : {n.tipo_dato}"
    if es_raiz:
        lineas = [etiqueta]
        nuevo = ""
    else:
        lineas = [prefijo + ("└── " if ultimo else "├── ") + etiqueta]
        nuevo = prefijo + ("    " if ultimo else "│   ")
    for i, h in enumerate(n.hijos):
        lineas += arbol_txt(h, nuevo, i == len(n.hijos) - 1, False).split("\n")
    return "\n".join(lineas)


def titulo(txt):
    print("\n" + "=" * 70)
    print(txt)
    print("=" * 70)


def reportar(errores, lineas):
    for e in sorted(errores, key=lambda e: (e.linea, e.col or 0)):
        ubic = f"línea {e.linea}" + (f", columna {e.col}" if e.col else "")
        print(f"  ✘ Error {e.fase} ({ubic}): {e.mensaje}")
        if 1 <= e.linea <= len(lineas):
            print("      " + lineas[e.linea - 1])
            if e.col:
                print("      " + " " * (e.col - 1) + "^")


def mostrar_simbolos(tabla, con_valores):
    cab = ["Nombre", "Tipo", "Línea decl.", "Asignaciones", "Lecturas"]
    if con_valores:
        cab += ["Valor inicial", "Valor final"]
    filas = []
    for s in tabla.values():
        f = [s.nombre, s.tipo, s.linea, s.asignaciones, s.lecturas]
        if con_valores:
            f += [s.valor_inicial, s.valor_final]
        filas.append(f)
    print(tabla_txt(cab, filas))


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def compilar(fuente, ver_tokens=False):
    lineas = fuente.splitlines()

    titulo("FASE 1: ANÁLISIS LÉXICO")
    tokens, errs = analizar_lexico(fuente)
    if ver_tokens:
        print(tabla_txt(["Línea", "Col", "Token", "Lexema"],
                        [[t.linea, t.col, t.tipo, t.valor] for t in tokens if t.tipo != "EOF"]))
    if errs:
        reportar(errs, lineas)
        print(f"\nCompilación detenida: {len(errs)} error(es) léxico(s).")
        return 1
    print(f"  ✔ {len(tokens) - 1} tokens reconocidos, sin errores léxicos.")

    titulo("FASE 2: ANÁLISIS SINTÁCTICO  (AST)")
    parser = Parser(tokens)
    raiz = parser.programa()
    if parser.errores:
        reportar(parser.errores, lineas)
        print(f"\nCompilación detenida: {len(parser.errores)} error(es) sintáctico(s).")
        return 1
    print("  ✔ La estructura del programa es correcta.\n")

    sem = Semantico()
    sem.analizar(raiz)
    nodos = numerar(raiz)
    print("Árbol sintáctico (AST):")
    print(arbol_txt(raiz))

    titulo("AST TABLE")
    filas = []
    for n in nodos:
        filas.append([n.id, n.tipo, valor_txt(n),
                      n.tipo_dato if n.tipo_dato else "-",
                      n.padre if n.padre else "-",
                      ",".join(str(h.id) for h in n.hijos) or "-",
                      n.linea])
    print(tabla_txt(["ID", "Nodo", "Valor", "Tipo dato", "Padre", "Hijos", "Línea"], filas))

    titulo("FASE 3: ANÁLISIS SEMÁNTICO")
    if sem.errores:
        reportar(sem.errores, lineas)
        print("\nTabla de Símbolos (hasta donde se pudo analizar):")
        mostrar_simbolos(sem.tabla, False)
        print(f"\nCompilación detenida: {len(sem.errores)} error(es) semántico(s).")
        return 1
    print("  ✔ Variables declaradas antes de usarse, sin duplicados y con tipos compatibles.")

    titulo("FASE 4: EJECUCIÓN")
    try:
        env, traza = ejecutar(raiz, sem.tabla)
    except ErrorEjecucion as e:
        print(f"  ✘ Error de ejecución: {e}")
        return 1
    for linea, nombre, valor in traza:
        src = lineas[linea - 1].strip() if linea <= len(lineas) else ""
        print(f"  L{linea:<3} {src:<45} →  {nombre} = {valor}")

    titulo("TABLA DE SÍMBOLOS")
    mostrar_simbolos(sem.tabla, True)
    print()
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Compilador del lenguaje ALEX")
    ap.add_argument("archivo", help="archivo fuente (.alex)")
    ap.add_argument("--tokens", action="store_true", help="mostrar la tabla de tokens")
    args = ap.parse_args()
    with open(args.archivo, encoding="utf-8") as f:
        fuente = f.read()
    sys.exit(compilar(fuente, args.tokens))


if __name__ == "__main__":
    main()
