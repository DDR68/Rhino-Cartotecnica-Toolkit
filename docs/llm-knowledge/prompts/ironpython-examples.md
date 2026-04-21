# IronPython 2.7 — Esempi di sintassi per Rhino 7/8

Riferimento pratico per assistenti AI. Ogni sezione mostra il pattern corretto
e, dove rilevante, l'errore tipico da evitare.

---

## 1. Intestazione e import standard

Ogni script deve iniziare esattamente cosi:

```python
#! python 2
# -*- coding: utf-8 -*-

import Rhino
import scriptcontext as sc
import System
from Rhino.Geometry import Point3d, Vector3d, Line, Arc, Circle, Plane
from Rhino.Geometry import NurbsCurve, PolyCurve, Interval
```

---

## 2. String formatting: DO / DON'T

```python
# SBAGLIATO — f-string (Python 3.6+, non esiste in IronPython 2.7)
msg = f"Trovati {n} oggetti su layer {nome}"

# SBAGLIATO — print con keyword argument
print("Risultato: {}".format(val), end="")

# GIUSTO — .format()
msg = "Trovati {0} oggetti su layer {1}".format(n, nome)

# GIUSTO — operatore %
msg = "Trovati %d oggetti su layer %s" % (n, nome)

# GIUSTO — print come statement
print "Risultato: {0}".format(val)
```

---

## 3. Print: statement, non funzione

```python
# SBAGLIATO — parentesi con virgola crea una tupla
print("Valore:", x)       # stampa ('Valore:', 42)

# GIUSTO
print "Valore: {0}".format(x)

# anche accettabile (parentesi singola senza virgola)
print("Valore: {0}".format(x))
```

---

## 4. Type hints: non esistono

```python
# SBAGLIATO
def crea_box(l: float, p: float, a: float) -> list:
    pass

# GIUSTO
def crea_box(l, p, a):
    pass
```

---

## 5. Selezione interattiva — GetObject completo

```python
go = Rhino.Input.Custom.GetObject()
go.SetCommandPrompt("Seleziona curve")
go.GeometryFilter = Rhino.DocObjects.ObjectType.Curve
go.EnablePreSelect(True, True)
go.DeselectAllBeforePostSelect = False
go.GetMultiple(1, 0)  # min 1, max 0 = illimitato

if go.CommandResult() != Rhino.Commands.Result.Success:
    print "Selezione annullata"
else:
    for i in range(go.ObjectCount):
        objref = go.Object(i)
        crv = objref.Curve()        # coercizione a curva
        if crv is None:
            continue
        rh_obj = objref.Object()     # RhinoObject (per attributi, layer, ecc.)
        guid = rh_obj.Id
        print "Curva {0}: lunghezza {1:.2f}".format(i, crv.GetLength())
```

Note:
- `objref.Curve()` restituisce la geometria coercita a curva
- `objref.Object()` restituisce il RhinoObject (attributi, Id, layer index)
- `objref.Geometry()` restituisce la geometria generica (Brep, Mesh, ecc.)
- Controllare SEMPRE `CommandResult()` prima di accedere agli oggetti

---

## 6. Input numerico — GetNumber

```python
gn = Rhino.Input.Custom.GetNumber()
gn.SetCommandPrompt("Larghezza (cm)")
gn.SetDefaultNumber(10.0)
gn.SetLowerLimit(0.1, False)   # False = limite non stretto
gn.AcceptNothing(True)
gn.Get()

if gn.CommandResult() != Rhino.Commands.Result.Success:
    print "Annullato"
else:
    larghezza = gn.Number()
```

---

## 7. Input punto — GetPoint

```python
gp = Rhino.Input.Custom.GetPoint()
gp.SetCommandPrompt("Punto di inserimento")
gp.Get()

if gp.CommandResult() != Rhino.Commands.Result.Success:
    print "Annullato"
else:
    pt = gp.Point()
    print "Punto: {0:.2f}, {1:.2f}".format(pt.X, pt.Y)
```

---

## 8. Input stringa — GetString

```python
gs = Rhino.Input.Custom.GetString()
gs.SetCommandPrompt("Nome formato")
gs.SetDefaultString("A20")
gs.AcceptNothing(True)
gs.Get()

if gs.CommandResult() != Rhino.Commands.Result.Success:
    print "Annullato"
else:
    nome = gs.StringResult()
```

---

## 9. Creazione layer con verifica esistenza

```python
def get_or_create_layer(nome, r, g, b):
    """Restituisce l'indice del layer, creandolo se non esiste."""
    idx = sc.doc.Layers.FindByFullPath(nome, -1)
    if idx >= 0:
        return idx
    layer = Rhino.DocObjects.Layer()
    layer.Name = nome
    layer.Color = System.Drawing.Color.FromArgb(r, g, b)
    idx = sc.doc.Layers.Add(layer)
    return idx

# Uso:
idx_taglio = get_or_create_layer("Taglio", 0, 0, 0)
idx_cordone = get_or_create_layer("Cordone", 255, 0, 0)
```

---

## 10. Attributi oggetto e assegnazione colore

```python
# Colore da layer (default cartotecnica)
attr = Rhino.DocObjects.ObjectAttributes()
attr.LayerIndex = idx_taglio
attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromLayer
sc.doc.Objects.AddCurve(curva, attr)

# Colore per oggetto (override)
attr2 = Rhino.DocObjects.ObjectAttributes()
attr2.LayerIndex = idx_taglio
attr2.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
attr2.ObjectColor = System.Drawing.Color.FromArgb(0, 0, 255)
sc.doc.Objects.AddCurve(curva, attr2)
```

