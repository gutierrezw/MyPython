from Class_DataFrame import get_yfinance
from Modulos_Mysql import (RepositorioOportunidadesBuySell,  IPerformance,  DiariaCNV, PlanInversion)
from Modulos_Utilitarios import vehiculo_parm, convierte_ticket_crypto, porcentaje
from Modulos_Comunes import crea_dataframe_index
from Modulos_python import *

"""
 fecha:: 2025-11-02
 nota::: modulo para reconstruir  tabla performa diaria y performace para los Fondos Comunes de Invervión FCIes
         1) se crea index de referencia 
         2) se obtiene de booktrading, los símbolos  y Dataframe de  las operaciones 
         3) se actualiza el acumulado porcentual de cada simbolo en performa del stock (P_vehiculo) de acuerdo
            al peso para en momento de la operación.
         4) Eliminar manualmente la tablas performa_inversion
         4) hay que cargar tabla diaria_performa antes de iniciar el paso (5) 
         6) cambiar a False switch diaria para iniciar carga performa_inversion
"""


class FondosInversion:
    def __init__(self):
        self.ClassCNV = DiariaCNV()
        self.Performance = IPerformance()
        self.PlanInversion = PlanInversion()
        self.ROportunidades = RepositorioOportunidadesBuySell()

        self.sesion = self.ClassCNV.select_sesion(
            datetime.now(), accion="select", vehiculo="BBVA.ARS"
        )
        self.account_bbva = self.sesion["idcuenta"]
        self.orden = json.loads(self.sesion["orcartera"])
        self.vehiculo = "BBVA.ARS"

        self.sesion = self.ClassCNV.select_sesion(
            datetime.now(), accion="select", vehiculo="SANT.ARS"
        )
        self.account_sant = self.sesion["idcuenta"]

        fci_positions = self.ROportunidades.select_inversion(
                    tipoin=self.vehiculo, ticket="all"
        )

        self.positions = {}
        for items in fci_positions:
            self.positions.update({items['ticket'] : 
                                  {"conid" : items['conid'],
                                   "useraccount": items['useraccount'],
                                   "vehiculo": items['tipoinv'],
                                   "empresa": items['empresa'],
                                   "costobase": items['costobase'],
                                   "position" : items['position'],
                                    }
                                                            
                                })                                                           
        
        self.parms = vehiculo_parm(vehiculo=self.vehiculo)

def date_minima(book, ix):
    DateMin = datetime(9999, 12, 31, 0, 0, 0)

    for row in book:
        fecha_op = row[ix.index("fechahora")]
        if fecha_op < DateMin:
            DateMin = fecha_op
    return DateMin

def proceso_symbol(symbol, vehiculo, fci, dateInc, book, ix):
    indice, index_ref, rtn_index = crea_dataframe_index(vehiculo=vehiculo, desde=dateInc)

    print(f" symbol: {symbol} - history: {len(book)} - desde: {dateInc} - index: {len(indice)}")
    detalle = fci.PlanInversion.get_yf_CNV(symbol=symbol)

    print(f" detalle: {detalle}")

    # bkey, diaria, ebook = None, [], enumerate(book)
    # eof_book, read = next(ebook, (None, None))
    
    



def proceso_FCI():
    DateMin = datetime(9999, 12, 31, 0, 0, 0)
    fci = FondosInversion()
 
    for symbol, values in fci.positions.items():  

        trader, ix = fci.ROportunidades.select_booktrading(
            accion="select*",
            account=values.get("useraccount"),
            idivisa="ARS",
            symbol=symbol,
        )
        DateMin = min(DateMin, date_minima(book=trader, ix=ix))
        proceso_symbol(symbol=symbol, vehiculo=values.get("vehiculo"), fci=fci, dateInc=DateMin.date(), book=trader, ix=ix) 


if __name__ == "__main__":
    proceso_FCI()

