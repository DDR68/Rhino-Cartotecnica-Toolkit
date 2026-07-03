#! python 2
# -*- coding: utf-8 -*-
# Quota_Selezione.py - v2.0
# Quota ingombro orizzontale e verticale della selezione.
# Novita v2.0: i punti di ancoraggio delle quote non sono piu' gli angoli
# astratti della BoundingBox ma i punti REALI sulle curve che realizzano
# gli estremi (min/max X per la quota orizzontale, min/max Y per la
# verticale). Il valore misurato resta identico; le quote risultano
# agganciate alla geometria (grip e linee di estensione sui punti veri).

import Rhino
import Rhino.Geometry as rg
import Rhino.DocObjects as rd
import Rhino.Input.Custom as ric
import scriptcontext as sc
import System
import math

# ---------------------------------------------------------------- parametri
OFFSET_MM        = 15.0   # distanza della linea di quota dall'ingombro
TEXT_MM          = 10.0   # altezza testo
ARROW_MM         = 8.0    # lunghezza freccia
TEXT_GAP_MM      = 2.0    # distanza testo/linea
EXT_OFFSET_MM    = 2.0    # offset linee di estensione dal punto ancorato
SUPPRESS_EXT     = True   # True = niente linee di estensione (stile attuale);
                          # False = linee di estensione dai punti reali
LAYER_NAME       = "Quote"
STYLE_NAME       = "QuotaSelezione"
FALLBACK_SAMPLES = 200    # campioni di riserva se ExtremeParameters fallisce


def get_or_create_layer(name, r, g, b):
    idx = sc.doc.Layers.FindByFullPath(name, -1)
    if idx < 0:
        layer = rd.Layer()
        layer.Name = name
        layer.Color = System.Drawing.Color.FromArgb(r, g, b)
        idx = sc.doc.Layers.Add(layer)
    return idx


def apply_style_settings(ds, scale):
    """Applica le impostazioni dello stile (usata sia in creazione che
    in aggiornamento, cosi' le modifiche ai parametri hanno effetto
    anche su stili gia' presenti nel documento)."""
    ds.TextHeight = TEXT_MM * scale
    ds.ArrowLength = ARROW_MM * scale
    ds.TextGap = TEXT_GAP_MM * scale
    ds.ExtensionLineOffset = EXT_OFFSET_MM * scale
    ds.ExtensionLineExtension = 0.0
    ds.DimTextLocation = rd.DimensionStyle.TextLocation.InDimLine
    ds.SuppressExtension1 = SUPPRESS_EXT
    ds.SuppressExtension2 = SUPPRESS_EXT
    ds.Suffix = " mm"
    unit_to_mm = Rhino.RhinoMath.UnitScale(
        sc.doc.ModelUnitSystem, Rhino.UnitSystem.Millimeters)
    ds.LengthFactor = unit_to_mm
    ds.LengthResolution = 2


def create_dim_style():
    scale = Rhino.RhinoMath.UnitScale(
        Rhino.UnitSystem.Millimeters, sc.doc.ModelUnitSystem)

    existing = sc.doc.DimStyles.FindName(STYLE_NAME)
    if existing is not None:
        # aggiorna lo stile esistente con i parametri correnti
        idx = existing.Index
        apply_style_settings(existing, scale)
        sc.doc.DimStyles.Modify(existing, idx, True)
        return idx

    idx = sc.doc.DimStyles.Add(STYLE_NAME)
    if idx < 0:
        print("Errore: impossibile creare DimensionStyle")
        return sc.doc.DimStyles.CurrentDimensionStyleIndex

    ds = sc.doc.DimStyles[idx]
    if ds is None:
        return sc.doc.DimStyles.CurrentDimensionStyleIndex

    apply_style_settings(ds, scale)
    sc.doc.DimStyles.Modify(ds, idx, True)
    return idx


def collect_selection():
    sel = list(sc.doc.Objects.GetSelectedObjects(False, False))
    curves = []
    dims = []
    for obj in sel:
        if obj is None:
            continue
        geom = obj.Geometry
        if geom is None:
            continue
        if isinstance(geom, rg.Curve):
            curves.append(obj)
        elif isinstance(geom, rg.LinearDimension):
            dims.append(obj)

    if len(curves) == 0 and len(dims) == 0:
        return None, None
    return curves, dims


def ask_selection():
    go = ric.GetObject()
    go.SetCommandPrompt("Seleziona curve e/o quote")
    go.GeometryFilter = (
        rd.ObjectType.Curve | rd.ObjectType.Annotation
    )
    go.SubObjectSelect = False
    go.GroupSelect = True
    go.EnablePreSelect(False, True)
    go.GetMultiple(1, 0)
    if go.CommandResult() != Rhino.Commands.Result.Success:
        return None, None

    curves = []
    dims = []
    for i in range(go.ObjectCount):
        obj = go.Object(i).Object()
        if obj is None:
            continue
        geom = obj.Geometry
        if geom is None:
            continue
        if isinstance(geom, rg.Curve):
            curves.append(obj)
        elif isinstance(geom, rg.LinearDimension):
            dims.append(obj)

    if len(curves) == 0 and len(dims) == 0:
        return None, None
    return curves, dims


def compute_curves_bbox(curves):
    pts = []
    for obj in curves:
        geom = obj.Geometry
        if geom is None:
            continue
        b = geom.GetBoundingBox(True)
        if b.IsValid:
            pts.append(b.Min)
            pts.append(b.Max)
    if len(pts) == 0:
        return rg.BoundingBox.Empty
    return rg.BoundingBox(pts)


