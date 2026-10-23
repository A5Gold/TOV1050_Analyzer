import pytest
from openpyxl import load_workbook
import pandas as pd
from app.core.exporter import ExcelExporter
from app.core.tov1050_report_export import export_tov1050_report,export_analysis_report


def test_streaming_report_preserves_every_sheet_cell_order_and_metadata():
    result={"Wire Wear":pd.DataFrame([{"id":"ID0","FromM":98150.2,"ToM":98151,"maxValue":9.1,"level":"L1","Tension Length":"A, B"}]),
            "Low Height":pd.DataFrame()}
    frame=pd.DataFrame({"Chainage":[98150.2,98150.3,98150.3,98150.4],"height1":[4400,None,4550,4600],
                        "wear1":[9.1,10.2,float('nan'),11],"stagger1":[-350,0,500,500],
                        "line":["ISL"]*4,"Overlap":[None,"Y",None,None],"source_row_number":[102,103,104,105]})
    metadata={"enrichment_version":"tov640-first-nonempty-v1","metadata_capabilities":"unknown"}
    legacy=load_workbook(ExcelExporter.export_report(result,frame,metadata),read_only=True)
    streamed=load_workbook(export_tov1050_report(result,frame,metadata),read_only=True)
    assert legacy.sheetnames==streamed.sheetnames
    for name in legacy.sheetnames:
        # Write-only XML omits trailing blank cells; compare the full header width.
        assert list(legacy[name].values)==list(streamed[name].iter_rows(values_only=True,max_col=legacy[name].max_column))
        assert legacy[name].sheet_state==streamed[name].sheet_state
    legacy.close()
    streamed.close()


def test_large_tov1050_chartdata_streams_full_rows_without_downsampling():
    frame=pd.DataFrame({"Chainage":range(50001),"height1":[4500.0]*50001})
    workbook=load_workbook(export_analysis_report({},frame,line="AEL"),read_only=True)
    rows=workbook["ChartData"].values
    assert next(rows)==("Chainage","height1")
    count=0
    for count,row in enumerate(rows,1):
        assert row==(count-1,4500)
    assert count==50001
    workbook.close()


def test_eal_large_report_keeps_legacy_writer(monkeypatch):
    from app.core import tov1050_report_export as module
    sentinel=object()
    monkeypatch.setattr(module.ExcelExporter,"export_report",lambda *args,**kwargs:sentinel)
    monkeypatch.setattr(module,"export_tov1050_report",lambda *args,**kwargs: (_ for _ in ()).throw(AssertionError("EAL must keep legacy writer")))
    assert module.export_analysis_report({},pd.DataFrame({"Chainage":range(50001)}),line="EAL") is sentinel


def test_tov1050_download_chunks_preserve_binary_and_csv_bytes():
    import io
    from app.api.endpoints.analysis import _download_body
    for content in (bytes(range(256))*1025, b"Chainage,height1\n"+b"98150.2,4500\n"*20000):
        chunks=list(_download_body(io.BytesIO(content),"KTL"))
        assert b"".join(chunks)==content
        assert max(map(len,chunks))==65536
        assert len(chunks)==(len(content)+65535)//65536
    for line in ("EAL","TML"):
        stream=io.BytesIO(b"legacy\n")
        assert _download_body(stream,line) is stream


@pytest.mark.parametrize("streamed", [False, True])
def test_report_four_decimal_display_preserves_full_measurement_values(streamed):
    value = 48430.1234567
    frame = pd.DataFrame({"Chainage": [value], "height1": [3500.1234567]})
    results = {"Low Height": pd.DataFrame([{"FromM": value, "maxValue": 3500.1234567}])}
    output = export_tov1050_report(results, frame) if streamed else export_analysis_report(results, frame, line="AEL")
    book = load_workbook(output, read_only=True)
    for sheet_name, header, expected in (("ChartData", "Chainage", value), ("Summary", "FromM", value),
                                         ("Low Height", "MaxValue", 3500.1234567)):
        rows = list(book[sheet_name].rows)
        cell = rows[1][[c.value for c in rows[0]].index(header)]
        assert cell.number_format == "0.####"
        assert cell.value == expected
    book.close()
