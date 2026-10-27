import logging

def import_magellan(params):
    from .Magellan import BarCodeReader
    try:
        return BarCodeReader(params)
    except Exception as e:
        logging.error(str(e))
        return BarCodeReader()

def import_honeywell(params):
    from .Honeywell3320g import BarCodeReader
    try:
        return BarCodeReader(params)
    except Exception as e:
        logging.error(str(e))
        return BarCodeReader()
    


def import_Newland(params):
    from .NewlandFM430 import BarCodeReader
    try:
        return BarCodeReader(params)
    except Exception as e:
        logging.error(str(e))
        return BarCodeReader()
        

 


def get_code_readers():
    code_reader = {
        "Honeywell": {
            "import": import_honeywell
        },
        "Magellan": {
            "import": import_magellan
        },
      
        "Newland": {
            "import": import_Newland
        }
    }
    return code_reader