#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALEX - Compilador (front-end) + intérprete
Estudiante: Alexis Viquez Terranova
Materia: Compiladores - UNADECA - Prof. William Martinez

Fases:
  1. Análisis léxico      -> lista de tokens
  2. Análisis sintáctico  -> AST (árbol) + AST Table
  3. Análisis semántico   -> Tabla de Símbolos (con ámbitos) + verificación de tipos
  4. Ejecución            -> se interpreta el AST y se muestran los valores finales

El lenguaje tiene variables, expresiones, condicionales y funciones:
  - funciones predefinidas: mostrar, longitud, mayusculas, redondear, absoluto
  - funciones propias:      funcion nombre(p: tipo, ...): tipo { ... retornar valor; }
  - condicionales:          si (condicion) { ... } sino { ... }   (con == != < > <= >=)

Uso:
    python alex.py programa.alex
    python alex.py programa.alex --tokens     (muestra también la tabla de tokens)
"""
import sys
import math
import argparse

# ---------------------------------------------------------------------------
# Definición del lenguaje
# ---------------------------------------------------------------------------
TIPOS = {"entero", "decimal", "texto", "logico"}
RESERVADAS = {"dato", "funcion", "retornar", "si", "sino",
              "entero", "decimal", "texto", "logico", "verdadero", "falso"}
TOK_RESERVADOS = ("DATO", "FUNCION", "RETORNAR", "SI", "SINO", "TIPO", "VERDADERO", "FALSO")
DIGITOS = "0123456789"
SIMPLES = {
    ":": "DOSPUNTOS", ";": "PUNTOCOMA", "=": "IGUAL",
    "+": "MAS", "-": "MENOS", "*": "POR", "/": "DIV",
    "(": "LPAR", ")": "RPAR", "{": "LLAVEIZQ", "}": "LLAVEDER", ",": "COMA",
    "<": "MENOR", ">": "MAYOR",
}
# Operadores de comparación de dos caracteres
DOBLES = {"==": "IGUALIGUAL", "!=": "DIFERENTE", "<=": "MENORIGUAL", ">=": "MAYORIGUAL"}
COMPARADORES = ("IGUALIGUAL", "DIFERENTE", "MENOR", "MAYOR", "MENORIGUAL", "MAYORIGUAL")

# Funciones predefinidas de ALEX.
#   params: lista de (nombre, tipo)   tipo None = cualquier valor
#                                     tipo "numerico" = entero o decimal
#   ret:    tipo que devuelve         None = no devuelve valor
#                                     "=arg" = el mismo tipo que su argumento
#   variadica: acepta más argumentos del último tipo
PREDEFINIDAS = {
    "mostrar":    {"params": [("valor", None)],        "ret": None, "variadica": True},
    "longitud":   {"params": [("texto", "texto")],     "ret": "entero"},
    "mayusculas": {"params": [("texto", "texto")],     "ret": "texto"},
    "redondear":  {"params": [("numero", "decimal")],  "ret": "entero"},
    "absoluto":   {"params": [("numero", "numerico")], "ret": "=arg"},
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
            elif lex == "funcion":
                t = "FUNCION"
            elif lex == "retornar":
                t = "RETORNAR"
            elif lex == "si":
                t = "SI"
            elif lex == "sino":
                t = "SINO"
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
        elif fuente.startswith(("==", "!=", "<=", ">="), i):
            op = fuente[i:i + 2]
            tokens.append(Token(DOBLES[op], op, linea, col))
            i += 2
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
#   sentencia   ::= declaracion | asignacion | funcion | retorno | si | llamada ";"
#   declaracion ::= "dato" IDENT ":" TIPO [ "=" expresion ] ";"
#   asignacion  ::= IDENT "=" expresion ";"
#   funcion     ::= "funcion" IDENT "(" [ parametros ] ")" [ ":" TIPO ]
#                   "{" { sentencia } "}"            (solo al nivel principal)
#   parametros  ::= IDENT ":" TIPO { "," IDENT ":" TIPO }
#   retorno     ::= "retornar" [ expresion ] ";"
#   si          ::= "si" "(" expresion ")" bloque [ "sino" ( si | bloque ) ]
#   bloque      ::= "{" { sentencia } "}"
#   llamada     ::= IDENT "(" [ expresion { "," expresion } ] ")"
#   expresion   ::= suma { ("==" | "!=" | "<" | ">" | "<=" | ">=") suma }
#   suma        ::= termino { ("+" | "-") termino }
#   termino     ::= factor  { ("*" | "/") factor }
#   factor      ::= "-" factor | ENTERO | DECIMAL | TEXTO
#                 | "verdadero" | "falso" | llamada | IDENT | "(" expresion ")"
# ---------------------------------------------------------------------------
class Nodo:
    def __init__(self, tipo, valor=None, hijos=None, linea=0):
        self.tipo = tipo
        self.valor = valor
        self.hijos = hijos if hijos is not None else []
        self.linea = linea
        self.tipo_dato = None     # lo llena el analizador semántico
        self.nombre = None        # variable, función o parámetro
        self.tipo_decl = None     # tipo declarado (Declaracion, Parametro)
        self.tipo_ret = None      # tipo que devuelve (Funcion)
        self.params = []          # nodos Parametro (Funcion)
        self.cuerpo = []          # sentencias del cuerpo (Funcion)
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

    def saltar_bloque(self):
        """Salta un bloque { ... } completo (con llaves anidadas)."""
        profundidad = 0
        while self.actual().tipo != "EOF":
            t = self.avanzar().tipo
            if t == "LLAVEIZQ":
                profundidad += 1
            elif t == "LLAVEDER":
                profundidad -= 1
                if profundidad == 0:
                    return

    def sincronizar(self, inicio):
        """Recuperación de errores (modo pánico): salta hasta un punto seguro para seguir
        revisando el resto del programa y poder reportar más de un error."""
        while self.actual().tipo != "EOF":
            t = self.actual().tipo
            if t == "PUNTOCOMA":
                self.avanzar()
                return
            if t in ("DATO", "FUNCION", "RETORNAR", "SI") and self.p > inicio:
                return
            if t == "LLAVEDER":
                if self.p == inicio:
                    self.avanzar()          # llave de cierre suelta: se descarta
                return
            if t == "LLAVEIZQ":
                self.saltar_bloque()
                return
            self.avanzar()

    # reglas
    def programa(self):
        raiz = Nodo("Programa", linea=1)
        while self.actual().tipo != "EOF":
            inicio = self.p
            try:
                raiz.hijos.append(self.sentencia(dentro=False))
            except ErrorAlex as e:
                self.errores.append(e)
                self.sincronizar(inicio)
        return raiz

    def sentencia(self, dentro):
        t = self.actual()
        if t.tipo == "DATO":
            return self.declaracion()
        if t.tipo == "SI":
            return self.si()
        if t.tipo == "SINO":
            self.error("«sino» solo puede ir justo después del bloque de un «si»", t)
        if t.tipo == "FUNCION":
            return self.funcion(dentro)
        if t.tipo == "RETORNAR":
            return self.retorno()
        if t.tipo == "IDENT":
            if self.t[self.p + 1].tipo == "LPAR":
                n = self.llamada()
                self.punto_y_coma()
                return n
            return self.asignacion()
        if t.tipo in ("TIPO", "VERDADERO", "FALSO"):
            self.error(f"«{t.valor}» es una palabra reservada; una instrucción debe empezar con "
                       "«dato», «si», «funcion», «retornar» o el nombre de una variable o función", t)
        self.error(f"Instrucción inesperada «{simbolo(t)}»: se esperaba «dato», «si», «funcion», "
                   "«retornar» o el nombre de una variable o función", t)

    def declaracion(self):
        tdato = self.avanzar()
        t = self.actual()
        if t.tipo in TOK_RESERVADOS:
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

    def funcion(self, dentro):
        tf = self.actual()
        if dentro:
            self.error("No se pueden definir funciones dentro de otra función ni dentro de un bloque "
                       "(en ALEX las funciones se definen al nivel principal)", tf)
        self.avanzar()
        t = self.actual()
        if t.tipo in TOK_RESERVADOS:
            self.error(f"«{t.valor}» es una palabra reservada y no puede usarse como nombre de función", t)
        if t.tipo != "IDENT":
            self.error("Después de «funcion» se esperaba el nombre de la función", t)
        nombre = self.avanzar()
        self.esperar("LPAR", f"Se esperaba «(» después del nombre de la función «{nombre.valor}»")
        params = []
        if self.actual().tipo != "RPAR":
            while True:
                params.append(self.parametro())
                if self.actual().tipo == "COMA":
                    self.avanzar()
                    continue
                break
        self.esperar("RPAR", "Falta cerrar el paréntesis «)» de los parámetros")
        tipo_ret = None
        if self.actual().tipo == "DOSPUNTOS":
            self.avanzar()
            tt = self.actual()
            if tt.tipo != "TIPO":
                self.error("Se esperaba el tipo que devuelve la función (entero, decimal, texto o logico)", tt)
            tipo_ret = self.avanzar().valor
        cuerpo = self.bloque(f"el cuerpo de la función «{nombre.valor}»")
        firma = f"{nombre.valor}({', '.join(p.valor for p in params)})"
        nodo = Nodo("Funcion", firma, params + cuerpo, tf.linea)
        nodo.nombre = nombre.valor
        nodo.params = params
        nodo.cuerpo = cuerpo
        nodo.tipo_ret = tipo_ret
        return nodo

    def bloque(self, que):
        """{ sentencia* }  -> lista de sentencias. «que» describe el bloque para los mensajes."""
        t = self.actual()
        if t.tipo != "LLAVEIZQ":
            self.error(f"Se esperaba «{{» para abrir {que}", t)
        llave = self.avanzar()
        sentencias = []
        while self.actual().tipo not in ("LLAVEDER", "EOF"):
            inicio = self.p
            try:
                sentencias.append(self.sentencia(dentro=True))
            except ErrorAlex as e:
                self.errores.append(e)
                self.sincronizar(inicio)
        if self.actual().tipo == "EOF":
            raise ErrorAlex("sintáctico",
                            f"Falta «}}» para cerrar {que} (abierto en la línea {llave.linea})",
                            llave.linea, llave.col)
        self.avanzar()
        return sentencias

    def si(self):
        ts = self.avanzar()
        self.esperar("LPAR", "Se esperaba «(» después de «si»: la condición va entre paréntesis")
        cond = self.expresion()
        self.esperar("RPAR", "Falta cerrar el paréntesis «)» de la condición")
        entonces = Nodo("Bloque", "entonces", self.bloque("el bloque del «si»"), ts.linea)
        hijos = [cond, entonces]
        if self.actual().tipo == "SINO":
            tn = self.avanzar()
            if self.actual().tipo == "SI":                  # «sino si»: otro si dentro del sino
                hijos.append(Nodo("Bloque", "sino", [self.si()], tn.linea))
            else:
                hijos.append(Nodo("Bloque", "sino", self.bloque("el bloque del «sino»"), tn.linea))
        return Nodo("Si", None, hijos, ts.linea)

    def parametro(self):
        t = self.actual()
        if t.tipo in TOK_RESERVADOS:
            self.error(f"«{t.valor}» es una palabra reservada y no puede usarse como nombre de parámetro", t)
        if t.tipo != "IDENT":
            self.error("Se esperaba el nombre de un parámetro", t)
        nombre = self.avanzar()
        self.esperar("DOSPUNTOS", f"Se esperaba «:» después del nombre del parámetro «{nombre.valor}»")
        tt = self.actual()
        if tt.tipo != "TIPO":
            self.error("Se esperaba el tipo del parámetro (entero, decimal, texto o logico)", tt)
        tipo = self.avanzar()
        nodo = Nodo("Parametro", f"{nombre.valor}: {tipo.valor}", linea=nombre.linea)
        nodo.nombre = nombre.valor
        nodo.tipo_decl = tipo.valor
        return nodo

    def retorno(self):
        tr = self.avanzar()
        nodo = Nodo("Retorno", linea=tr.linea)
        if self.actual().tipo != "PUNTOCOMA":
            nodo.hijos.append(self.expresion())
            self.sin_encadenar()
        self.punto_y_coma()
        return nodo

    def llamada(self):
        nombre = self.avanzar()
        self.avanzar()                                   # «(»
        args = []
        if self.actual().tipo != "RPAR":
            while True:
                args.append(self.expresion())
                if self.actual().tipo == "COMA":
                    self.avanzar()
                    continue
                break
        if self.actual().tipo != "RPAR":
            self.error(f"Falta cerrar el paréntesis «)» de la llamada a «{nombre.valor}»", self.actual())
        self.avanzar()
        nodo = Nodo("Llamada", nombre.valor, args, nombre.linea)
        nodo.nombre = nombre.valor
        return nodo

    def expresion(self):
        izq = self.suma()
        while self.actual().tipo in COMPARADORES:
            op = self.avanzar()
            izq = Nodo("BinOp", op.valor, [izq, self.suma()], op.linea)
        return izq

    def suma(self):
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
            if self.t[self.p + 1].tipo == "LPAR":
                return self.llamada()
            self.avanzar()
            return Nodo("Variable", t.valor, linea=t.linea)
        if t.tipo == "LPAR":
            self.avanzar()
            e = self.expresion()
            self.esperar("RPAR", "Falta cerrar el paréntesis «)»")
            return e
        self.error(f"Se esperaba un valor o expresión, pero se encontró «{simbolo(t)}»", t)


# ---------------------------------------------------------------------------
# 3. ANALIZADOR SEMÁNTICO + TABLA DE SÍMBOLOS (con ámbitos)
#
# Ámbitos: hay un ámbito «global»; cada función tiene el suyo y cada bloque de
# un «si» o «sino» abre un ámbito anidado. Un bloque ve las variables de los
# bloques que lo rodean. Una función solo ve sus parámetros y sus variables
# locales (no ve las globales).
# ---------------------------------------------------------------------------
class Simbolo:
    def __init__(self, nombre, tipo, linea, ambito="global", clase="variable"):
        self.nombre = nombre
        self.tipo = tipo
        self.linea = linea
        self.ambito = ambito
        self.clase = clase               # variable | parámetro
        self.con_valor = False
        self.asignaciones = 0
        self.lecturas = 0
        self.valor_inicial = None
        self.valor_final = None


class InfoFuncion:
    def __init__(self, nombre, params, ret, linea, predefinida=False, variadica=False):
        self.nombre = nombre
        self.params = params             # lista de (nombre, tipo)
        self.ret = ret                   # tipo que devuelve; None = no devuelve valor
        self.linea = linea
        self.predefinida = predefinida
        self.variadica = variadica
        self.llamadas = 0


def asignable(destino, origen):
    return destino == origen or (destino == "decimal" and origen == "entero")


def acepta(esperado, recibido):
    if esperado is None:
        return True
    if esperado == "numerico":
        return recibido in ("entero", "decimal")
    return asignable(esperado, recibido)


def desc_tipo(t):
    if t == "numerico":
        return "un número (entero o decimal)"
    return f"de tipo {t}"


def plural(n):
    return f"{n} argumento" + ("" if n == 1 else "s")


class Semantico:
    def __init__(self):
        self.pila = [("global", {})]     # ámbitos activos: (etiqueta, {nombre: Simbolo})
        self.globales = self.pila[0][1]
        self.simbolos = []               # todos los símbolos, en orden de declaración
        self.funciones = {}              # funciones definidas por el programador
        self.predef = {}                 # funciones predefinidas (se crean al usarlas)
        self.funcion_actual = None
        self.errores = []

    def err(self, msg, linea):
        self.errores.append(ErrorAlex("semántico", msg, linea))

    def es_funcion(self, nombre):
        return nombre in PREDEFINIDAS or nombre in self.funciones

    def info_predef(self, nombre):
        if nombre not in self.predef:
            d = PREDEFINIDAS[nombre]
            self.predef[nombre] = InfoFuncion(nombre, d["params"], d["ret"], 0,
                                              predefinida=True,
                                              variadica=d.get("variadica", False))
        return self.predef[nombre]

    def buscar(self, nombre):
        """Busca una variable desde el ámbito más interno hacia afuera."""
        for _, tabla in reversed(self.pila):
            if nombre in tabla:
                return tabla[nombre]
        return None

    def msg_no_declarada(self, nombre, asignando):
        msg = f"La variable «{nombre}» no está declarada"
        if self.funcion_actual is not None and nombre in self.globales:
            msg += (" en esta función (una función no ve las variables globales; "
                    "recíbela como parámetro)")
        elif asignando:
            msg += " (hay que declararla antes con «dato»)"
        return msg

    def analizar(self, raiz):
        for s in raiz.hijos:
            self.sentencia(s)

    def sentencia(self, s):
        """Analiza una sentencia. Devuelve True si siempre termina en un «retornar»."""
        k = s.tipo
        if k == "Declaracion":
            self.declaracion(s)
        elif k == "Asignacion":
            self.asignacion(s)
        elif k == "Funcion":
            self.funcion(s)
        elif k == "Retorno":
            self.retorno(s)
            return True
        elif k == "Llamada":
            s.tipo_dato = self.llamada(s, False)
        elif k == "Si":
            return self.si(s)
        return False

    def analizar_sentencias(self, sentencias):
        """Analiza una lista de sentencias. Devuelve True si todos sus caminos retornan."""
        retorna = False
        linea_ret = None
        avisado = False
        for st in sentencias:
            if retorna and not avisado:
                self.err("Código inalcanzable: antes de esta instrucción siempre se ejecuta "
                         f"un «retornar» (línea {linea_ret})", st.linea)
                avisado = True
            if self.sentencia(st) and not retorna:
                retorna = True
                linea_ret = st.linea
        return retorna

    def bloque(self, nodo, etiqueta):
        """Abre un ámbito anidado para un bloque de «si» o «sino»."""
        self.pila.append((f"{self.pila[-1][0]}/{etiqueta}", {}))
        retorna = self.analizar_sentencias(nodo.hijos)
        self.pila.pop()
        return retorna

    def compatible(self, destino, origen, nombre, linea):
        if asignable(destino, origen):
            return
        if destino == "entero" and origen == "decimal":
            self.err(f"No se puede guardar un decimal en «{nombre}», que es de tipo entero", linea)
        else:
            self.err(f"Tipos incompatibles: «{nombre}» es de tipo {destino} y se esperaba "
                     f"un valor {destino}, pero se recibió {origen}", linea)

    def declaracion(self, n):
        te = self.tipo_expr(n.hijos[0]) if n.hijos else None     # primero la expresión
        etiqueta, actual = self.pila[-1]
        if self.es_funcion(n.nombre):
            self.err(f"«{n.nombre}» ya es el nombre de una función y no puede usarse como variable",
                     n.linea)
        elif n.nombre in actual:
            self.err(f"La variable «{n.nombre}» ya fue declarada en la línea "
                     f"{actual[n.nombre].linea}", n.linea)
        else:
            s = Simbolo(n.nombre, n.tipo_decl, n.linea, etiqueta)
            s.con_valor = bool(n.hijos)
            actual[n.nombre] = s
            self.simbolos.append(s)
        n.tipo_dato = n.tipo_decl
        if te:
            self.compatible(n.tipo_decl, te, n.nombre, n.linea)

    def asignacion(self, n):
        te = self.tipo_expr(n.hijos[0])
        s = self.buscar(n.nombre)
        if s is None:
            if self.es_funcion(n.nombre):
                self.err(f"«{n.nombre}» es una función, no una variable: no se le puede asignar un valor",
                         n.linea)
            else:
                self.err(self.msg_no_declarada(n.nombre, True), n.linea)
            return
        s.asignaciones += 1
        n.tipo_dato = s.tipo
        if te:
            self.compatible(s.tipo, te, n.nombre, n.linea)

    def si(self, n):
        tc = self.tipo_expr(n.hijos[0])
        if tc is not None and tc != "logico":
            self.err(f"La condición del «si» debe ser logico, pero es {tc} "
                     "(usa una comparación, por ejemplo «edad >= 18»)", n.linea)
        retorna_si = self.bloque(n.hijos[1], f"si@{n.linea}")
        if len(n.hijos) == 3:
            retorna_sino = self.bloque(n.hijos[2], f"sino@{n.hijos[2].linea}")
            return retorna_si and retorna_sino
        return False

    def funcion(self, n):
        nombre = n.nombre
        info = InfoFuncion(nombre, [(p.nombre, p.tipo_decl) for p in n.params], n.tipo_ret, n.linea)
        valida = True
        if nombre in PREDEFINIDAS:
            self.err(f"«{nombre}» es una función predefinida de ALEX y no se puede redefinir", n.linea)
            valida = False
        elif nombre in self.funciones:
            self.err(f"La función «{nombre}» ya fue definida en la línea "
                     f"{self.funciones[nombre].linea}", n.linea)
            valida = False
        elif nombre in self.globales:
            self.err(f"«{nombre}» ya es el nombre de una variable (línea "
                     f"{self.globales[nombre].linea})", n.linea)
            valida = False
        if valida:
            self.funciones[nombre] = info        # se registra antes del cuerpo (permite recursión)
        n.tipo_dato = n.tipo_ret

        anterior = (self.pila, self.funcion_actual)
        vars_f = {}
        self.pila = [(nombre, vars_f)]           # la función solo ve su propio ámbito
        self.funcion_actual = info
        for p in n.params:                       # parámetros = primeras variables del ámbito
            p.tipo_dato = p.tipo_decl
            if p.nombre in vars_f:
                self.err(f"El parámetro «{p.nombre}» está repetido en la función «{nombre}»", p.linea)
            elif self.es_funcion(p.nombre):
                self.err(f"El parámetro «{p.nombre}» no puede llamarse igual que una función", p.linea)
            else:
                s = Simbolo(p.nombre, p.tipo_decl, p.linea, nombre, "parámetro")
                s.con_valor = True
                vars_f[p.nombre] = s
                self.simbolos.append(s)

        retorna = self.analizar_sentencias(n.cuerpo)
        if n.tipo_ret and not retorna:
            self.err(f"La función «{nombre}» debe devolver un valor {n.tipo_ret}, pero no tiene "
                     "«retornar» en todos sus caminos", n.linea)
        self.pila, self.funcion_actual = anterior

    def retorno(self, n):
        te = self.tipo_expr(n.hijos[0]) if n.hijos else None
        n.tipo_dato = te
        f = self.funcion_actual
        if f is None:
            self.err("«retornar» solo se puede usar dentro de una función", n.linea)
            return
        if n.hijos:
            if f.ret is None:
                self.err(f"La función «{f.nombre}» no declara qué tipo devuelve, así que no puede "
                         "devolver un valor (agrega «: tipo» después de los parámetros)", n.linea)
            elif te and not asignable(f.ret, te):
                if f.ret == "entero" and te == "decimal":
                    self.err(f"La función «{f.nombre}» devuelve entero, pero «retornar» entrega un "
                             "decimal (un decimal no cabe en un entero)", n.linea)
                else:
                    self.err(f"La función «{f.nombre}» devuelve {f.ret}, pero «retornar» "
                             f"entrega {te}", n.linea)
        elif f.ret is not None:
            self.err(f"La función «{f.nombre}» debe devolver un valor {f.ret}: "
                     "falta el valor después de «retornar»", n.linea)

    def llamada(self, n, en_expresion):
        nombre = n.nombre
        tipos = [self.tipo_expr(a) for a in n.hijos]
        predef = nombre in PREDEFINIDAS
        if predef:
            info = self.info_predef(nombre)
        elif nombre in self.funciones:
            info = self.funciones[nombre]
        else:
            if self.buscar(nombre) is not None:
                self.err(f"«{nombre}» es una variable, no una función", n.linea)
            else:
                self.err(f"La función «{nombre}» no está definida "
                         "(hay que definirla antes de llamarla)", n.linea)
            return None
        info.llamadas += 1

        esperados, recibidos = len(info.params), len(n.hijos)
        if info.variadica and recibidos < esperados:
            self.err(f"La función «{nombre}» necesita al menos {plural(esperados)} "
                     f"y se le pasaron {recibidos}", n.linea)
        elif not info.variadica and recibidos != esperados:
            self.err(f"La función «{nombre}» espera {plural(esperados)} "
                     f"y se le pasaron {recibidos}", n.linea)
        else:
            for i, rec in enumerate(tipos):
                ptipo = info.params[min(i, esperados - 1)][1]
                if rec is not None and not acepta(ptipo, rec):
                    self.err(f"El argumento {i + 1} de «{nombre}» debe ser {desc_tipo(ptipo)}, "
                             f"pero se recibió {rec}", n.linea)

        if info.ret is None:
            if en_expresion:
                self.err(f"La función «{nombre}» no devuelve ningún valor: "
                         "no se puede usar dentro de una expresión", n.linea)
            n.tipo_dato = None
            return None
        ret = info.ret
        if ret == "=arg":                        # absoluto: devuelve el tipo de su argumento
            ret = tipos[0] if tipos and tipos[0] in ("entero", "decimal") else None
        n.tipo_dato = ret
        return ret

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
            s = self.buscar(n.valor)
            if s is None:
                if self.es_funcion(n.valor):
                    self.err(f"«{n.valor}» es una función; para usarla escribe «{n.valor}(...)»", n.linea)
                else:
                    self.err(self.msg_no_declarada(n.valor, False), n.linea)
                return None
            s.lecturas += 1
            return s.tipo
        if k == "Llamada":
            return self.llamada(n, True)
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
            op = n.valor
            if op in ("<", ">", "<=", ">="):                     # comparaciones de orden
                if ti in num and td in num:
                    return "logico"
                self.err(f"El operador «{op}» solo compara números (entero o decimal), "
                         f"no {ti} con {td}", n.linea)
                return None
            if op in ("==", "!="):                               # igualdad
                if (ti in num and td in num) or ti == td:
                    return "logico"
                self.err(f"No se puede comparar {ti} con {td} usando «{op}»", n.linea)
                return None
            if ti in num and td in num:
                return "entero" if (ti == td == "entero" and op != "/") else "decimal"
            if op == "+" and ti == td == "texto":
                return "texto"                                   # concatenación
            self.err(f"El operador «{op}» no se puede aplicar a {ti} y {td}", n.linea)
            return None


# ---------------------------------------------------------------------------
# 4. EJECUCIÓN (intérprete del AST)
# ---------------------------------------------------------------------------
MAX_LLAMADAS = 200       # límite de llamadas anidadas (protege de recursión sin caso base)


class _Retorno(Exception):
    """Se lanza al ejecutar «retornar» para salir de la función con su valor."""

    def __init__(self, valor):
        super().__init__()
        self.valor = valor


class Entorno:
    """Variables en tiempo de ejecución. Cada bloque y cada llamada a una función
    crea uno nuevo; un bloque puede ver el entorno que lo rodea (padre)."""

    def __init__(self, padre=None):
        self.vars = {}
        self.padre = padre

    def declarar(self, nombre, valor):
        self.vars[nombre] = valor

    def obtener(self, nombre):
        e = self
        while e is not None:
            if nombre in e.vars:
                return e.vars[nombre]
            e = e.padre

    def asignar(self, nombre, valor):
        e = self
        while e is not None:
            if nombre in e.vars:
                e.vars[nombre] = valor
                return
            e = e.padre


class Contexto:
    def __init__(self):
        self.funciones = {}     # nombre -> nodo Funcion (se registra al ejecutar su definición)
        self.eventos = []       # ["traza", línea, texto] o ["salida", línea, texto]
        self.salida = []        # lo que imprimió «mostrar»
        self.profundidad = 0    # llamadas a funciones que están en curso


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


def fmt_valor(v):
    """Formato de un valor cualquiera para «mostrar» (sin comillas en los textos)."""
    if isinstance(v, bool):
        return "verdadero" if v else "falso"
    if isinstance(v, float):
        return repr(round(v, 10))
    return str(v)


def evaluar(n, env, ctx):
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
        return env.obtener(n.valor)
    if k == "Llamada":
        return llamar(n, env, ctx)
    if k == "Unario":
        return -evaluar(n.hijos[0], env, ctx)
    a, b = evaluar(n.hijos[0], env, ctx), evaluar(n.hijos[1], env, ctx)
    op = n.valor
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        if b == 0:
            raise ErrorEjecucion(f"División entre cero (línea {n.linea})")
        return a / b
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    if op == "<":
        return a < b
    if op == ">":
        return a > b
    if op == "<=":
        return a <= b
    return a >= b                                        # ">="


def llamar_predef(nombre, args, n, ctx):
    if nombre == "mostrar":
        texto = " ".join(fmt_valor(a) for a in args)
        ctx.salida.append(texto)
        ctx.eventos.append(["salida", n.linea, texto])
        return None
    if nombre == "longitud":
        return len(args[0])
    if nombre == "mayusculas":
        return args[0].upper()
    if nombre == "redondear":
        return int(math.floor(args[0] + 0.5))            # los .5 se redondean hacia arriba
    if nombre == "absoluto":
        return abs(args[0])


def llamar(n, env, ctx):
    args = [evaluar(a, env, ctx) for a in n.hijos]       # primero se calculan los argumentos
    if n.nombre in PREDEFINIDAS:
        return llamar_predef(n.nombre, args, n, ctx)
    f = ctx.funciones[n.nombre]
    ctx.profundidad += 1
    if ctx.profundidad > MAX_LLAMADAS:
        raise ErrorEjecucion(f"Recursión demasiado profunda: más de {MAX_LLAMADAS} llamadas "
                             f"anidadas a «{n.nombre}» (línea {n.linea}). ¿Falta el caso base?")
    local = Entorno()                                    # ámbito nuevo: no ve las variables globales
    for p, v in zip(f.params, args):
        local.declarar(p.nombre, float(v) if p.tipo_decl == "decimal" else v)
    valor = None
    try:
        for s in f.cuerpo:
            exec_stmt(s, local, ctx)
    except _Retorno as r:
        valor = r.valor
    finally:
        ctx.profundidad -= 1
    if f.tipo_ret == "decimal" and valor is not None:
        valor = float(valor)
    return valor


def ejecutar_bloque(sentencias, env, ctx):
    local = Entorno(env)                                 # las variables del bloque viven solo aquí
    for s in sentencias:
        exec_stmt(s, local, ctx)


def exec_stmt(s, env, ctx):
    if s.tipo == "Declaracion":
        t = s.tipo_decl
        v = evaluar(s.hijos[0], env, ctx) if s.hijos else defecto(t)
        if t == "decimal":
            v = float(v)
        env.declarar(s.nombre, v)
        return v
    if s.tipo == "Asignacion":
        v = evaluar(s.hijos[0], env, ctx)
        if s.tipo_dato == "decimal":
            v = float(v)
        env.asignar(s.nombre, v)
        return v
    if s.tipo == "Llamada":
        return llamar(s, env, ctx)
    if s.tipo == "Retorno":
        raise _Retorno(evaluar(s.hijos[0], env, ctx) if s.hijos else None)
    if s.tipo == "Si":                                   # devuelve qué rama se ejecutó
        if evaluar(s.hijos[0], env, ctx):
            ejecutar_bloque(s.hijos[1].hijos, env, ctx)
            return "entonces"
        if len(s.hijos) == 3:
            ejecutar_bloque(s.hijos[2].hijos, env, ctx)
            return "sino"
        return None


RAMAS = {
    "entonces": "condición verdadera → se ejecuta el bloque «si»",
    "sino": "condición falsa → se ejecuta el bloque «sino»",
    None: "condición falsa → no se ejecuta ningún bloque",
}


def ejecutar(raiz, sem, ctx):
    env = Entorno()
    glob = sem.globales
    for s in raiz.hijos:
        if s.tipo == "Funcion":
            ctx.funciones[s.nombre] = s
            ctx.eventos.append(["traza", s.linea, f"función «{s.nombre}» definida"])
            continue
        ev = ["traza", s.linea, "✘ interrumpida por un error"]
        ctx.eventos.append(ev)
        v = exec_stmt(s, env, ctx)
        if s.tipo == "Declaracion":
            ev[2] = f"{s.nombre} = {fmt(v, s.tipo_decl)}"
            glob[s.nombre].valor_inicial = fmt(v, s.tipo_decl) + ("" if s.hijos else "  (por defecto)")
        elif s.tipo == "Asignacion":
            ev[2] = f"{s.nombre} = {fmt(v, s.tipo_dato)}"
        elif s.tipo == "Si":
            ev[2] = RAMAS[v]
        else:
            ev[2] = f"llamada a {s.nombre}"
    for nombre, v in env.vars.items():
        glob[nombre].valor_final = fmt(v, glob[nombre].tipo)
    return env


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
    if n.tipo_dato and n.tipo not in ("Declaracion", "Parametro"):
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


def firma_params(info):
    if not info.params:
        return "-"
    partes = []
    for nombre, tipo in info.params:
        t = "cualquiera" if tipo is None else ("número" if tipo == "numerico" else tipo)
        partes.append(f"{nombre}: {t}")
    txt = ", ".join(partes)
    return txt + ", ..." if info.variadica else txt


def mostrar_funciones(sem):
    infos = list(sem.funciones.values()) + [i for i in sem.predef.values() if i.llamadas > 0]
    if not infos:
        return
    filas = []
    for i in infos:
        ret = "-" if i.ret is None else ("(igual al argumento)" if i.ret == "=arg" else i.ret)
        filas.append([i.nombre, "predefinida" if i.predefinida else "propia", firma_params(i), ret,
                      "-" if i.predefinida else i.linea, i.llamadas])
    print("\nTabla de funciones:")
    print(tabla_txt(["Función", "Origen", "Parámetros", "Retorna", "Línea", "Llamadas"], filas))


def mostrar_simbolos(sem, con_valores):
    cab = ["Nombre", "Tipo", "Clase", "Ámbito", "Línea", "Asign.", "Lect."]
    if con_valores:
        cab += ["Valor inicial", "Valor final"]
    filas = []
    for s in sem.simbolos:
        f = [s.nombre, s.tipo, s.clase, s.ambito, s.linea, s.asignaciones, s.lecturas]
        if con_valores:
            f += [s.valor_inicial or "-", s.valor_final or "-"]
        filas.append(f)
    print(tabla_txt(cab, filas))
    mostrar_funciones(sem)


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
        mostrar_simbolos(sem, False)
        print(f"\nCompilación detenida: {len(sem.errores)} error(es) semántico(s).")
        return 1
    print("  ✔ Variables y funciones declaradas antes de usarse, sin duplicados, "
          "con tipos, argumentos, condiciones y retornos correctos.")

    titulo("FASE 4: EJECUCIÓN")
    ctx = Contexto()
    error = None
    try:
        ejecutar(raiz, sem, ctx)
    except ErrorEjecucion as e:
        error = e
    except RecursionError:
        error = ErrorEjecucion("Recursión demasiado profunda (¿falta el caso base?)")
    for tipo, linea, texto in ctx.eventos:
        if tipo == "traza":
            src = lineas[linea - 1].strip() if linea <= len(lineas) else ""
            print(f"  L{linea:<3} {src:<45} →  {texto}")
        else:
            print(f"       ▶ SALIDA: {texto}")
    if error:
        print(f"  ✘ Error de ejecución: {error}")
        return 1

    if ctx.salida:
        titulo("SALIDA DEL PROGRAMA")
        for texto in ctx.salida:
            print("  " + texto)

    titulo("TABLA DE SÍMBOLOS")
    mostrar_simbolos(sem, True)
    print()
    return 0


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.setrecursionlimit(10000)
    ap = argparse.ArgumentParser(description="Compilador del lenguaje ALEX")
    ap.add_argument("archivo", help="archivo fuente (.alex)")
    ap.add_argument("--tokens", action="store_true", help="mostrar la tabla de tokens")
    args = ap.parse_args()
    with open(args.archivo, encoding="utf-8") as f:
        fuente = f.read()
    sys.exit(compilar(fuente, args.tokens))


if __name__ == "__main__":
    main()
