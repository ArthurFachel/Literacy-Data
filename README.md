# Comparação Regional de Alfabetização


Aplicativo de análise regional de alfabetização no Brasil.

## Visão Geral

Este projeto reúne um backend Python com uma API REST e uma interface de frontend leve para explorar dados de alfabetização, infraestrutura escolar e saneamento por região do Brasil.

- `Literacy-Data/api.py` — backend Flask que expõe os dados via HTTP
- `Literacy-Data/analysis_engine.py` — motor de análise que carrega os dados e gera estatísticas
- `Literacy-Data/frontend/` — interface de exploração com mapa interativo e painéis de comparação
- `Literacy-Data/data/` — os dados estão em um drive, pode ter acesso via o link em data.txt

## Funcionalidades

- Listar regiões válidas disponíveis no dataset
- Exibir municípios de cada região ordenados por taxa de alfabetização
- Encontrar o melhor e o pior município em cada região
- Comparar métricas de alfabetização entre múltiplas regiões
- Agregar dados de infraestrutura escolar (INEP) por região
- Agregar dados de saneamento e provedor de água (SINISA) por região
- Mostrar correlações entre alfabetização e indicadores de infraestrutura/saneamento

## Estrutura do Projeto

- `Literacy-Data/`
  - `api.py`
  - `analysis_engine.py`
  - `frontend/`
    - `index.html`
    - `app.js`
    - `style.css`

## Requisitos

- Python 3.10+ recomendado
- pacotes Python: `flask`, `pandas`, `numpy`, `scipy`
- arquivos de dados esperados pelo `analysis_engine.py`:
  - `master_dataset_socioeconomico.csv`
  - `sidra_alfabetizacao_2022.csv`
  - `INEP.csv`
  - `SINISA_AGUA_Indicadores_Base Municipal_2023.xlsx`

> Atenção: o caminho padrão dos dados está configurado em `Literacy-Data/analysis_engine.py` no valor `DATA_DIR`.

## Como Executar

1. Acesse a pasta do backend:

```bash
cd Literacy-Data
```

2. Ative seu ambiente virtual Python (opcional):

```bash
python -m venv venv
source venv/bin/activate
```

3. Instale dependências:

```bash
pip install flask pandas numpy scipy
```

4. Inicie a API:

```bash
python api.py
```

5. Abra o frontend:

- Abra `Literacy-Data/frontend/index.html` diretamente no navegador.
- Ou sirva a pasta `Literacy-Data/frontend` com um servidor estático para evitar limitações de CORS.

## Endpoints da API

- `GET /regions`
  - Retorna todas as regiões válidas.

- `GET /regions/<region>`
  - Retorna municípios da região ordenados por taxa de alfabetização.

- `GET /regions/<region>/extremes`
  - Retorna o melhor e o pior município da região.

- `POST /regions/compare`
  - Corpo: `{"regions": ["Norte", "Nordeste"]}`
  - Compara estatísticas de alfabetização entre regiões.

- `GET /school-infra`
  - Retorna agregados de infraestrutura escolar por região.

- `GET /sanitation-provider`
  - Retorna estatísticas de provedor de saneamento por região.

- `GET /correlations`
  - Retorna correlações entre indicadores e alfabetização.

- `GET /regions/<region>/school-infra`
  - Dados de infraestrutura escolar para uma região específica.

- `GET /regions/<region>/sanitation-provider`
  - Dados de saneamento para uma região específica.

- `GET /regions/<region>/correlations`
  - Correlações para uma região específica.

## Exemplo de Uso

```bash
curl http://localhost:5000/regions
curl http://localhost:5000/regions/Sul
curl http://localhost:5000/regions/Nordeste/extremes
curl -X POST http://localhost:5000/regions/compare \
  -H 'Content-Type: application/json' \
  -d '{"regions": ["Norte", "Nordeste"]}'
```

## Observações

- O frontend usa `http://localhost:5000` como URL da API.
- Caso a API esteja em outra porta, atualize `API_URL` em `Literacy-Data/frontend/app.js`.
- Alguns endpoints dependem dos arquivos de dados `INEP.csv` e `SINISA` existentes no caminho configurado.