def extreme_points_on_curves(curve_objs, direction):
    """Restituisce i punti REALI sulle curve che realizzano il minimo e
    il massimo lungo 'direction'. Usa endpoint + Curve.ExtremeParameters,
    con campionamento di riserva se necessario.

    Gli endpoint vengono valutati per primi cosi', in caso di pareggio
    (es. lato verticale di un rettangolo tutto alla stessa X), vince
    lo spigolo e non un punto interno del lato."""
    best_min = None
    best_max = None
    vmin = 1.0e300
    vmax = -1.0e300

    for obj in curve_objs:
        crv = obj.Geometry
        if crv is None:
            continue

        candidates = [crv.PointAtStart, crv.PointAtEnd]

        params = None
        try:
            params = crv.ExtremeParameters(direction)
        except Exception:
            params = None

        if params is not None:
            for t in params:
                candidates.append(crv.PointAt(t))
        elif not crv.IsLinear():
            # riserva: campionamento fitto
            dom = crv.Domain
            n = FALLBACK_SAMPLES
            for i in range(n + 1):
                t = dom.ParameterAt(float(i) / float(n))
                candidates.append(crv.PointAt(t))

        for pt in candidates:
            v = pt.X * direction.X + pt.Y * direction.Y + pt.Z * direction.Z
            if v < vmin:
                vmin = v
                best_min = pt
            if v > vmax:
                vmax = v
                best_max = pt

    return best_min, best_max


def add_linear_dim(pt1, pt2, dim_pt, rotation_rad, ds_idx, layer_idx, label):
    """Crea una quota lineare ruotata ancorata a pt1/pt2 (punti reali
    sulle curve). La linea di quota passa per dim_pt."""
    style = sc.doc.DimStyles[ds_idx]
    if style is None:
        print("Errore: DimensionStyle non trovato")
        return False

    plane = rg.Plane.WorldXY
    horizontal = rg.Vector3d.XAxis

    dim = rg.LinearDimension.Create(
        rg.AnnotationType.Rotated,
        style,
        plane,
        horizontal,
        pt1,
        pt2,
        dim_pt,
        rotation_rad
    )

    if dim is None:
        print("Errore: impossibile creare quota %s" % label)
        return False

    attr = rd.ObjectAttributes()
    attr.LayerIndex = layer_idx
    attr.ColorSource = rd.ObjectColorSource.ColorFromLayer

    guid = sc.doc.Objects.AddLinearDimension(dim, attr)
    if guid == System.Guid.Empty:
        print("Errore: impossibile aggiungere quota %s al documento" % label)
        return False
    return True


def main():
    # 1. Verifica selezione attiva, altrimenti chiedi
    curves, dims = collect_selection()
    if curves is None:
        print("Nessuna selezione attiva, seleziona curve e/o quote...")
        curves, dims = ask_selection()
        if curves is None:
            print("Nessun oggetto valido selezionato.")
            return

    if len(curves) == 0:
        print("Nessuna curva nella selezione, impossibile quotare.")
        return

    print("Curve selezionate: %d" % len(curves))
    if dims is not None and len(dims) > 0:
        print("Quote selezionate: %d" % len(dims))

    # 2. BoundingBox (serve solo per posizionare le linee di quota)
    bbox = compute_curves_bbox(curves)
    if not bbox.IsValid:
        print("Errore: BoundingBox non valida.")
        return

    # 3. Punti reali di ancoraggio sulle curve
    pt_xmin, pt_xmax = extreme_points_on_curves(curves, rg.Vector3d.XAxis)
    pt_ymin, pt_ymax = extreme_points_on_curves(curves, rg.Vector3d.YAxis)

    if pt_xmin is None or pt_ymin is None:
        print("Errore: impossibile determinare i punti estremi sulle curve.")
        return

    print("Ancoraggio X: (%.3f, %.3f) -> (%.3f, %.3f)" %
          (pt_xmin.X, pt_xmin.Y, pt_xmax.X, pt_xmax.Y))
    print("Ancoraggio Y: (%.3f, %.3f) -> (%.3f, %.3f)" %
          (pt_ymin.X, pt_ymin.Y, pt_ymax.X, pt_ymax.Y))

    # 4. Layer, stile, offset
    layer_idx = get_or_create_layer(LAYER_NAME, 105, 105, 105)
    ds_idx = create_dim_style()

    scale = Rhino.RhinoMath.UnitScale(
        Rhino.UnitSystem.Millimeters, sc.doc.ModelUnitSystem)
    offset = OFFSET_MM * scale

    # 5. Quota orizzontale (sotto): ancorata ai punti reali di min/max X
    dim_pt_h = rg.Point3d(
        (bbox.Min.X + bbox.Max.X) * 0.5,
        bbox.Min.Y - offset,
        0
    )
    ok_h = add_linear_dim(pt_xmin, pt_xmax, dim_pt_h, 0.0,
                          ds_idx, layer_idx, "orizzontale")
    if ok_h:
        print("Quota orizzontale creata (ancorata alle curve).")

    # 6. Quota verticale (a destra): ancorata ai punti reali di min/max Y
    dim_pt_v = rg.Point3d(
        bbox.Max.X + offset,
        (bbox.Min.Y + bbox.Max.Y) * 0.5,
        0
    )
    ok_v = add_linear_dim(pt_ymin, pt_ymax, dim_pt_v, math.pi / 2.0,
                          ds_idx, layer_idx, "verticale")
    if ok_v:
        print("Quota verticale creata (ancorata alle curve).")

    sc.doc.Views.Redraw()

    if ok_h and ok_v:
        print("Quote create con successo.")
    else:
        print("Attenzione: alcune quote non sono state create.")


if __name__ == "__main__":
    main()
