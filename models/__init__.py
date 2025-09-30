from . import model_adoreaboo
from . import model_beelittle
from . import model_zing
from . import model_prathiksham

def get_db_model(db_name: str):
    """
    Returns the Item, Sale, ViewsAtc classes for the given db_name.
    """
    db_map = {
        "adoreaboo": (model_adoreaboo.Item, model_adoreaboo.Sale, model_adoreaboo.ViewsAtc),
        "beelittle": (model_beelittle.Item, model_beelittle.Sale, model_beelittle.ViewsAtc),
        "zing": (model_zing.Item, model_zing.Sale, model_zing.ViewsAtc),
        "prathiksham": (model_prathiksham.Item, model_prathiksham.Sale, model_prathiksham.ViewsAtc),
    }
    if db_name not in db_map:
        raise ValueError(f"No models found for database '{db_name}'")
    return db_map[db_name]