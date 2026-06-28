"""
REST API for Brazil Regional Literacy Comparison

Endpoints:
  GET  /regions                    — list all valid regions
  GET  /regions/<region>           — list municipalities sorted best→worst
  GET  /regions/<region>/extremes  — best and worst municipality
  POST /regions/compare            — compare multiple regions (body: {"regions": [...]})

Run: python api.py
"""

import json
from flask import Flask, request, jsonify
from analysis_engine import get_engine, LiteracyEngine

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

engine: LiteracyEngine = get_engine()


@app.route('/regions', methods=['GET'])
def list_regions():
    """Return all valid region names."""
    return jsonify({'regions': engine.valid_regions})


@app.route('/regions/<region>', methods=['GET'])
def get_region(region: str):
    """Return municipalities in a region sorted best→worst."""
    try:
        result = engine.list_municipalities(region)
        return jsonify({
            'region': region,
            'total': len(result),
            'municipalities': result.to_dict(orient='records'),
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@app.route('/regions/<region>/extremes', methods=['GET'])
def get_extremes(region: str):
    """Return the best and worst municipality in a region."""
    try:
        result = engine.best_worst(region)
        return jsonify({
            'region': region,
            **result,
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@app.route('/regions/compare', methods=['POST'])
def compare():
    """Compare literacy stats across specified regions.

    Body: {"regions": ["Norte", "Nordeste"]}  or {"regions": null} for all
    """
    data = request.get_json(silent=True) or {}
    regions = data.get('regions', None)
    try:
        stats = engine.compare_regions(regions)
        return jsonify({
            'comparison': stats.to_dict(orient='records'),
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({'error': 'Method not allowed'}), 405


# ============================================
# NEW: School Infrastructure (INEP) endpoints
# ============================================

@app.route('/school-infra', methods=['GET'])
def school_infra():
    """Return school infrastructure aggregated by region."""
    try:
        df = engine.school_infra_by_region()
        result = []
        for _, r in df.iterrows():
            # Handle potential scalar vs series; force scalar via iloc if needed
            municipios = int(r['municipios'].item() if hasattr(r['municipios'], 'item') else r['municipios'])
            result.append({
                'regiao': str(r['regiao']),
                'municipios': municipios,
                'refeitorio_publica_pct': round(float(r['mean_refeitorio_publica']) * 100, 1),
                'refeitorio_privada_pct': round(float(r['mean_refeitorio_privada']) * 100, 1),
                'cozinha_publica_pct': round(float(r['mean_cozinha_publica']) * 100, 1),
                'cozinha_privada_pct': round(float(r['mean_cozinha_privada']) * 100, 1),
                'alfabetizacao_media': round(float(r['mean_alfabetizacao']), 2),
            })
        return jsonify({'data': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/sanitation-provider', methods=['GET'])
def sanitation_provider():
    """Return sanitation provider (SINISA) stats by region."""
    try:
        df = engine.sanitation_provider_by_region()
        result = []
        for _, r in df.iterrows():
            def safe_float(val):
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return None
            def safe_int(val):
                try:
                    return int(val)
                except (TypeError, ValueError):
                    return None
            result.append({
                'regiao': str(r['regiao']),
                'total_municipios': safe_int(r['total']),
                'pct_saneamento_publico': safe_float(r['pct_publico']),
                'pct_saneamento_privado': safe_float(r['pct_privado']),
                'alf_publico': round(safe_float(r['mean_alf_publico']), 2) if safe_float(r['mean_alf_publico']) is not None else None,
                'alf_privado': round(safe_float(r['mean_alf_privado']), 2) if safe_float(r['mean_alf_privado']) is not None else None,
                'cobertura_publico': round(safe_float(r['mean_cobertura_publico']), 1) if safe_float(r['mean_cobertura_publico']) is not None else None,
                'cobertura_privado': round(safe_float(r['mean_cobertura_privado']), 1) if safe_float(r['mean_cobertura_privado']) is not None else None,
            })
        return jsonify({'data': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/correlations', methods=['GET'])
def correlations():
    """Return Pearson correlations between infra/sanitation and literacy."""
    try:
        corr = engine.correlations()
        return jsonify({'correlations': corr})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================
# NEW: Region-specific endpoints for interactivity
# ============================================

@app.route('/regions/<region>/school-infra', methods=['GET'])
def region_school_infra(region: str):
    """Return school infrastructure data for a specific region."""
    try:
        data = engine.school_infra_by_region_single(region)
        return jsonify(data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/regions/<region>/sanitation-provider', methods=['GET'])
def region_sanitation_provider(region: str):
    """Return sanitation provider data for a specific region."""
    try:
        data = engine.sanitation_provider_by_region_single(region)
        return jsonify(data)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/regions/<region>/correlations', methods=['GET'])
def region_correlations(region: str):
    """Return correlations for a specific region."""
    try:
        corr = engine.correlations()
        return jsonify({'correlations': corr})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

if __name__ == '__main__':
    import sys

    port = 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

    print(f"Literacy Analysis API running on http://0.0.0.0:{port}")
    print(f"Valid regions: {engine.valid_regions}")
    app.run(host='0.0.0.0', port=port, debug=False)