---

## 11. NurbsCurve non-razionale

Curva semplice da lista di punti, senza pesi:

```python
pts = [Point3d(0, 0, 0), Point3d(5, 3, 0), Point3d(10, 0, 0)]
crv = NurbsCurve.Create(False, 2, pts)   # False=non-periodica, grado 2
if crv:
    sc.doc.Objects.AddCurve(crv, attr)
```

---

## 12. NurbsCurve razionale — Point4d con pesi

MAI usare `ControlPoint()` — non funziona in IronPython 2.7.
Usare SEMPRE `Point4d` in coordinate omogenee: `Point4d(x*w, y*w, z*w, w)`.

```python
from Rhino.Geometry import Point4d

degree = 2
n_pts = 3
order = degree + 1

crv = NurbsCurve(3, True, order, n_pts)
# 3 = dimensione spaziale, True = razionale

# Knot vector clamped
for i in range(crv.Knots.Count):
    crv.Knots[i] = 0.0 if i < degree else 1.0

# Control points con peso
w_mid = 0.866    # cos(30) per arco conico 60 gradi
crv.Points.SetPoint(0, Point4d(0.0,  0.0,  0.0, 1.0))
crv.Points.SetPoint(1, Point4d(5.0 * w_mid, 3.0 * w_mid, 0.0, w_mid))
crv.Points.SetPoint(2, Point4d(10.0, 0.0,  0.0, 1.0))

if crv.IsValid:
    sc.doc.Objects.AddCurve(crv, attr)
```

---

## 13. Arco da centro, raggio e angoli

```python
import math

centro = Point3d(0, 0, 0)
raggio = 5.0
piano = Plane.WorldXY
piano.Origin = centro

cerchio = Circle(piano, raggio)

# Quarto di cerchio, Q1 (0 a 90 gradi, CCW)
arco = Arc(cerchio, Interval(0, math.pi / 2))
crv_arco = arco.ToNurbsCurve()
sc.doc.Objects.AddCurve(crv_arco, attr)

# Semicerchio verso il basso (angoli negativi)
arco_basso = Arc(cerchio, Interval(-math.pi, 0))
```

---

## 14. Linea

```python
linea = Line(Point3d(0, 0, 0), Point3d(10, 0, 0))
crv_linea = linea.ToNurbsCurve()
sc.doc.Objects.AddCurve(crv_linea, attr)

# Oppure direttamente
sc.doc.Objects.AddLine(Point3d(0, 0, 0), Point3d(10, 0, 0), attr)
```

---

## 15. User Text — documento e oggetto

```python
# DOCUMENTO — metadati globali (parametri dimensionali)
sc.doc.Strings.SetString("L", "15.0")
sc.doc.Strings.SetString("P", "10.0")
sc.doc.Strings.SetString("A", "5.0")
sc.doc.Strings.SetString("S", "0.05")

val = sc.doc.Strings.GetValue("L")
if val is not None:
    L = float(val)

# OGGETTO — metadati sulla singola curva
rh_obj = sc.doc.Objects.FindId(guid)
if rh_obj:
    rh_obj.Attributes.SetUserString("Tipo", "Piega")
    rh_obj.Attributes.SetUserString("ID", "1")
    rh_obj.Attributes.SetUserString("Comportamento", "Profondita")
    sc.doc.Objects.ModifyAttributes(rh_obj, rh_obj.Attributes, True)

# Lettura
tipo = rh_obj.Attributes.GetUserString("Tipo")
```

---

## 16. Conversione unita di misura

```python
# Mai assumere l'unita. Convertire sempre.
scala = Rhino.RhinoMath.UnitScale(
    Rhino.UnitSystem.Centimeters,
    sc.doc.ModelUnitSystem
)

# Esempio: 18 mm di patella, convertiti nell'unita del documento
patella_cm = 1.8
patella_doc = patella_cm * scala
```

---

## 17. BoundingBox e validazione geometria

```python
bb = crv.GetBoundingBox(True)
if not bb.IsValid:
    print "BoundingBox non valido"
else:
    dim_x = bb.Max.X - bb.Min.X
    dim_y = bb.Max.Y - bb.Min.Y
    print "Dimensioni: {0:.2f} x {1:.2f}".format(dim_x, dim_y)
```

---

## 18. Redraw e messaggio finale

```python
sc.doc.Views.Redraw()
print "Script completato: {0} curve create".format(n_curve)
```

---

## 19. Template script minimo completo

```python
#! python 2
# -*- coding: utf-8 -*-

import Rhino
import scriptcontext as sc
import System
from Rhino.Geometry import Point3d, Line

def get_or_create_layer(nome, r, g, b):
    idx = sc.doc.Layers.FindByFullPath(nome, -1)
    if idx >= 0:
        return idx
    layer = Rhino.DocObjects.Layer()
    layer.Name = nome
    layer.Color = System.Drawing.Color.FromArgb(r, g, b)
    return sc.doc.Layers.Add(layer)

def main():
    idx_taglio = get_or_create_layer("Taglio", 0, 0, 0)

    attr = Rhino.DocObjects.ObjectAttributes()
    attr.LayerIndex = idx_taglio
    attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromLayer

    pt_a = Point3d(0, 0, 0)
    pt_b = Point3d(10, 0, 0)
    sc.doc.Objects.AddLine(pt_a, pt_b, attr)

    sc.doc.Views.Redraw()
    print "Fatto."

if __name__ == "__main__":
    main()
```
