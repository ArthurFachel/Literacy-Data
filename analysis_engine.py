"""
Brazil Regional Literacy Analysis Engine

Provides functions to:
1. List municipalities in a region sorted by literacy rate (best to worst)
2. Get the best and worst municipality in a region
3. Compare literacy stats across multiple regions
4. School infrastructure (INEP) by municipality
5. Sanitation provider (SINISA) by municipality

Data source: master_dataset_socioeconomico.csv + sidra_alfabetizacao_2022.csv + INEP.csv + SINISA
"""

import pandas as pd
import numpy as np
from scipy import stats
import os
from typing import Optional

DATA_DIR = '/home/fachel/Desktop/Vscode/CPA-TF/data'

MASTER_PATH = os.path.join(DATA_DIR, 'master_dataset_socioeconomico.csv')
SIDRA_PATH = os.path.join(DATA_DIR, 'sidra_alfabetizacao_2022.csv')
INEP_PATH = os.path.join(DATA_DIR, 'INEP.csv')
SINISA_PATH = os.path.join(DATA_DIR, 'SINISA_AGUA_Indicadores_Base Municipal_2023.xlsx')

_engine = None


class LiteracyEngine:
    """Loads and analyzes literacy data by region."""

    def __init__(self, master_path: str = MASTER_PATH, sidra_path: str = SIDRA_PATH,
                 inep_path: str = INEP_PATH, sinisa_path: str = SINISA_PATH):
        # -- Master + names (existing) --
        self.df = pd.read_csv(master_path)
        sidra = pd.read_csv(sidra_path, encoding='latin-1')
        general = sidra[sidra['variavel'].str.contains(
            'pessoas de 15 anos ou mais de idade', regex=False
        )].copy()
        general['nome_municipio_clean'] = (
            general['nome_municipio']
            .str.encode('latin-1')
            .str.decode('utf-8')
            .str.replace(r'\s+-\s+[A-Z]{2}$', '', regex=True)
        )
        name_map = general[['cod_municipio', 'nome_municipio_clean']].drop_duplicates()
        name_map = name_map.set_index('cod_municipio')['nome_municipio_clean']
        self.df['municipio'] = self.df['cod_municipio'].map(name_map)
        self.valid_regions = sorted(self.df['regiao'].unique().tolist())

        # -- INEP school infrastructure --
        if os.path.exists(inep_path):
            self._load_inep(inep_path)
        else:
            self.inep_mun = pd.DataFrame()

        # -- SINISA sanitation provider --
        if os.path.exists(sinisa_path):
            self._load_sinisa(sinisa_path)
        else:
            self.sinisa_mun = pd.DataFrame()

    def _load_inep(self, path: str):
        inep = pd.read_csv(path, encoding='latin-1', low_memory=False)
        inep['id_municipio_str'] = inep['id_municipio'].astype(str).str.replace('.0', '', regex=False)

        # Classify school as public/private
        inep['escola_publica'] = inep['rede'].isin(['Municipal', 'Estadual', 'Federal']).astype(int)
        inep['escola_privada'] = (inep['rede'] == 'Privada').astype(int)

        pub = inep[inep['escola_publica'] == 1].groupby('id_municipio_str').agg(
            total_publicas=('id_municipio', 'count'),
            pct_refeitorio_publica=('refeitorio', 'mean'),
            pct_cozinha_publica=('cozinha', 'mean'),
        ).reset_index()

        # Aggregate private schools
        priv = inep[inep['escola_privada'] == 1].groupby('id_municipio_str').agg(
            total_privadas=('id_municipio', 'count'),
            pct_refeitorio_privada=('refeitorio', 'mean'),
            pct_cozinha_privada=('cozinha', 'mean'),
        ).reset_index()

        # Total schools
        total = inep.groupby('id_municipio_str').agg(total_escolas=('id_municipio', 'count')).reset_index()

        self.inep_mun = total.merge(pub, on='id_municipio_str', how='left').merge(priv, on='id_municipio_str', how='left')
        self.inep_mun['razao_privada'] = (self.inep_mun['total_privadas'] / self.inep_mun['total_escolas']).fillna(0)


    def _load_sinisa(self, path: str):
        sin = pd.read_excel(path, skiprows=7)
        sin = sin[sin['Codigo do IBGE'].notna() & (sin['Codigo do IBGE'] != 'Codigo do IBGE')].copy()
        sin['cod_IBGE'] = sin['Codigo do IBGE'].astype(str).str.replace('.0', '', regex=False)

        def _classify_nat(nat):
            if pd.isna(nat):
                return np.nan
            nat = str(nat).lower()
            publicos = ['municipio', 'autarquia', 'empresa publica', 'estado']
            privados = ['empresa privada', 'sociedade de economia mista', 'associacao privada']
            tem_publico = any(p in nat for p in publicos)
            tem_privado = any(p in nat for p in privados)
            if tem_publico and not tem_privado:
                return 'publico'
            elif tem_privado and not tem_publico:
                return 'privado'
            elif tem_publico and tem_privado:
                return 'misto'
            else:
                return 'outro'

        sin['nat_class'] = sin['Natureza Jurídica'].apply(_classify_nat)
        sin['saneamento_publico'] = (sin['nat_class'] == 'publico').astype(int)
        sin['saneamento_privado'] = (sin['nat_class'] == 'privado').astype(int)

        # Convert water coverage to numeric
        sin['cobertura_agua'] = pd.to_numeric(
            sin['Atendimento da população total com rede de abastecimento de água'],
            errors='coerce'
        )

        self.sinisa_mun = sin[['cod_IBGE', 'nat_class', 'saneamento_publico', 'saneamento_privado', 'cobertura_agua']].copy()

    def get_merged(self) -> pd.DataFrame:
        """Return master merged with INEP and SINISA."""
        df = self.df.copy()
        df['cod_municipio_str'] = df['cod_municipio'].astype(str)

        if not self.inep_mun.empty:
            df = df.merge(self.inep_mun, left_on='cod_municipio_str', right_on='id_municipio_str', how='left')

        if not self.sinisa_mun.empty:
            df = df.merge(self.sinisa_mun, left_on='cod_municipio_str', right_on='cod_IBGE', how='left')

        return df

    def list_municipalities(self, region: str) -> pd.DataFrame:
        """
        Return municipalities in a region sorted by literacy rate (best first).
        Columns: cod_municipio, municipio, taxa_alfabetizacao, pop_total
        """
        if region not in self.valid_regions:
            raise ValueError(f"Unknown region '{region}'. Valid: {self.valid_regions}")

        subset = self.df[self.df['regiao'] == region].copy()
        subset = subset.sort_values('taxa_alfabetizacao', ascending=False)
        return subset[['cod_municipio', 'municipio', 'taxa_alfabetizacao', 'pop_total']].reset_index(drop=True)

    def best_worst(self, region: str) -> dict:
        """
        Return the best and worst municipality in a region.
        Returns dict with 'best' and 'worst' keys, each: {cod_municipio, municipio, taxa_alfabetizacao, pop_total}
        """
        if region not in self.valid_regions:
            raise ValueError(f"Unknown region '{region}'. Valid: {self.valid_regions}")

        subset = self.df[self.df['regiao'] == region]

        best = subset.loc[subset['taxa_alfabetizacao'].idxmax()]
        worst = subset.loc[subset['taxa_alfabetizacao'].idxmin()]

        def _row(r):
            return {
                'cod_municipio': int(r['cod_municipio']),
                'municipio': r['municipio'],
                'taxa_alfabetizacao': round(float(r['taxa_alfabetizacao']), 2),
                'pop_total': int(r['pop_total']),
            }

        return {'best': _row(best), 'worst': _row(worst)}

    def compare_regions(self, regions: Optional[list[str]] = None) -> pd.DataFrame:
        """
        Compare literacy statistics across multiple regions.
        If regions is None, compares all regions.
        Returns: region, count, mean, median, min, max, std
        """
        if regions is None:
            regions = self.valid_regions

        for r in regions:
            if r not in self.valid_regions:
                raise ValueError(f"Unknown region '{r}'. Valid: {self.valid_regions}")

        subset = self.df[self.df['regiao'].isin(regions)]

        stats = subset.groupby('regiao')['taxa_alfabetizacao'].agg(
            count='count',
            mean='mean',
            median='median',
            min='min',
            max='max',
            std='std',
        ).round(2).reset_index()

        stats.columns = ['regiao', 'municipios', 'media', 'mediana', 'minimo', 'maximo', 'desvio_padrao']
        return stats

    def school_infra_by_region(self) -> pd.DataFrame:
        """Return school infrastructure (INEP) aggregated by region."""
        df = self.get_merged()
        # Only municipalities with both public and private data
        mask = df['pct_refeitorio_publica'].notna() & df['pct_refeitorio_privada'].notna()
        df = df[mask].copy()

        agg = df.groupby('regiao').agg(
            municipios=('cod_municipio', 'count'),
            mean_refeitorio_publica=('pct_refeitorio_publica', 'mean'),
            mean_refeitorio_privada=('pct_refeitorio_privada', 'mean'),
            mean_cozinha_publica=('pct_cozinha_publica', 'mean'),
            mean_cozinha_privada=('pct_cozinha_privada', 'mean'),
            mean_alfabetizacao=('taxa_alfabetizacao', 'mean'),
        ).round(3).reset_index()
        return agg

    def sanitation_provider_by_region(self) -> pd.DataFrame:
        """Return sanitation provider (SINISA) statistics by region."""
        df = self.get_merged()
        df = df[df['nat_class'].isin(['publico', 'privado'])].copy()

        # For each region, calculate % municipalities with public vs private provider
        # and mean literacy for each
        pub = df[df['nat_class'] == 'publico'].groupby('regiao').agg(
            count_publico=('cod_municipio', 'count'),
            mean_alf_publico=('taxa_alfabetizacao', 'mean'),
            mean_cobertura_publico=('cobertura_agua_pct', 'mean'),
        ).round(2)

        priv = df[df['nat_class'] == 'privado'].groupby('regiao').agg(
            count_privado=('cod_municipio', 'count'),
            mean_alf_privado=('taxa_alfabetizacao', 'mean'),
            mean_cobertura_privado=('cobertura_agua_pct', 'mean'),
        ).round(2)

        # Total municipalities per region
        total = df.groupby('regiao')['cod_municipio'].count().to_frame('total')

        merged = total.join(pub, how='left').join(priv, how='left').reset_index()
        merged['pct_publico'] = (merged['count_publico'] / merged['total'] * 100).round(1)
        merged['pct_privado'] = (merged['count_privado'] / merged['total'] * 100).round(1)
        return merged.fillna(0)

    def school_infra_by_region_single(self, region: str) -> dict:
        """Return school infrastructure details for a single region."""
        if region not in self.valid_regions:
            raise ValueError(f"Unknown region '{region}'.")
        df = self.get_merged()
        sub = df[df['regiao'] == region].copy()
        mask = sub['pct_refeitorio_publica'].notna()
        sub = sub[mask]
        if sub.empty:
            return {'regiao': region, 'municipios': 0}
        return {
            'regiao': region,
            'municipios': int(len(sub)),
            'refeitorio_publica_pct': round(float(sub['pct_refeitorio_publica'].mean()) * 100, 1),
            'refeitorio_privada_pct': round(float(sub['pct_refeitorio_privada'].mean()) * 100, 1),
            'cozinha_publica_pct': round(float(sub['pct_cozinha_publica'].mean()) * 100, 1),
            'cozinha_privada_pct': round(float(sub['pct_cozinha_privada'].mean()) * 100, 1),
            'alfabetizacao_media': round(float(sub['taxa_alfabetizacao'].mean()), 2),
        }

    def sanitation_provider_by_region_single(self, region: str) -> dict:
        """Return sanitation provider stats for a single region."""
        if region not in self.valid_regions:
            raise ValueError(f"Unknown region '{region}'.")
        df = self.get_merged()
        sub = df[(df['regiao'] == region) & df['nat_class'].isin(['publico', 'privado'])].copy()
        if sub.empty:
            return {'regiao': region, 'total_municipios': 0}
        total = len(sub)
        pub = sub[sub['nat_class'] == 'publico']
        priv = sub[sub['nat_class'] == 'privado']
        return {
            'regiao': region,
            'total_municipios': int(total),
            'pct_saneamento_publico': round(len(pub) / total * 100, 1) if total else 0,
            'pct_saneamento_privado': round(len(priv) / total * 100, 1) if total else 0,
            'alf_publico': round(float(pub['taxa_alfabetizacao'].mean()), 2) if not pub.empty else None,
            'alf_privado': round(float(priv['taxa_alfabetizacao'].mean()), 2) if not priv.empty else None,
            'cobertura_publico': round(float(pub['cobertura_agua'].mean()), 1) if not pub.empty else None,
            'cobertura_privado': round(float(priv['cobertura_agua'].mean()), 1) if not priv.empty else None,
        }

    def correlations(self) -> dict:
        """Return Pearson correlations between infra/sanitation and literacy."""
        df = self.get_merged().dropna(subset=['taxa_alfabetizacao'])
        result = {}

        sub = df.dropna(subset=['pct_refeitorio_publica', 'taxa_alfabetizacao'])
        r, p = stats.pearsonr(sub['pct_refeitorio_publica'], sub['taxa_alfabetizacao'])
        result['refeitorio_publica'] = {'r': round(r, 3), 'p': round(p, 3), 'n': len(sub)}

        sub = df.dropna(subset=['pct_refeitorio_privada', 'taxa_alfabetizacao'])
        r, p = stats.pearsonr(sub['pct_refeitorio_privada'], sub['taxa_alfabetizacao'])
        result['refeitorio_privada'] = {'r': round(r, 3), 'p': round(p, 3), 'n': len(sub)}

        sub = df.dropna(subset=['pct_cozinha_publica', 'taxa_alfabetizacao'])
        r, p = stats.pearsonr(sub['pct_cozinha_publica'], sub['taxa_alfabetizacao'])
        result['cozinha_publica'] = {'r': round(r, 3), 'p': round(p, 3), 'n': len(sub)}

        sub = df.dropna(subset=['pct_cozinha_privada', 'taxa_alfabetizacao'])
        r, p = stats.pearsonr(sub['pct_cozinha_privada'], sub['taxa_alfabetizacao'])
        result['cozinha_privada'] = {'r': round(r, 3), 'p': round(p, 3), 'n': len(sub)}

        sub = df.dropna(subset=['cobertura_agua_pct', 'taxa_alfabetizacao'])
        r, p = stats.pearsonr(sub['cobertura_agua_pct'], sub['taxa_alfabetizacao'])
        result['cobertura_agua'] = {'r': round(r, 3), 'p': round(p, 3), 'n': len(sub)}

        sub = df[df['nat_class'].isin(['publico', 'privado'])].dropna(subset=['saneamento_privado', 'taxa_alfabetizacao'])
        r, p = stats.pearsonr(sub['saneamento_privado'], sub['taxa_alfabetizacao'])
        result['saneamento_privado_dummy'] = {'r': round(r, 3), 'p': round(p, 3), 'n': len(sub)}

        return result


def get_engine() -> LiteracyEngine:
    """Get or create the singleton engine."""
    global _engine
    if _engine is None:
        _engine = LiteracyEngine()
    return _engine
