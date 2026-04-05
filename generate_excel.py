import json
import os
try:
    import pandas as pd
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl"])
    import pandas as pd

def main():
    json_path = os.path.join("Reference", "api_responses.json")
    out_path = os.path.join("Reference", "Endpoint_Fields.xlsx")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    rows = []
    
    for endpoint, response in data.items():
        if "error" in response:
            continue
        
        item = None
        # Check if it's a list endpoint (has 'datas' array)
        if "datas" in response:
            if response["datas"] and isinstance(response["datas"], list) and len(response["datas"]) > 0:
                item = response["datas"][0]
        else:
            # It's a detail endpoint
            item = response
            
        if not item:
            continue
            
        for key, value in item.items():
            val_type = type(value).__name__
            if value is None:
                val_type = "null"
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                val_type = f"Array of Objects"
                
            example_val = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
                
            rows.append({
                "Endpoint": endpoint,
                "Trường Dữ Liệu (Field)": key,
                "Kiểu Dữ Liệu (Type)": val_type,
                "Ví Dụ (Example Value)": example_val
            })
            
    df = pd.DataFrame(rows)
    
    # Save to Excel
    writer = pd.ExcelWriter(out_path, engine='openpyxl')
    df.to_excel(writer, index=False, sheet_name='Fields')
    
    # Auto-adjust columns width
    worksheet = writer.sheets['Fields']
    for idx, col in enumerate(df.columns):
        series = df[col]
        max_len = max((
            series.astype(str).map(len).max(),
            len(str(series.name))
        )) + 2
        worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)
        
    writer.close()
    print(f"Báo cáo đã được lưu tại: {out_path}")

if __name__ == "__main__":
    main()
