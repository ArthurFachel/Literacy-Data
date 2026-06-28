# Comparação Regional de Alfabetização — Motor de Análise

Backend Python + API REST para comparar taxas de alfabetização entre as regiões do Brasil.

## Arquivos

- `analysis_engine.py` — Classe principal `LiteracyEngine` (carrega dados, ordena municípios, encontra extremos, agrega por região)
- `api.py` — API REST Flask que expõe o motor via HTTP
- `venv/` — Ambiente virtual Python com pandas + flask

## Fonte de dados

Lê de `master_dataset_socioeconomico.csv` (5.570 municípios, pré-unidos com região + covariáveis) e `sidra_alfabetizacao_2022.csv` para nomes de municípios. Ambos do IBGE SIDRA Censo 2022.

## Endpoints da API

| Método | Caminho | Descrição |
|--------|---------|-----------|
| GET | `/regions` | Lista todas as regiões válidas |
| GET | `/regions/<nome>` | Municípios ordenados por alfabetização (melhor → pior) |
| GET | `/regions/<nome>/extremes` | Melhor e pior município |
| POST | `/regions/compare` | Compara entre regiões (body: `{"regions": [...]}`) |

## Executar

```bash
cd /home/fachel/.hermes/kanban/workspaces/t_e0e11d7e
source venv/bin/activate
python api.py [porta]
```

## Exemplos

```bash
# Listar municípios da região Sul
curl http://localhost:5001/regions/Sul

# Melhor e pior no Nordeste
curl http://localhost:5001/regions/Nordeste/extremes

# Comparar Norte vs Nordeste
curl -X POST http://localhost:5001/regions/compare \
  -H 'Content-Type: application/json' \
  -d '{"regions": ["Norte", "Nordeste"]}'
```

## Verificado

Todos os endpoints testados: 5 regiões válidas, ordenação correta, casos de borda tratados (região inválida → 404 com erro descritivo), funciona com lista de regiões vazia.
