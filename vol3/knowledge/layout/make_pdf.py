"""Rebuild nw-500-warranty.pdf (pages 1-2 of the fixture) from HTML. Needs weasyprint.

The committed PDF is what vol3/ch03.py hands to a real parser (AIEV_PARSER=pdfplumber).
"""
from pathlib import Path

from weasyprint import HTML

HERE = Path(__file__).resolve().parent
HTML(string="""<style>@page{size:A5;margin:18mm} body{font:11pt sans-serif}
.cols{columns:2;column-gap:10mm} table{border-collapse:collapse;width:100%}
td,th{border:1px solid #000;padding:3pt} footer{position:fixed;bottom:-10mm;font-size:8pt}
</style>
<footer>Northwind Goods | warranty-nw500</footer>
<h2>NW-500 Warranty Card</h2>
<div class="cols"><p>Keep your receipt. The warranty starts on the delivery date shown on
your order.</p><p>Claims are made by email to the support team with the order number and
a short description.</p></div>
<h2 style="break-before:page">Warranty by region</h2>
<table><tr><th>Region</th><th>Warranty</th><th>Claim by</th></tr>
<tr><td>India</td><td>12 months</td><td>email</td></tr>
<tr><td>EU</td><td>24 months</td><td>email or store</td></tr>
<tr><td>UK</td><td>12 months</td><td>email</td></tr></table>""").write_pdf(HERE / "nw-500-warranty.pdf")
