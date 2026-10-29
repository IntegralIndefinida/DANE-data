"""
dane-data — microdatos del DANE (GEIH y EAM) listos para analizar.

    import dane_data as dd
    dd.set_paths(geih="~/datos/GEIH/data", eam="~/datos/EAM/data", save=True)

    df = dd.geih.load(2025, months=[1, 2, 3])
    dd.geih.indicadores(df, por="sexo")

    eam = dd.eam.load(range(2015, 2025))
    dd.eam.resumen(eam, por=["anio", "division"])
"""

from . import eam, geih
from ._hooks import DownloadCancelled
from .config import get_path, set_paths, show_paths
from .referencias import DEPARTAMENTOS, MESES, SMLV, buscar_variable, describir, diccionario
from .stats import tabla, weighted_mean, weighted_quantile

__version__ = "0.3.2"

__all__ = [
    "geih", "eam", "set_paths", "get_path", "show_paths", "tabla", "weighted_mean",
    "weighted_quantile", "buscar_variable", "describir", "diccionario", "SMLV",
    "DEPARTAMENTOS", "MESES", "DownloadCancelled",
]
