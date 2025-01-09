#%%
import pandas as pd
#%%
df = pd.read_parquet('albums_20250104_190759.parquet')


# %%
df['Entradas nas Paradas'] = df['Entradas nas Paradas'].str.strip()
# %%
entradas_split = df['Entradas nas Paradas'].str.split(',', expand=True)
#%%
df_long = entradas_split.melt(ignore_index=False, value_name='Entrada_Parada').dropna()

# Resetar o índice e manter a referência ao índice original
df_long.reset_index(inplace=True)


# Fazer o merge com base no índice original
df_normalizado = pd.merge(df[['Posição', 'Artista', 'Álbum', 'Ano']].reset_index(), df_long, on='index').drop(columns=['index'])
#%%
# Remover duplicatas usando as colunas relevantes
df_normalizado = df_normalizado.drop_duplicates(subset=['Artista', 'Álbum', 'Ano', 'Entrada_Parada'])

# Remover a coluna variable
df_normalizado.drop(columns=['variable'], inplace=True)

#%%
df_normalizado = df_normalizado.rename(columns={
    'Posição': 'Posicao',
    'Artista': 'Artista',
    'Álbum': 'Album',
    'Ano': 'Ano',
    'Entrada_Parada': 'Entrada_Parada'
    })

#%%
df_normalizado.head(20)
#%%
artista = 'Miles Davis'
album = "Kind of Blue"
entradas_album = df_normalizado[(df_normalizado['Artista'] == artista) & (df_normalizado['Album'] == album)]
entradas_album

#%%
df = df_normalizado
#%%
