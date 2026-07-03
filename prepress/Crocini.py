#! python 2
# -*- coding: utf-8 -*-
# Crocini.py - v2.0
# Crea crocini di registro sugli angoli della BoundingBox della selezione.
# Novita v2.0: le linee dei crocini mantengono sempre una distanza minima
# (CLEARANCE_MM) dal tracciato. Il centro del crocino coincide sempre con
# l'angolo della BoundingBox; vengono spostati/accorciati solo i tratti di
# linea in conflitto, dove si verifica la necessita.

import math
import Rhino
import scriptcontext as sc
import System

# ---------------------------------------------------------------- parametri
CLEARANCE_MM   = 5.0    # distanza minima delle linee del crocino dal tracciato
HALF_SIZE_MM   = 10.0   # semi-lunghezza dei bracci del crocino
SAMPLE_STEP_MM = 0.25   # passo di campionamento lungo le linee del crocino
MIN_SEG_MM     = 1.0    # lunghezza minima di un sottosegmento per essere disegnato
PLOT_WEIGHT_MM = 0.5    # larghezza di stampa
LAYER_NAME     = "Crocini"


def get_or_select_objects():
    """Verifica selezione attiva, altrimenti chiede selezione interattiva."""
    selected = list(sc.doc.Objects.GetSelectedObjects(False, False))
    valid = []
    if selected:
        for obj in selected:
            ot = obj.ObjectType
            if (ot == Rhino.DocObjects.ObjectType.Curve or
                    ot == Rhino.DocObjects.ObjectType.Annotation):
                valid.append(obj)
        if valid:
            return valid

    go = Rhino.Input.Custom.GetObject()
    go.SetCommandPrompt("Seleziona curve e quote")
    go.GeometryFilter = (Rhino.DocObjects.ObjectType.Curve |
                         Rhino.DocObjects.ObjectType.Annotation)
    go.SubObjectSelect = False
    go.GroupSelect = True
    go.GetMultiple(1, 0)
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return None

    objs = []
    for i in range(go.ObjectCount):
        robj = go.Object(i).Object()
        if robj is not None:
            objs.append(robj)
    return objs if objs else None


def ensure_layer(name, color):
    """Crea il layer se non esiste, restituisce l'indice."""
    idx = sc.doc.Layers.FindByFullPath(name, -1)
    if idx >= 0:
        return idx
    layer = Rhino.DocObjects.Layer()
    layer.Name = name
    layer.Color = color
    idx = sc.doc.Layers.Add(layer)
    if idx < 0:
        raise Exception("Impossibile creare il layer '%s'" % name)
    return idx


def build_attributes(layer_idx, color, plot_weight_mm):
    """Attributi: colore da oggetto, tipo linea da layer, larghezza stampa da oggetto."""
    attr = Rhino.DocObjects.ObjectAttributes()
    attr.LayerIndex = layer_idx
    attr.ColorSource = Rhino.DocObjects.ObjectColorSource.ColorFromObject
    attr.ObjectColor = color
    attr.LinetypeSource = Rhino.DocObjects.ObjectLinetypeSource.LinetypeFromLayer
    attr.PlotWeightSource = Rhino.DocObjects.ObjectPlotWeightSource.PlotWeightFromObject
    attr.PlotWeight = plot_weight_mm
    return attr


def collect_obstacles(objs):
    """Separa gli ostacoli per il test di distanza:
    curve reali per le curve, BoundingBox per le annotazioni (quote)."""
    curves = []
    boxes = []
    for obj in objs:
        geom = obj.Geometry
        if geom is None:
            continue
        if isinstance(geom, Rhino.Geometry.Curve):
            curves.append(geom)
        else:
            b = geom.GetBoundingBox(True)
            if b.IsValid:
                boxes.append(b)
    return curves, boxes


def min_distance(pt, curves, boxes):
    """Distanza minima del punto da tutte le curve e da tutte le box."""
    dmin = 1.0e300
    for crv in curves:
        rc, t = crv.ClosestPoint(pt)
        if rc:
            d = crv.PointAt(t).DistanceTo(pt)
            if d < dmin:
                dmin = d
    for box in boxes:
        d = box.ClosestPoint(pt).DistanceTo(pt)
        if d < dmin:
            dmin = d
    return dmin


