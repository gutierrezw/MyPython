arelle (el estándar mundial)

La estructura típica de un filing Inline XBRL es:
    ✔ Un HTML grande (tu .htm)
    ✔ Con tags <ix:nonnumeric> y <ix:nonfraction>
    ✔ Con una sección ix:resources y ix:header
    ✔ Con contexts xbrli:context
    ✔ Con facts inline dentro del HTML
    ✔ Y tu snippet concuerda exactamente con eso.



valuation_arelle_parser.py
    ✔ inline XBRL activado correctamente
    ✔ zip con instancia interna
    ✔ extracción de facts, contextos y unidades
    ✔ loader único para todos los formatos
    ✔ cero dependencias raras
    ✔ compatible con tu engine y tu API

valuation_xbrl_api.py
    ✔ Crear un objeto Filing que encapsula:
        facts
        contexts
        units
        modelo Arelle
    ✔ Exponer funciones simples:
        load_filing(path)
        get_fact(name, prefer="duration")
        select_best_fact(facts, prefer)
        build_ttm(filings)
    ✔ Garantizar que el motor de valoración tenga datos limpios:
        NetIncome
        OperatingCF
        CapEx
        Dividends
        Shares
        Revenue
        FFO, AFFO (si existen)