import pandas as pd

# Merge datasets from multiple sources

# load both CSVs
df_vcsheet = pd.read_csv("/Users/theguy/Desktop/stuff/vcsheet.csv")
df_investorhunt = pd.read_csv("/Users/theguy/Desktop/stuff/investorhunt.csv")

print(f"vcsheet rows: {len(df_vcsheet)}")
print(f"investorhunt rows: {len(df_investorhunt)}")

# standardize name column
df_vcsheet.rename(columns={"firm_name": "name"}, inplace=True)

# add missing columns
df_vcsheet["investor_type"] = "VC Firm"
df_investorhunt["website"] = pd.NA

# tag each row with its source
df_vcsheet["data_source"] = "vcsheet"
df_investorhunt["data_source"] = "investorhunt"

# combine
df_final = pd.concat([df_vcsheet, df_investorhunt], ignore_index=True)

print(f"\nBefore deduplication: {len(df_final)}")

df_final.drop_duplicates(subset="name", inplace=True)

print(f"After deduplication: {len(df_final)}")
print(f"\nNull counts:")
print(df_final.isnull().sum())
print(f"\nColumns: {list(df_final.columns)}")

df_final.to_csv("/Users/theguy/Desktop/stuff/healthcare_vcs_final.csv", index=False)
print("\nSaved to healthcare_vcs_final.csv")