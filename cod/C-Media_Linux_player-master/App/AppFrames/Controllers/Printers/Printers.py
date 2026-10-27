def import_tmt88(params):
    from .TM_T88V import Printer
    return Printer(params)

def import_sat(params):
    from .SAT import Printer
    return Printer(params)

def import_UniversalPrinter(params):
    from .UniversalPrinter import Printer
    return Printer(params)

def get_impresoras():
    impresoras = {
        "TM-T88":{
            "value": 0,
            "import": import_tmt88
        },
        "SAT":{
            "value": 1,
            "import": import_sat
        },
        "UniversalPrinter":{
            "value": 2,
            "import": import_UniversalPrinter
        }
    }
    return impresoras