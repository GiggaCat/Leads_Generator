import os
import pandas as pd
import openpyxl

def append_to_excel(leads_list, file_name):
    df_new = pd.DataFrame(leads_list)

    # File does NOT exist → create new
    if not os.path.exists(file_name):
        df_new.to_excel(file_name, index=False)
        return

    # File exists → append without breaking formatting
    workbook = openpyxl.load_workbook(file_name)
    sheet = workbook.active

    # Find next empty row
    next_row = sheet.max_row + 1

    for _, row in df_new.iterrows():
        sheet.append(list(row.values))

    workbook.save(file_name)
