"""Synthetic business profile: fictional Pakistan-based buyer, suppliers, products, agreements and policies.

EVERYTHING HERE IS FICTIONAL. Tax rates and policy rules are synthetic and configurable; they are NOT
Pakistani tax law or current government rates. To add an industry/currency, create another ``Profile``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal as D

from ..schemas import ProductInfo, SupplierAgreement, SupplierInfo

SYNTHETIC_BANNER = "SYNTHETIC DOCUMENT - FICTIONAL DATA FOR SOFTWARE TESTING ONLY"


@dataclass
class SupplierSpec:
    info: SupplierInfo
    code: str                       # short code used in invoice numbers
    inv_format: str                 # invoice number format
    template: str                   # preferred invoice template: A | B | C
    date_style: str                 # strftime format used on this supplier's documents
    price_factor: D                 # relative to product list price
    categories: list[str]
    charges_allowed: list[str] = field(default_factory=list)
    freight_cap: D = D("0")


@dataclass
class AgreementSpec:
    agreement: SupplierAgreement
    price_adj: D = D("1.00")


@dataclass
class Profile:
    name: str
    currency: str
    customer_name: str
    customer_address: str
    customer_tax_id: str
    products: list[ProductInfo]
    suppliers: list[SupplierSpec]
    agreements: list[AgreementSpec]
    tax_rates: dict[str, D]
    unknown_supplier: SupplierInfo
    start: date = date(2025, 1, 6)
    end: date = date(2025, 8, 29)


def _p(code, desc, cat, uom, price, aliases):
    return ProductInfo(product_code=code, description=desc, category=cat, uom=uom, list_price=D(str(price)), aliases=aliases)


PRODUCTS = [
    # Electrical Equipment
    _p("ELE-1001", "Miniature Circuit Breaker 1-Pole 16A", "Electrical Equipment", "PCS", 650, ["MCB 1P 16A", "1 Pole MCB 16 Amp"]),
    _p("ELE-1002", "Miniature Circuit Breaker 2-Pole 32A", "Electrical Equipment", "PCS", 1850, ["MCB 2P 32A", "MCB 2 Pole 32 Amp"]),
    _p("ELE-1003", "Miniature Circuit Breaker 3-Pole 32A", "Electrical Equipment", "PCS", 2650, ["MCB 3P 32A", "MCB 3 Pole 32 Amp"]),
    _p("ELE-1004", "Miniature Circuit Breaker 3-Pole 63A", "Electrical Equipment", "PCS", 3900, ["MCB 3P 63A", "MCB 3 Pole 63 Amp"]),
    _p("ELE-1005", "Residual Current Breaker 2-Pole 40A", "Electrical Equipment", "PCS", 4800, ["RCCB 2P 40A", "RCCB 2 Pole 40 Amp"]),
    _p("ELE-1006", "AC Contactor 3-Pole 25A", "Electrical Equipment", "PCS", 3400, ["Contactor 25A 3P", "3 Pole AC Contactor 25 Amp"]),
    _p("ELE-1007", "AC Contactor 3-Pole 40A", "Electrical Equipment", "PCS", 5200, ["Contactor 40A 3P", "3 Pole AC Contactor 40 Amp"]),
    _p("ELE-1008", "Distribution Board 8-Way", "Electrical Equipment", "PCS", 7800, ["DB 8 Way", "8 Way Distribution Box"]),
    _p("ELE-1009", "Isolator Switch 3-Pole 63A", "Electrical Equipment", "PCS", 4300, ["Isolator 3P 63A", "3 Pole Isolator 63 Amp"]),
    _p("ELE-1010", "Digital Energy Meter Single Phase", "Electrical Equipment", "PCS", 6200, ["1-Phase Digital kWh Meter", "Single Phase Energy Meter Digital"]),
    # Lighting
    _p("LGT-2001", "LED Bulb 9W E27", "Lighting", "PCS", 280, ["LED Lamp 9 Watt E27", "9W E27 LED Bulb"]),
    _p("LGT-2002", "LED Bulb 12W E27", "Lighting", "PCS", 320, ["LED Lamp 12 Watt E27", "12W E27 LED Bulb"]),
    _p("LGT-2003", "LED Tube Light 18W 4ft", "Lighting", "PCS", 590, ["LED Tube 18 Watt 4 Feet", "T8 LED Tube 18W"]),
    _p("LGT-2004", "LED Panel Light 36W 600x600", "Lighting", "PCS", 2650, ["LED Panel 36 Watt 600 x 600", "36W Square LED Panel"]),
    _p("LGT-2005", "LED Flood Light 50W", "Lighting", "PCS", 2400, ["Flood Light LED 50 Watt", "50W LED Floodlight"]),
    _p("LGT-2006", "LED Flood Light 100W", "Lighting", "PCS", 4600, ["Flood Light LED 100 Watt", "100W LED Floodlight"]),
    _p("LGT-2007", "LED Street Light 120W", "Lighting", "PCS", 11500, ["Street Light LED 120 Watt", "120W LED Streetlight"]),
    _p("LGT-2008", "Emergency Rechargeable Light 12W", "Lighting", "PCS", 1900, ["Rechargeable Emergency Lamp 12 Watt", "12W Emergency LED Light"]),
    # Electronic Components
    _p("ELC-3001", "Electrolytic Capacitor 470uF 25V", "Electronic Components", "PCS", 18, ["Capacitor 470uF 25V", "470 uF 25 V Electrolytic Cap"]),
    _p("ELC-3002", "Electrolytic Capacitor 1000uF 50V", "Electronic Components", "PCS", 42, ["Capacitor 1000uF 50V", "1000 uF 50 V Electrolytic Cap"]),
    _p("ELC-3003", "Power Relay 12V 10A", "Electronic Components", "PCS", 210, ["Relay 12 Volt 10 Amp", "12V 10A Relay"]),
    _p("ELC-3004", "Power Relay 24V 16A", "Electronic Components", "PCS", 340, ["Relay 24 Volt 16 Amp", "24V 16A Relay"]),
    _p("ELC-3005", "Microcontroller Development Board 32-bit", "Electronic Components", "PCS", 3800, ["32 bit MCU Dev Board", "32-bit Microcontroller Board"]),
    _p("ELC-3006", "Voltage Regulator IC 7805", "Electronic Components", "PCS", 25, ["7805 Voltage Regulator", "7805 Regulator IC"]),
    _p("ELC-3007", "Step-Down Transformer 12V 2A", "Electronic Components", "PCS", 950, ["Transformer 12 Volt 2 Amp", "12V 2A Step Down Transformer"]),
    _p("ELC-3008", "Switch Mode Power Supply 24V 5A", "Electronic Components", "PCS", 3300, ["SMPS 24V 5A", "24 Volt 5 Amp Power Supply"]),
    _p("ELC-3009", "Glass Fuse 5A 20mm Box of 100", "Electronic Components", "BOX", 650, ["Glass Fuse 5 Amp 20 mm (100 pcs)", "5A 20mm Fuse Box 100"]),
    _p("ELC-3010", "Carbon Film Resistor Kit 600 Pieces", "Electronic Components", "SET", 900, ["Resistor Assortment Kit 600 pcs", "600 pc Resistor Kit"]),
    # Cables
    _p("CAB-4001", "PVC Insulated Cable 1.5mm Single Core 100m Coil", "Cables", "ROLL", 5400, ["PVC Cable 1.5 mm 100 m", "1.5mm Single Core Cable 100m"]),
    _p("CAB-4002", "PVC Insulated Cable 2.5mm Single Core 100m Coil", "Cables", "ROLL", 8600, ["PVC Cable 2.5 mm 100 m", "2.5mm Single Core Cable 100m"]),
    _p("CAB-4003", "PVC Insulated Cable 4mm Single Core 100m Coil", "Cables", "ROLL", 13400, ["PVC Cable 4 mm 100 m", "4mm Single Core Cable 100m"]),
    _p("CAB-4004", "PVC Insulated Cable 6mm Single Core 100m Coil", "Cables", "ROLL", 19500, ["PVC Cable 6 mm 100 m", "6mm Single Core Cable 100m"]),
    _p("CAB-4005", "Flexible Cable 3 Core 1.5mm", "Cables", "MTR", 95, ["Flex Cable 3C 1.5 mm", "3 Core 1.5mm Flexible Wire"]),
    _p("CAB-4006", "Armoured Cable 4 Core 10mm", "Cables", "MTR", 1350, ["SWA Cable 4C 10 mm", "4 Core 10mm Armoured Cable"]),
    _p("CAB-4007", "Coaxial Cable RG6", "Cables", "MTR", 48, ["RG6 Coax Cable", "Coax RG-6"]),
    _p("CAB-4008", "CAT6 Network Cable 305m Box", "Cables", "BOX", 21500, ["Cat 6 LAN Cable 305 m", "CAT6 UTP 305m Box"]),
    # Connectors
    _p("CON-5001", "Copper Cable Lug 16mm", "Connectors", "PCS", 38, ["Cu Lug 16 mm", "16mm Copper Lug"]),
    _p("CON-5002", "Terminal Block 12-Way", "Connectors", "PCS", 180, ["12 Way Terminal Strip", "Terminal Strip 12W"]),
    _p("CON-5003", "Brass Cable Gland PG21", "Connectors", "PCS", 95, ["Cable Gland Brass PG 21", "PG21 Brass Gland"]),
    _p("CON-5004", "Lever Connector 3-Way", "Connectors", "PCS", 70, ["3 Way Lever Connector", "Lever Nut 3W"]),
    _p("CON-5005", "BNC Connector Crimp Type", "Connectors", "PCS", 55, ["BNC Crimp Connector", "Crimp BNC Plug"]),
    _p("CON-5006", "Industrial Plug 3-Pin 13A", "Connectors", "PCS", 130, ["3 Pin Plug 13 Amp Industrial", "13A Industrial 3 Pin Plug"]),
    _p("CON-5007", "Industrial Socket 3-Pole 32A", "Connectors", "PCS", 1250, ["Industrial Socket 32 Amp 3P", "32A 3 Pole Industrial Socket"]),
    _p("CON-5008", "Nylon Cable Tie 200mm Pack of 100", "Connectors", "PKT", 260, ["Cable Ties 200 mm x100", "200mm Nylon Ties Pack 100"]),
    # Industrial Supplies
    _p("IND-6001", "Insulation Tape PVC 20m", "Industrial Supplies", "ROLL", 70, ["PVC Electrical Tape 20 m", "20m Insulation Tape"]),
    _p("IND-6002", "Insulated Safety Gloves 1000V", "Industrial Supplies", "PCS", 2400, ["1000V Insulating Gloves", "Electrician Gloves 1000 Volt"]),
    _p("IND-6003", "Safety Helmet Industrial", "Industrial Supplies", "PCS", 850, ["Industrial Hard Hat", "Hard Hat Safety Helmet"]),
    _p("IND-6004", "Cable Tray Perforated 2m", "Industrial Supplies", "PCS", 3200, ["Perforated Cable Tray 2 m", "2m Perforated Tray"]),
    _p("IND-6005", "PVC Conduit Pipe 20mm 3m", "Industrial Supplies", "PCS", 120, ["Conduit Pipe PVC 20 mm 3 m", "20mm PVC Conduit 3m"]),
    _p("IND-6006", "Soldering Iron 60W", "Industrial Supplies", "PCS", 1200, ["60 Watt Soldering Iron", "Soldering Iron 60 Watt"]),
    _p("IND-6007", "Digital Multimeter Auto-Ranging", "Industrial Supplies", "PCS", 4500, ["Auto Ranging Digital Multimeter", "DMM Auto Range"]),
    _p("IND-6008", "Heat Shrink Sleeve Kit 127 Pieces", "Industrial Supplies", "SET", 1100, ["Heat Shrink Tubing Kit 127 pcs", "127 pc Heat Shrink Kit"]),
]


def _sup(sid, code, name, tax_id, addr, city, terms, aliases, cats, disc_qty, disc_pct, inv_fmt, tmpl, dstyle, factor, charges=(), cap="0"):
    info = SupplierInfo(supplier_id=sid, name=name, tax_id=tax_id, address=addr, city=city, payment_terms=terms,
                        aliases=aliases, categories=cats, volume_discount_min_qty=D(str(disc_qty)), volume_discount_pct=D(str(disc_pct)))
    return SupplierSpec(info=info, code=code, inv_format=inv_fmt, template=tmpl, date_style=dstyle, price_factor=D(str(factor)),
                        categories=cats, charges_allowed=list(charges), freight_cap=D(cap))


SUPPLIERS = [
    _sup("SUP-001", "KET", "Karachi Electro Traders (Pvt) Ltd", "SYN-TAX-0001-1", "Plot 14, Sector 7-A, Korangi Industrial Area", "Karachi", "Net 30",
         ["KET Karachi", "Karachi Electro Traders"], ["Electrical Equipment", "Cables"], 50, 5, "KET/25/{n:04d}", "A", "%d/%m/%Y", "0.97"),
    _sup("SUP-002", "LLI", "Lahore LumenTech Industries", "SYN-TAX-0002-2", "12-B, Quaid Road, Industrial Estate", "Lahore", "Net 45",
         ["LumenTech Lahore", "Lahore Lumentech Inds"], ["Lighting", "Electronic Components"], 100, 5, "LL-INV-{n:04d}", "B", "%d-%b-%Y", "1.02", ["FREIGHT"], "3500"),
    _sup("SUP-003", "ICC", "Indus Components & Circuits (Pvt) Ltd", "SYN-TAX-0003-3", "Unit 9, Tech Park Phase 2", "Karachi", "Net 30",
         ["Indus Components and Circuits", "ICC Karachi"], ["Electronic Components"], 500, 3, "IC2025-{n:05d}", "C", "%Y-%m-%d", "0.95", ["FREIGHT", "PACKING"], "2000"),
    _sup("SUP-004", "SCW", "Sialkot CableWorks Co.", "SYN-TAX-0004-4", "Kutchery Road, Industrial Zone", "Sialkot", "Net 15",
         ["Sialkot Cable Works", "SCW Sialkot"], ["Cables", "Connectors"], 20, 4, "SCW-{n:05d}", "A", "%d %B %Y", "1.00"),
    _sup("SUP-005", "PPS", "Punjab Power Supply Co.", "SYN-TAX-0005-5", "Block C, Small Industries Estate", "Faisalabad", "Net 30",
         ["Punjab Power Supply Company", "PPS Faisalabad"], ["Electrical Equipment", "Industrial Supplies"], 0, 0, "PPS/{n:04d}/25", "B", "%d/%m/%Y", "1.04", ["FREIGHT", "HANDLING"], "5000"),
    _sup("SUP-006", "FIM", "Faisalabad Industrial Mart", "SYN-TAX-0006-6", "Jaranwala Road, Warehouse 3", "Faisalabad", "Net 45",
         ["FIM Faisalabad", "Faisalabad Industrial Mart Pvt Ltd"], ["Industrial Supplies", "Connectors"], 0, 0, "FIM-{n:04d}", "C", "%d-%m-%Y", "0.99"),
    _sup("SUP-007", "QVS", "Quetta Voltage Solutions", "SYN-TAX-0007-7", "Airport Road, Commercial Block 5", "Quetta", "Net 30",
         ["QVS Quetta", "Quetta Voltage Solns"], ["Electrical Equipment", "Lighting"], 0, 0, "QVS{n:05d}", "A", "%d %b %Y", "1.01", ["FREIGHT"], "4000"),
    _sup("SUP-008", "PCH", "Peshawar Circuit House", "SYN-TAX-0008-8", "University Road, Plaza 21", "Peshawar", "Net 15",
         ["Circuit House Peshawar", "PCH Peshawar"], ["Electronic Components", "Connectors"], 0, 0, "PCH-{n:04d}", "B", "%Y/%m/%d", "0.98"),
]


def _ag(aid, sid, f, t, terms, disc_qty, disc_pct, freight, cap, allowed, adj="1.00"):
    ag = SupplierAgreement(agreement_id=aid, supplier_id=sid, effective_from=f, effective_to=t, currency="PKR", payment_terms=terms,
                           volume_discount_min_qty=D(str(disc_qty)), volume_discount_pct=D(str(disc_pct)),
                           freight_policy=freight, freight_cap=D(str(cap)), allowed_charge_types=allowed)
    return AgreementSpec(agreement=ag, price_adj=D(adj))


AGREEMENTS = [
    _ag("AG-001-A", "SUP-001", date(2025, 1, 1), date(2025, 5, 31), "Net 30", 50, 5, "INCLUDED", 0, []),
    _ag("AG-001-B", "SUP-001", date(2025, 6, 1), date(2025, 12, 31), "Net 30", 50, 5, "INCLUDED", 0, [], "1.04"),
    _ag("AG-002", "SUP-002", date(2025, 1, 1), date(2025, 12, 31), "Net 45", 100, 5, "CAPPED", 3500, ["FREIGHT"]),
    _ag("AG-003", "SUP-003", date(2025, 1, 1), date(2025, 12, 31), "Net 30", 500, 3, "CAPPED", 2000, ["FREIGHT", "PACKING"]),
    _ag("AG-004-A", "SUP-004", date(2025, 1, 1), date(2025, 6, 30), "Net 15", 20, 4, "INCLUDED", 0, []),
    _ag("AG-004-B", "SUP-004", date(2025, 7, 1), date(2025, 12, 31), "Net 15", 20, 4, "INCLUDED", 0, [], "1.03"),
    _ag("AG-005", "SUP-005", date(2025, 1, 1), date(2025, 12, 31), "Net 30", 0, 0, "CAPPED", 5000, ["FREIGHT", "HANDLING"]),
    _ag("AG-006", "SUP-006", date(2025, 1, 1), date(2025, 4, 30), "Net 45", 0, 0, "INCLUDED", 0, []),
    _ag("AG-007", "SUP-007", date(2025, 2, 1), date(2025, 12, 31), "Net 30", 0, 0, "CAPPED", 4000, ["FREIGHT"]),
    _ag("AG-008", "SUP-008", date(2025, 1, 1), date(2025, 12, 31), "Net 15", 0, 0, "INCLUDED", 0, []),
]

TAX_RATES = {"Electrical Equipment": D("15"), "Lighting": D("15"), "Electronic Components": D("10"),
             "Cables": D("10"), "Connectors": D("10"), "Industrial Supplies": D("15")}

UNKNOWN_SUPPLIER = SupplierInfo(supplier_id="SUPX-900", name="Gwadar General Traders", tax_id="SYN-TAX-0900-0",
                                address="Port Road, Shop 18", city="Gwadar", payment_terms="Net 15")

ELECTRICAL_PKR = Profile(
    name="electrical_pkr", currency="PKR",
    customer_name="Meridian Power Solutions (Pvt) Ltd",
    customer_address="Office 301, Harbour Business Centre, Karachi",
    customer_tax_id="SYN-TAX-CUST-01",
    products=PRODUCTS, suppliers=SUPPLIERS, agreements=AGREEMENTS, tax_rates=TAX_RATES,
    unknown_supplier=UNKNOWN_SUPPLIER,
)

# ---------------------------------------------------------------------------------------------
# Policies (synthetic). Structured rows feed the deterministic engine AND are rendered into documents for RAG.
# ---------------------------------------------------------------------------------------------
POLICY_DOCS = {
    "POL-001": ("Three-Way Matching Policy", [
        ("1.1", "match_basis", "PO>DC>INVOICE", "Every supplier invoice must be matched to its purchase order and to the goods-received or delivery record before payment is considered."),
        ("1.2", "qty_tolerance", "0", "The invoiced quantity of a product must not exceed the lower of the cumulative ordered quantity and the cumulative received quantity. Quantity tolerance is 0 units unless the purchasing manager approves otherwise."),
        ("1.3", "partial_delivery", "AGGREGATE", "Where goods arrive in several deliveries, received quantities are aggregated across all delivery records for the purchase order before comparison with the invoice."),
        ("1.4", "missing_dc", "REVIEW", "A missing delivery record is not proof of non-delivery. The invoice is routed to manual review so that receiving staff can confirm delivery."),
        ("1.5", "over_delivery", "REVIEW", "Where the received quantity exceeds the ordered quantity, the discrepancy is routed to the purchasing manager; the invoice may only be paid up to the ordered quantity until approved."),
    ]),
    "POL-002": ("Tax Rates and Tax Information Policy (Synthetic)", [
        ("2.1", "tax_rate:Electrical Equipment", "15", "Synthetic policy tax rate for Electrical Equipment is 15 percent. This is a test configuration and not statutory tax law."),
        ("2.2", "tax_rate:Lighting", "15", "Synthetic policy tax rate for Lighting products is 15 percent."),
        ("2.3", "tax_rate:Electronic Components", "10", "Synthetic policy tax rate for Electronic Components is 10 percent."),
        ("2.4", "tax_rate:Cables", "10", "Synthetic policy tax rate for Cables is 10 percent."),
        ("2.5", "tax_rate:Connectors", "10", "Synthetic policy tax rate for Connectors is 10 percent."),
        ("2.6", "tax_rate:Industrial Supplies", "15", "Synthetic policy tax rate for Industrial Supplies is 15 percent."),
        ("2.7", "tax_information", "REQUIRED", "Every invoice must state the tax rate and tax amount for each line. Invoices without tax information are held for manual review."),
        ("2.8", "tax_basis", "NET_AFTER_DISCOUNT", "Tax is calculated on the line amount after discount. Additional charges are not taxable under this synthetic policy."),
    ]),
    "POL-003": ("Additional Charges Policy", [
        ("3.1", "charges_default", "NOT_ALLOWED", "Freight, handling, packing, fuel and other additional charges are payable only if the supplier agreement expressly permits them."),
        ("3.2", "freight_cap", "PER_AGREEMENT", "Where an agreement permits freight, the charge must not exceed the freight cap stated in that agreement."),
        ("3.3", "surcharges", "NOT_ALLOWED", "Fuel, service or miscellaneous surcharges not named in the agreement are unauthorized and are queried with the supplier."),
        ("3.4", "currency", "PKR", "All invoices must be issued in Pakistani Rupees (PKR) unless the agreement states another currency."),
    ]),
    "POL-004": ("Duplicate Invoice and Payment Control Policy", [
        ("4.1", "duplicate_key", "SUPPLIER+INVOICE_NUMBER", "An invoice is an exact duplicate when the supplier and the normalized invoice number match an invoice already processed, regardless of file name or document format."),
        ("4.2", "possible_duplicate", "SUPPLIER+PO+AMOUNT", "An invoice with a different number but the same supplier, purchase order and economic content as an earlier invoice is a possible duplicate and requires review."),
        ("4.3", "payment_authority", "HUMAN", "No automated system may approve, release or reverse a payment. All payment decisions remain with authorised finance staff."),
    ]),
    "POL-005": ("Supplier and Agreement Validity Policy", [
        ("5.1", "approved_suppliers", "MASTER_ONLY", "Invoices may only be accepted from suppliers listed in the approved supplier master. Invoices from unlisted suppliers are routed to procurement for onboarding review."),
        ("5.2", "agreement_validity", "PO_DATE", "The applicable supplier agreement is the one effective on the purchase order date. If no agreement is effective, contract prices cannot be validated and the invoice is held for review."),
        ("5.3", "supplier_details", "MATCH_MASTER", "Supplier tax identification on an invoice must match the supplier master. Differences are queried before payment."),
        ("5.4", "document_dates", "SEQUENCE", "The invoice date should not precede the delivery date of the goods it bills. Inconsistent dates or references are routed to review."),
        ("5.5", "ambiguous_products", "REVIEW", "Where an invoice line cannot be resolved to a single catalogue product, it is routed to manual review."),
    ]),
}
