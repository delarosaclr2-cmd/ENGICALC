"""El ZIP reconstruido mantiene un inventario verificable de su contenido."""
import hashlib
import json
from types import SimpleNamespace
import zipfile

from empaquetado import finalizar_portable as entrega


def test_reconstruir_no_incluye_el_manifiesto_anterior_en_su_propio_hash(tmp_path, monkeypatch):
    app = tmp_path / 'ENGICALC'
    (app / 'HVAC_INDUSTRIAL_CALCULATOR').mkdir(parents=True)
    (app / 'ENGICALC.exe').write_bytes(b'ejecutable de prueba')
    (app / 'HVAC_INDUSTRIAL_CALCULATOR/HVAC_Calculator.exe').write_bytes(b'hvac de prueba')
    dato = app / 'ejemplo.json'
    dato.write_text('{"revision":1}', encoding='utf-8')
    monkeypatch.setattr(entrega.importlib.metadata, 'version', lambda name: '1.0')
    monkeypatch.setattr(entrega.importlib.metadata, 'distribution', lambda name: SimpleNamespace(files=[]))

    def git(args, **kwargs):
        return 'a' * 40 if args[1] == 'rev-parse' else b''

    monkeypatch.setattr(entrega.subprocess, 'check_output', git)
    primera, segunda = tmp_path / 'primera', tmp_path / 'segunda'
    primera.mkdir()
    segunda.mkdir()
    entrega.finalizar(app, primera)
    dato.write_text('{"revision":2}', encoding='utf-8')
    archivo = entrega.finalizar(app, segunda)
    with zipfile.ZipFile(archivo) as z:
        manifiesto = json.loads(z.read('ENGICALC/MANIFIESTO.json'))
        assert 'MANIFIESTO.json' not in manifiesto['archivos']
        for nombre, esperado in manifiesto['archivos'].items():
            assert hashlib.sha256(z.read('ENGICALC/' + nombre)).hexdigest() == esperado
        assert set(z.namelist()) == {'ENGICALC/' + n for n in manifiesto['archivos']} | {'ENGICALC/MANIFIESTO.json'}
        assert json.loads(z.read('ENGICALC/ejemplo.json'))['revision'] == 2
