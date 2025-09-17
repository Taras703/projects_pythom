import hashlib
from urllib.parse import urlencode
from typing import Dict, Optional

def _md5_upper(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest().upper()

def _format_shp_part(shp: Dict[str, str]) -> str:
    if not shp:
        return ""
    sorted_shp = sorted(shp.items())
    return ":".join([f"Shp_{k}={v}" for k, v in sorted_shp])

def build_payment_url(
        merchant_login: str,
        password1: str,
        out_sum: str,
        inv_id: str,
        description: str,
        shp: Optional[Dict[str, str]] = None,
        is_test: bool = True
) -> str:
    if shp is None:
        shp = {}

    signature_base = f"{merchant_login}:{out_sum}:{inv_id}:{password1}"
    if shp:
        sorted_shp = sorted(shp.items())
        shp_params = [f"Shp_{k}={v}" for k, v in sorted_shp]
        signature_base += ":" + ":".join(shp_params)

    signature = _md5_upper(signature_base)

    base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
    params = {
        "MerchantLogin": merchant_login,
        "OutSum": out_sum,
        "InvId": inv_id,
        "Description": description,
        "SignatureValue": signature
    }
    if is_test:
        params["IsTest"] = 1

    for k, v in shp.items():
        params[f"Shp_{k}"] = v

    return f"{base_url}?{urlencode(params)}"

def verify_signature_from_result(out_sum: str, inv_id: str, signature_value: str, password2: str, shp: Optional[Dict[str, str]] = None) -> bool:
    if shp is None:
        shp = {}
    signature_values = [out_sum, inv_id, password2]
    shp_part = _format_shp_part(shp)
    if shp_part:
        signature_values.append(shp_part)
    signature_string = ":".join(signature_values)
    expected_signature = _md5_upper(signature_string)
    return signature_value.upper() == expected_signature