def clipped_segments(center, direction, half, curves, boxes,
                     clearance, step, min_len):
    """Restituisce i sottosegmenti della linea del crocino (lunga 2*half,
    centrata su center, orientata secondo direction) che mantengono una
    distanza >= clearance da tutti gli ostacoli.

    Vengono spostate solo le coordinate degli estremi dei tratti in
    conflitto; i tratti liberi restano identici alla croce originale."""
    total = 2.0 * half
    n = max(2, int(math.ceil(total / step)))

    pts = []
    valid = []
    for i in range(n + 1):
        t = -half + total * i / n
        pt = Rhino.Geometry.Point3d(center.X + direction.X * t,
                                    center.Y + direction.Y * t,
                                    center.Z)
        pts.append(pt)
        valid.append(min_distance(pt, curves, boxes) >= clearance)

    segments = []
    start = None
    for i in range(n + 1):
        if valid[i] and start is None:
            start = i
        closing = (not valid[i]) or (i == n)
        if closing and start is not None:
            end = i if valid[i] else i - 1
            if end > start:
                a = pts[start]
                b = pts[end]
                if a.DistanceTo(b) >= min_len:
                    segments.append(Rhino.Geometry.Line(a, b))
            start = None
    return segments


def add_crosshair(center, half, attr, curves, boxes,
                  clearance, step, min_len):
    """Disegna un crocino centrato su center, ritagliando i tratti che
    violerebbero la distanza minima dal tracciato. Le linee di ogni
    crocino vengono raggruppate. Restituisce il numero di linee create."""
    dir_x = Rhino.Geometry.Vector3d(1.0, 0.0, 0.0)
    dir_y = Rhino.Geometry.Vector3d(0.0, 1.0, 0.0)

    lines = []
    lines.extend(clipped_segments(center, dir_x, half, curves, boxes,
                                  clearance, step, min_len))
    lines.extend(clipped_segments(center, dir_y, half, curves, boxes,
                                  clearance, step, min_len))
    if not lines:
        print("Attenzione: crocino in (%.2f, %.2f) completamente in conflitto, "
              "nessuna linea creata." % (center.X, center.Y))
        return 0

    group_idx = sc.doc.Groups.Add()
    local_attr = attr.Duplicate()
    if group_idx >= 0:
        local_attr.AddToGroup(group_idx)

    added = 0
    for ln in lines:
        if sc.doc.Objects.AddLine(ln, local_attr) != System.Guid.Empty:
            added += 1
    return added


def main():
    objs = get_or_select_objects()
    if not objs:
        print("Nessun oggetto valido selezionato. Operazione annullata.")
        return

    bbox = Rhino.Geometry.BoundingBox.Empty
    for obj in objs:
        geom = obj.Geometry
        if geom is None:
            continue
        b = geom.GetBoundingBox(True)
        if b.IsValid:
            bbox.Union(b)

    if not bbox.IsValid:
        print("BoundingBox non valida. Verificare la selezione.")
        return

    scale = Rhino.RhinoMath.UnitScale(
        Rhino.UnitSystem.Millimeters, sc.doc.ModelUnitSystem)
    half_size = HALF_SIZE_MM * scale
    clearance = CLEARANCE_MM * scale
    step      = SAMPLE_STEP_MM * scale
    min_len   = MIN_SEG_MM * scale

    curves, boxes = collect_obstacles(objs)

    blue = System.Drawing.Color.FromArgb(0, 0, 255)
    layer_idx = ensure_layer(LAYER_NAME, blue)
    attr = build_attributes(layer_idx, blue, PLOT_WEIGHT_MM)

    corners = [
        Rhino.Geometry.Point3d(bbox.Min.X, bbox.Min.Y, bbox.Min.Z),
        Rhino.Geometry.Point3d(bbox.Max.X, bbox.Min.Y, bbox.Min.Z),
        Rhino.Geometry.Point3d(bbox.Max.X, bbox.Max.Y, bbox.Min.Z),
        Rhino.Geometry.Point3d(bbox.Min.X, bbox.Max.Y, bbox.Min.Z),
    ]

    crocini = 0
    linee = 0
    for corner in corners:
        n = add_crosshair(corner, half_size, attr, curves, boxes,
                          clearance, step, min_len)
        if n > 0:
            crocini += 1
            linee += n

    sc.doc.Views.Redraw()
    print("%d crocini creati (%d linee), distanza minima dal tracciato: %.1f mm."
          % (crocini, linee, CLEARANCE_MM))


main()
