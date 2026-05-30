
import pandas as pd


df = pd.read_excel(r'resource/test.xlsx')
row_v = {'标题': 'n', '值': '9'}
df.insert(1, 'new_line', value=row_v)

print(df)

# df.to_excel('resource/test_out.xlsx', sheet_name='Sheet1')
