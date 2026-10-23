"""Bounded-memory ChartData writer; legacy exception/report semantics unchanged."""
from copy import copy
import io
import math

from openpyxl import Workbook, load_workbook
from openpyxl.cell import WriteOnlyCell
import pandas as pd

from .exporter import ExcelExporter
from .tov1050_contract import LINE_WORKBOOKS


def _excel_value(value):
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float):
        return None if math.isnan(value) else str(value) if math.isinf(value) else value
    return value


def export_tov1050_report(results, chart_df=None, metadata=None):
    """Delegate Summary/exception generation, stream full ChartData row by row.

    This function does not map metadata, aggregate exceptions, or downsample.
    The small legacy workbook provides exact headers/order and formatting.
    """
    small = ExcelExporter.export_report(results, chart_df=None)
    source = load_workbook(small, read_only=True)
    target = Workbook(write_only=True)
    header_style = source["Summary"]["A1"]

    def header(sheet, values):
        cells=[]
        for value in values:
            cell=WriteOnlyCell(sheet,value=value)
            cell.font=copy(header_style.font)
            cell.border=copy(header_style.border)
            cell.fill=copy(header_style.fill)
            cell.alignment=copy(header_style.alignment)
            cells.append(cell)
        sheet.append(cells)

    for original in source:
        sheet=target.create_sheet(original.title)
        for index,row in enumerate(original.iter_rows()):
            if index == 0:
                header(sheet,[cell.value for cell in row])
            else:
                sheet.append([cell.value for cell in row])
    if chart_df is not None and not chart_df.empty:
        columns=[c for c in ExcelExporter.CATENARY_COLUMNS if c in chart_df.columns]
        sheet=target.create_sheet("ChartData")
        header(sheet,columns)
        for row in chart_df[columns].itertuples(index=False,name=None):
            sheet.append([_excel_value(value) for value in row])
    if metadata:
        sheet=target.create_sheet("_Metadata")
        sheet.sheet_state="hidden"
        header(sheet,["key","value"])
        for key,value in metadata.items():
            sheet.append([key,str(value)])
    output=io.BytesIO()
    target.save(output)
    source.close()
    output.seek(0)
    return output


def export_analysis_report(results, chart_df=None, metadata=None, line=""):
    if str(line).strip().upper() in LINE_WORKBOOKS and chart_df is not None and len(chart_df)>50_000:
        return export_tov1050_report(results,chart_df,metadata)
    return ExcelExporter.export_report(results,chart_df=chart_df,metadata=metadata)
